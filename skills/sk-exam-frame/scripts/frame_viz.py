#!/usr/bin/env python3
"""Draw a problem map and a quick data scatter as SVG with the standard library only.

  template  write an example problem-map spec (JSON) to fill in
  map       spec JSON -> problem_map.svg (cause tree, system flow, assumption -> break -> question)
  scatter   CSV x/y columns -> scatter SVG, with optional group colors, overlay points and marks

Every command prints a JSON summary. Exit codes: 0 ok, 1 input error, 2 nothing to draw.
If matplotlib and a Korean-capable font are already installed, --png also writes a PNG copy of
the scatter. Nothing is installed, downloaded, or opened in a browser.
"""

import argparse
import csv
import json
import math
from pathlib import Path
import sys
from xml.sax.saxutils import escape

PALETTE = ("#2f6db5", "#d9822b", "#3a9a5b", "#c23b3b", "#7b5ea7",
           "#8c6d3f", "#d16ba5", "#5f6b7a", "#3fa7b5", "#a3a33a")
STATUS_COLOR = {"확인": "#3a9a5b", "반박": "#c23b3b", "미확인": "#8a8f98", "가설": "#d9822b"}
FONT = "font-family=\"'Malgun Gothic','Apple SD Gothic Neo','Noto Sans CJK KR','NanumGothic',sans-serif\""

TEMPLATE = {
    "title": "문제 지도 — 과제 이름",
    "problem": "누가 / 어떤 결정을 / 무엇 때문에 지금 못 하나",
    "causes": [{"text": "근본 원인 가설", "status": "가설"}],
    "effects": ["지금 드러나는 증상"],
    "flow": {
        "inputs": ["입력 데이터"],
        "process": ["처리·규칙"],
        "outputs": ["출력"],
        "users": [{"name": "담당자", "action": "조건을 바꾸고 결과를 확인"},
                  {"name": "사용자", "action": "자기 결과를 조회"}],
    },
    "assumptions": [{"assumption": "단순 해법이 깔고 있는 가정",
                     "breaks": "현실이 다르면 틀리는 결과",
                     "question": "담당자에게 물을 구체 질문 하나",
                     "status": "미확인",
                     "by": "참가자"}],
}


class InputError(Exception):
    pass


def text_width(text, size):
    return sum(size * (1.0 if ord(ch) > 0x2E80 else 0.58) for ch in text)


def wrap(text, width, size):
    paragraphs = str(text).split("\n")
    if len(paragraphs) > 1:  # explicit line breaks are kept
        return [line for part in paragraphs for line in wrap(part, width, size)]
    lines, line = [], ""
    for word in str(text).split(" "):
        candidate = f"{line} {word}".strip()
        if line and text_width(candidate, size) > width:
            lines.append(line)
            line = word
        else:
            line = candidate
        while text_width(line, size) > width:  # one long word: hard split
            cut = len(line)
            while cut > 1 and text_width(line[:cut], size) > width:
                cut -= 1
            lines.append(line[:cut])
            line = line[cut:]
    if line:
        lines.append(line)
    return lines or [""]


class Svg:
    def __init__(self, width):
        self.width = width
        self.parts = []
        self.shapes = []  # same drawing as plain tuples, replayed by png()
        self.bottom = 0

    def text(self, x, y, value, size=13, weight="normal", fill="#1f2328", anchor="start"):
        self.parts.append(f'<text x="{x:.1f}" y="{y:.1f}" font-size="{size}" font-weight="{weight}" '
                          f'fill="{fill}" text-anchor="{anchor}" {FONT}>{escape(str(value))}</text>')
        self.shapes.append(("text", x, y, str(value), size, weight, fill, anchor))
        self.bottom = max(self.bottom, y + size * 0.4)

    @staticmethod
    def box_height(lines, size=13, tag=None):
        return len(lines) * size * 1.35 + 14 + (16 if tag else 0)

    def box(self, x, y, w, lines, size=13, fill="#f4f6f8", stroke="#8a8f98", tag=None, tag_color="#8a8f98",
            height=None):
        line_h = size * 1.35
        h = max(self.box_height(lines, size, tag), height or 0)
        self.parts.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" rx="6" '
                          f'fill="{fill}" stroke="{stroke}"/>')
        self.shapes.append(("rect", x, y, w, h, fill, stroke))
        ty = y + 7 + size
        if tag:
            self.text(x + 8, ty - 2, f"[{tag}]", size=11, weight="bold", fill=tag_color)
            ty += 16
        for line in lines:
            self.text(x + 8, ty, line, size=size)
            ty += line_h
        self.bottom = max(self.bottom, y + h)
        return h

    def arrow(self, x1, y1, x2, y2):
        self.parts.append(f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" '
                          f'stroke="#5f6b7a" stroke-width="1.5" marker-end="url(#arrow)"/>')
        self.shapes.append(("arrow", x1, y1, x2, y2))

    def render(self, height=None):
        height = height or self.bottom + 24
        head = (f'<svg xmlns="http://www.w3.org/2000/svg" width="{self.width}" height="{height:.0f}" '
                f'viewBox="0 0 {self.width} {height:.0f}">'
                '<defs><marker id="arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" '
                'markerHeight="7" orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" fill="#5f6b7a"/>'
                '</marker></defs><rect width="100%" height="100%" fill="#ffffff"/>')
        return head + "".join(self.parts) + "</svg>\n"

    def png(self, out, height=None):
        plt, note = korean_pyplot()
        if plt is None:
            return note
        from matplotlib.patches import FancyBboxPatch
        height = height or self.bottom + 24
        dpi = 100
        fig = plt.figure(figsize=(self.width / dpi, height / dpi), dpi=dpi)
        ax = fig.add_axes((0, 0, 1, 1))
        ax.set_xlim(0, self.width)
        ax.set_ylim(height, 0)
        ax.axis("off")
        points = 72 / dpi  # SVG pixel sizes -> matplotlib points
        for shape in self.shapes:
            if shape[0] == "rect":
                _, x, y, w, h, fill, stroke = shape
                ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0,rounding_size=6",
                                            facecolor=fill, edgecolor=stroke, linewidth=1))
            elif shape[0] == "arrow":
                _, x1, y1, x2, y2 = shape
                ax.annotate("", xy=(x2, y2), xytext=(x1, y1),
                            arrowprops={"arrowstyle": "-|>", "color": "#5f6b7a", "lw": 1.3})
            else:
                _, x, y, value, size, weight, fill, anchor = shape
                ha = {"start": "left", "middle": "center", "end": "right"}[anchor]
                ax.text(x, y, value, fontsize=size * points, fontweight=weight, color=fill, ha=ha, va="baseline")
        fig.savefig(out, dpi=dpi, facecolor="white")
        plt.close(fig)
        return str(out)


def korean_pyplot():
    """Return (pyplot, font name) when matplotlib and a Korean font are already installed."""
    try:
        import matplotlib
        matplotlib.use("Agg")
        from matplotlib import font_manager, pyplot as plt
    except ImportError:
        return None, "matplotlib 없음: PNG 생략(SVG 사용)"
    names = {f.name for f in font_manager.fontManager.ttflist}
    korean = next((n for n in ("Malgun Gothic", "AppleGothic", "Apple SD Gothic Neo", "NanumGothic",
                               "Noto Sans CJK KR", "Noto Sans KR", "UnDotum") if n in names), None)
    if korean is None:
        return None, "한글 글꼴 없음: PNG 생략(SVG 사용)"
    plt.rcParams["font.family"] = korean
    plt.rcParams["axes.unicode_minus"] = False
    return plt, korean


def as_list(value, name):
    if value is None:
        return []
    if not isinstance(value, list):
        raise InputError(f"{name} must be a list")
    return value


def column(svg, x, y, w, title, items, size=13):
    svg.text(x, y, title, size=12, weight="bold", fill="#5f6b7a")
    y += 8
    mids = []
    for item in items:
        if isinstance(item, dict):
            label = item.get("text") or item.get("name") or ""
            if item.get("action"):
                label = f"{label}: {item['action']}"
            status = item.get("status")
        else:
            label, status = str(item), None
        h = svg.box(x, y, w, wrap(label, w - 16, size), size=size, tag=status,
                    tag_color=STATUS_COLOR.get(status, "#8a8f98"))
        mids.append(y + h / 2)
        y += h + 8
    return mids, y


def draw_map(spec):
    svg, summary = build_map(spec)
    return (svg.render() if svg else None), summary


def build_map(spec):
    if not isinstance(spec, dict):
        raise InputError("spec must be a JSON object")
    flow = spec.get("flow") or {}
    if not isinstance(flow, dict):
        raise InputError("flow must be an object with inputs/process/outputs/users")
    causes = as_list(spec.get("causes"), "causes")
    effects = as_list(spec.get("effects"), "effects")
    assumptions = as_list(spec.get("assumptions"), "assumptions")
    stages = [("입력", as_list(flow.get("inputs"), "flow.inputs")),
              ("처리·규칙", as_list(flow.get("process"), "flow.process")),
              ("출력", as_list(flow.get("outputs"), "flow.outputs")),
              ("사용자", as_list(flow.get("users"), "flow.users"))]
    if not (spec.get("problem") or causes or assumptions or any(items for _, items in stages)):
        return None, {"sections": 0}

    svg = Svg(1200)
    svg.text(24, 36, spec.get("title", "문제 지도"), size=20, weight="bold")
    y = 56

    # 1. causes -> problem -> effects
    svg.text(24, y + 16, "1. 원인 → 문제 → 증상", size=15, weight="bold")
    top = y + 34
    cause_mids, c_end = column(svg, 24, top, 340, "근본 원인(근거 상태)", causes)
    problem_lines = wrap(spec.get("problem", ""), 340, 15)
    svg.text(430, top, "풀어야 할 문제", size=12, weight="bold", fill="#5f6b7a")
    ph = svg.box(430, top + 8, 356, problem_lines, size=15, fill="#fff4e5", stroke="#d9822b")
    p_mid = top + 8 + ph / 2
    effect_mids, e_end = column(svg, 850, top, 326, "드러나는 증상", effects)
    for m in cause_mids:
        svg.arrow(364, m, 428, p_mid)
    for m in effect_mids:
        svg.arrow(786, p_mid, 848, m)
    y = max(c_end, e_end, top + 8 + ph) + 24

    # 2. system boundary
    svg.text(24, y + 16, "2. 시스템 경계: 입력 → 처리 → 출력 → 사용자", size=15, weight="bold")
    top = y + 34
    col_w, gap = 270, 22
    ends, mids_prev = [], None
    for i, (title, items) in enumerate(stages):
        x = 24 + i * (col_w + gap)
        mids, end = column(svg, x, top, col_w, title, items)
        ends.append(end)
        if mids_prev and mids:
            svg.arrow(x - gap, sum(mids_prev) / len(mids_prev), x - 2, sum(mids) / len(mids))
        mids_prev = mids or mids_prev
    y = max(ends + [top]) + 24

    # 3. assumptions -> breaks -> questions
    if assumptions:
        svg.text(24, y + 16, "3. 단순 해법의 숨은 가정 → 깨지는 지점 → 인터뷰 질문", size=15, weight="bold")
        y += 34
        widths = (330, 380, 410)
        xs = (24, 24 + widths[0] + 14, 24 + widths[0] + widths[1] + 28)
        for x, w, title in zip(xs, widths, ("가정(상태)", "현실이 다르면 틀리는 결과", "담당자에게 물을 질문")):
            svg.text(x, y, title, size=12, weight="bold", fill="#5f6b7a")
        y += 8
        for n, item in enumerate(assumptions, 1):
            if not isinstance(item, dict):
                raise InputError("each assumption must be an object")
            status = item.get("status", "미확인")
            tag = f"{status} · {item['by']}" if item.get("by") else status  # 출처: 참가자 / AI 제안
            cells = (f"A{n}. {item.get('assumption', '')}", item.get("breaks", ""), f"Q{n}. {item.get('question', '')}")
            wrapped = [wrap(text, w - 16, 13) for text, w in zip(cells, widths)]
            h = max(Svg.box_height(lines, 13, tag if i == 0 else None) for i, lines in enumerate(wrapped))
            for i, (x, w, lines) in enumerate(zip(xs, widths, wrapped)):
                fill = ("#f4f6f8", "#fdeeee", "#eef4fb")[i]
                svg.box(x, y, w, lines, size=13, fill=fill, height=h,
                        tag=tag if i == 0 else None, tag_color=STATUS_COLOR.get(status, "#8a8f98"))
            for i in range(2):
                svg.arrow(xs[i] + widths[i], y + h / 2, xs[i + 1] - 2, y + h / 2)
            y += h + 8
    summary = {"sections": 3 if assumptions else 2, "causes": len(causes), "effects": len(effects),
               "assumptions": len(assumptions), "flow_items": sum(len(items) for _, items in stages)}
    return svg, summary


def nice_ticks(lo, hi, count=6):
    if hi <= lo:
        hi = lo + 1
    raw = (hi - lo) / count
    mag = 10 ** math.floor(math.log10(raw))
    step = next(m * mag for m in (1, 2, 2.5, 5, 10) if m * mag >= raw)
    start = math.ceil(lo / step) * step
    ticks, t = [], start
    while t <= hi + step * 1e-9:
        ticks.append(round(t, 10))
        t += step
    return ticks


def read_points(path, xcol, ycol, gcol=None, encoding="utf-8-sig"):
    try:
        return _read_points(path, xcol, ycol, gcol, encoding)
    except UnicodeDecodeError as error:
        raise InputError(f"{Path(path).name}: cannot decode as {encoding}; try --encoding cp949") from error


def _read_points(path, xcol, ycol, gcol, encoding):
    with open(path, encoding=encoding, newline="") as handle:
        reader = csv.DictReader(handle)
        fields = reader.fieldnames or []
        for name in (xcol, ycol) + ((gcol,) if gcol else ()):
            if name not in fields:
                raise InputError(f"{Path(path).name}: column {name!r} not found; columns: {fields}")
        points, skipped = [], 0
        for row in reader:
            try:
                x, y = float(row[xcol]), float(row[ycol])
                if not (math.isfinite(x) and math.isfinite(y)):
                    raise ValueError
            except (TypeError, ValueError):
                skipped += 1
                continue
            points.append((x, y, (row.get(gcol) or "(빈 값)") if gcol else "전체"))
    return points, skipped


def percentile(values, q):
    ordered = sorted(values)
    k = (len(ordered) - 1) * q / 100
    lo, hi = math.floor(k), math.ceil(k)
    return ordered[lo] + (ordered[hi] - ordered[lo]) * (k - lo)


def parse_mark(text):
    try:
        coords, _, label = text.partition(":")
        x, y = (float(v) for v in coords.split(","))
    except ValueError as error:
        raise InputError(f"--mark must look like 0,0:label (got {text!r})") from error
    return x, y, label


def draw_scatter(points, overlay, marks, title, clip_pct, xlabel, ylabel, overlay_label="보조 점"):
    if not points:
        return None, {"plotted": 0}
    xs, ys = [p[0] for p in points], [p[1] for p in points]
    if clip_pct < 100:
        lo_q = (100 - clip_pct) / 2
        x0, x1 = percentile(xs, lo_q), percentile(xs, 100 - lo_q)
        y0, y1 = percentile(ys, lo_q), percentile(ys, 100 - lo_q)
    else:
        x0, x1, y0, y1 = min(xs), max(xs), min(ys), max(ys)
    for mx, my, _ in marks:
        x0, x1, y0, y1 = min(x0, mx), max(x1, mx), min(y0, my), max(y1, my)
    pad_x, pad_y = (x1 - x0) * 0.05 or 1, (y1 - y0) * 0.05 or 1
    x0, x1, y0, y1 = x0 - pad_x, x1 + pad_x, y0 - pad_y, y1 + pad_y
    inside = [p for p in points if x0 <= p[0] <= x1 and y0 <= p[1] <= y1]
    outside = len(points) - len(inside)

    width, plot_h, left, top = 1000, 640, 70, 50
    plot_w = 700
    sx = lambda v: left + (v - x0) / (x1 - x0) * plot_w
    sy = lambda v: top + plot_h - (v - y0) / (y1 - y0) * plot_h
    svg = Svg(width)
    svg.text(left, 26, title, size=17, weight="bold")
    svg.parts.append(f'<rect x="{left}" y="{top}" width="{plot_w}" height="{plot_h}" fill="none" stroke="#c9ced6"/>')
    for t in nice_ticks(x0, x1):
        svg.parts.append(f'<line x1="{sx(t):.1f}" y1="{top}" x2="{sx(t):.1f}" y2="{top + plot_h}" stroke="#eef0f3"/>')
        svg.text(sx(t), top + plot_h + 18, f"{t:g}", size=11, fill="#5f6b7a", anchor="middle")
    for t in nice_ticks(y0, y1):
        svg.parts.append(f'<line x1="{left}" y1="{sy(t):.1f}" x2="{left + plot_w}" y2="{sy(t):.1f}" stroke="#eef0f3"/>')
        svg.text(left - 8, sy(t) + 4, f"{t:g}", size=11, fill="#5f6b7a", anchor="end")
    svg.text(left + plot_w / 2, top + plot_h + 40, xlabel, size=12, anchor="middle")
    svg.text(left, top - 6, ylabel, size=11, fill="#5f6b7a")

    groups = {}
    for p in points:
        groups[p[2]] = groups.get(p[2], 0) + 1
    order = sorted(groups, key=lambda g: -groups[g])
    color = {g: PALETTE[i % len(PALETTE)] for i, g in enumerate(order)}
    radius = 2.2 if len(inside) > 3000 else 3
    for x, y, g in inside:
        svg.parts.append(f'<circle cx="{sx(x):.1f}" cy="{sy(y):.1f}" r="{radius}" fill="{color[g]}" fill-opacity="0.65"/>')
    overlay_in = [p for p in overlay if x0 <= p[0] <= x1 and y0 <= p[1] <= y1]
    for x, y, _ in overlay_in:
        svg.parts.append(f'<rect x="{sx(x) - 2.5:.1f}" y="{sy(y) - 2.5:.1f}" width="5" height="5" '
                         f'fill="none" stroke="#1f2328" stroke-width="1"/>')
    for x, y, label in marks:
        svg.parts.append(f'<path d="M{sx(x):.1f},{sy(y) - 9:.1f} l8,15 h-16 z" fill="#c23b3b" stroke="#ffffff"/>')
        if label:
            svg.text(sx(x) + 10, sy(y) - 6, label, size=12, weight="bold", fill="#c23b3b")

    lx, ly = left + plot_w + 30, top + 10
    svg.text(lx, ly, "범례 (점 수)", size=12, weight="bold")
    for g in order[:len(PALETTE)]:
        ly += 20
        svg.parts.append(f'<circle cx="{lx + 6}" cy="{ly - 4}" r="5" fill="{color[g]}"/>')
        svg.text(lx + 18, ly, f"{g} ({groups[g]})", size=12)
    if len(order) > len(PALETTE):
        ly += 20
        svg.text(lx, ly, f"그 밖 {len(order) - len(PALETTE)}개 그룹은 색이 반복됨", size=11, fill="#5f6b7a")
    if overlay:
        ly += 24
        svg.parts.append(f'<rect x="{lx + 1}" y="{ly - 9}" width="10" height="10" fill="none" stroke="#1f2328"/>')
        svg.text(lx + 18, ly, f"{overlay_label} ({len(overlay_in)}/{len(overlay)})", size=12)
    ly += 30
    svg.text(lx, ly, f"표시 {len(inside)} / 전체 {len(points)}", size=12)
    if outside:
        ly += 18
        label = f"가운데 {clip_pct:g}% 보기 범위 밖 {outside}개" if clip_pct < 100 else f"범위 밖 {outside}개"
        svg.text(lx, ly, label, size=12, fill="#c23b3b")
    summary = {"plotted": len(inside), "outside_view": outside, "groups": groups,
               "overlay_plotted": len(overlay_in), "view": [round(v, 4) for v in (x0, x1, y0, y1)],
               "colors": color}
    return svg.render(top + plot_h + 60), summary


def write_png(points, overlay, marks, summary, title, out, overlay_label="보조 점"):
    plt, note = korean_pyplot()
    if plt is None:
        return note
    x0, x1, y0, y1 = summary["view"]
    fig, ax = plt.subplots(figsize=(10, 6.4), dpi=110)
    for group, col in summary["colors"].items():
        pts = [(x, y) for x, y, g in points if g == group]
        ax.scatter([p[0] for p in pts], [p[1] for p in pts], s=6, color=col, alpha=0.65,
                   label=f"{group} ({len(pts)})")
    if overlay:
        ax.scatter([p[0] for p in overlay], [p[1] for p in overlay], s=14, marker="s",
                   facecolors="none", edgecolors="#1f2328", linewidths=0.6, label=overlay_label)
    for x, y, label in marks:
        ax.scatter([x], [y], s=90, marker="^", color="#c23b3b", zorder=5)
        ax.annotate(label, (x, y), xytext=(6, 6), textcoords="offset points", color="#c23b3b", weight="bold", zorder=6)
    ax.set_xlim(x0, x1)
    ax.set_ylim(y0, y1)
    ax.set_title(title)
    ax.legend(loc="center left", bbox_to_anchor=(1.01, 0.5), fontsize=8)
    fig.tight_layout()
    fig.savefig(out)
    plt.close(fig)
    return str(out)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)
    t = sub.add_parser("template", help="write an example map spec")
    t.add_argument("--out", type=Path, default=Path("exam-notes/problem_map.json"))
    m = sub.add_parser("map", help="spec JSON -> SVG problem map")
    m.add_argument("spec", type=Path)
    m.add_argument("--out", type=Path, default=Path("exam-notes/problem_map.svg"))
    m.add_argument("--png", action="store_true", help="also write PNG if matplotlib and a Korean font exist")
    s = sub.add_parser("scatter", help="CSV -> SVG scatter")
    s.add_argument("csv", type=Path)
    s.add_argument("--x", required=True)
    s.add_argument("--y", required=True)
    s.add_argument("--group")
    s.add_argument("--overlay", type=Path, help="second CSV drawn as hollow squares (same --x/--y unless overridden)")
    s.add_argument("--overlay-x")
    s.add_argument("--overlay-y")
    s.add_argument("--overlay-label", default="보조 점")
    s.add_argument("--mark", action="append", default=[],
                   help="x,y:label, repeatable; write --mark=-1,2:label for negative x")
    s.add_argument("--clip-pct", type=float, default=99.0,
                   help="central percentage of points that sets the view; 100 shows everything")
    s.add_argument("--title", default="데이터 분포")
    s.add_argument("--out", type=Path, default=Path("exam-notes/data_scatter.svg"))
    s.add_argument("--png", action="store_true", help="also write PNG if matplotlib and a Korean font exist")
    s.add_argument("--encoding", default="utf-8-sig", help="CSV encoding, e.g. cp949 for Excel-saved Korean files")
    args = parser.parse_args(argv)
    try:
        if args.command == "template":
            if args.out.exists():
                raise InputError(f"{args.out} already exists; not overwriting")
            args.out.parent.mkdir(parents=True, exist_ok=True)
            args.out.write_text(json.dumps(TEMPLATE, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            result, code = {"status": "ok", "written": str(args.out)}, 0
        elif args.command == "map":
            try:
                spec = json.loads(args.spec.read_text(encoding="utf-8"))
            except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
                raise InputError(f"cannot read spec: {error}") from error
            drawing, summary = build_map(spec)
            if drawing is None:
                result, code = {"status": "nothing_to_draw", **summary}, 2
            else:
                args.out.parent.mkdir(parents=True, exist_ok=True)
                args.out.write_text(drawing.render(), encoding="utf-8")
                result, code = {"status": "ok", "written": str(args.out), **summary}, 0
                if args.png:
                    result["png"] = drawing.png(args.out.with_suffix(".png"))
        else:
            if not 50 <= args.clip_pct <= 100:
                raise InputError("--clip-pct must be between 50 and 100")
            points, skipped = read_points(args.csv, args.x, args.y, args.group, args.encoding)
            overlay, overlay_skipped = [], 0
            if args.overlay:
                overlay, overlay_skipped = read_points(args.overlay, args.overlay_x or args.x,
                                                       args.overlay_y or args.y, encoding=args.encoding)
            marks = [parse_mark(m) for m in args.mark]
            svg, summary = draw_scatter(points, overlay, marks, args.title, args.clip_pct, args.x, args.y,
                                        args.overlay_label)
            base = {"rows_read": len(points) + skipped, "skipped_non_numeric": skipped,
                    "overlay_skipped_non_numeric": overlay_skipped}
            if svg is None:
                result, code = {"status": "nothing_to_draw", **base, **summary}, 2
            else:
                args.out.parent.mkdir(parents=True, exist_ok=True)
                args.out.write_text(svg, encoding="utf-8")
                png = write_png(points, overlay, marks, summary, args.title, args.out.with_suffix(".png"),
                                args.overlay_label) \
                    if args.png else None
                summary.pop("colors")
                result = {"status": "ok", "written": str(args.out), **base, **summary}
                if png:
                    result["png"] = png
                code = 0
    except (InputError, OSError) as error:
        print(json.dumps({"status": "error", "error": str(error)}, ensure_ascii=False), file=sys.stderr)
        return 1
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
