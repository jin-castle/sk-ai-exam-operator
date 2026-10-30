#!/usr/bin/env python3
"""Maintain local exam notes and advisory windows from user-reported minutes.

No model, network, browser, scheduler, or elapsed-clock inference is used.
Only the managed status files are replaced; existing note content is preserved.
"""

import argparse
from datetime import datetime, timezone
import json
import math
from pathlib import Path
import sys
import tempfile


OWNER = "sk-ai-exam-operator"
MARKER = "<!-- managed-by: sk-ai-exam-operator -->"
TOTAL = 180
NOTES = (
    "01_domain.md", "02_requirements.md", "03_exceptions.md",
    "04_decisions.md", "05_verification.md",
)
WINDOWS = (
    (8, "inspect", "과제·자료 확인", "기본 파일 조사"),
    (20, "interview", "업무 사례 인터뷰", "Ouroboros interview 관점"),
    (30, "rules", "규칙·예외·수용 기준", "Ouroboros interview 관점"),
    (40, "plan", "최소 설계", "gstack plan-eng-review 관점"),
    (65, "prototype", "첫 사용자 흐름 구현", "기본 구현·규칙 검사"),
    (80, "test", "직접 사용·반례 검사", "참가자 수동 UI·코드 검사"),
    (105, "improve", "원인 확인·최소 개선", "Superpowers debugging·code-review 관점"),
    (125, "complete-flow", "필수 흐름 끝단·실패 처리", "기본 구현·디버깅"),
    (145, "review", "통합 검증·변경 리뷰", "gstack review·완료 전 검증 관점"),
    (165, "explain", "본인 설명·코드 일치 확인", "기본 코드 대조"),
    (180, "final", "저장·실행·제출 확인", "Superpowers verification-before-completion 관점"),
)


def checked_remaining(value):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("remaining must be a finite number of minutes")
    if not math.isfinite(value) or not 0 <= value <= TOTAL:
        raise ValueError("remaining must be between 0 and 180 minutes")
    return value


def window_for(remaining):
    if remaining is None:
        return {"id": "unconfirmed", "label": "잔여 시간 미확인", "skill": "기본 자료 확인"}
    checked_remaining(remaining)
    if remaining == 0:
        return {"id": "expired", "label": "과제 시간 종료", "skill": "개발·검사 작업 중단"}
    elapsed = TOTAL - remaining
    for end, key, label, skill in WINDOWS:
        if elapsed < end:
            return {"id": key, "label": label, "skill": skill}
    raise ValueError("invalid timing window")


def safe_file(path):
    if path.is_symlink() or (path.exists() and not path.is_file()):
        raise ValueError(f"refusing linked or non-file target: {path.name}")


def load_state(path):
    safe_file(path)
    state = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(state, dict) or state.get("owner") != OWNER or state.get("schema_version") != 1:
        raise ValueError("existing state is not owned by this operator; preserving it")
    if state.get("total_minutes") != TOTAL:
        raise ValueError("existing total differs from the 180-minute contract")
    timer = state.get("timer")
    if not isinstance(timer, dict) or "last_reported_remaining" not in timer:
        raise ValueError("existing timer state is incomplete; preserving it")
    remaining = timer["last_reported_remaining"]
    if remaining is not None:
        checked_remaining(remaining)
        if timer.get("source") != "user_report" or not isinstance(timer.get("reported_at_utc"), str):
            raise ValueError("existing time has no user-report provenance")
    elif timer.get("source") != "unconfirmed":
        raise ValueError("unconfirmed timer has invalid provenance")
    return state


def atomic_write(path, content):
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", newline="\n",
                                         dir=path.parent, prefix=".operator-", delete=False) as output:
            temporary = Path(output.name)
            output.write(content)
        temporary.replace(path)
    finally:
        if temporary is not None and temporary.exists():
            temporary.unlink()


def response_for(state, *, supplied=False, increased=False):
    timer = state["timer"]
    remaining = timer["last_reported_remaining"]
    return {
        "last_reported_remaining": remaining,
        "time_source": timer["source"],
        "new_user_report_recorded": supplied,
        "reported_at_utc": timer["reported_at_utc"],
        "advisory_window": window_for(remaining),
        "time_increased_by_user_correction": increased,
        "actual_work_stage": "decide from task, notes, code, and actual verification",
        "timer_notice": "마지막 사용자 보고이며 실시간 타이머가 아님. 새 시간 보고가 없으면 감소·초기화하지 않음.",
    }


def render_status(state):
    info = response_for(state)
    timer = state["timer"]
    remaining = timer["last_reported_remaining"]
    shown = "미확인" if remaining is None else f"{remaining:g}분 (마지막 사용자 보고)"
    timing = info["advisory_window"]
    return (
        f"{MARKER}\n# 시험 운영 상태\n\n"
        f"- 계획 기준: {TOTAL}분\n- 남은 시간: {shown}\n"
        f"- 보고 기록 시각(UTC, 잔여 시간 계산에 사용하지 않음): {timer['reported_at_utc'] or '미확인'}\n"
        f"- 마지막 보고에 따른 권고 구간: {timing['label']}\n"
        f"- 참고 도구: {timing['skill']}\n\n"
        "권고 구간은 실제 진행 완료를 의미하지 않는다. 업무 단계·성공 기준·실제 검증은 본문 기록을 확인한다.\n"
        "AI 금지 후속 서술형에 들어가면 기록 갱신을 포함한 AI 지원을 멈춘다.\n"
    )


def session(command, root, remaining=None):
    root = Path(root).absolute()
    if root.is_symlink() or (root.exists() and not root.is_dir()):
        raise ValueError("notes root must be a normal directory")
    state_path = root / ".operator-state.json"
    status_path = root / "00_status.md"
    if remaining is not None:
        checked_remaining(remaining)

    if command == "status":
        return response_for(load_state(state_path))
    if command not in ("init", "checkpoint"):
        raise ValueError("unsupported session command")

    templates = Path(__file__).resolve().parents[1] / "assets" / "templates"
    safe_file(state_path)
    safe_file(status_path)
    if status_path.exists() and not status_path.read_text(encoding="utf-8").startswith(MARKER + "\n"):
        raise ValueError("existing 00_status.md is not managed; preserving it")
    if state_path.exists():
        state = load_state(state_path)
    elif command == "checkpoint":
        raise ValueError("session not initialized; inspect existing notes before init")
    else:
        state = {
            "owner": OWNER, "schema_version": 1, "total_minutes": TOTAL,
            "timer": {"last_reported_remaining": None, "source": "unconfirmed", "reported_at_utc": None},
        }

    additions = []
    for name in NOTES:
        target = root / name
        safe_file(target)
        if command == "init" and not target.exists():
            additions.append((target, (templates / name).read_text(encoding="utf-8")))

    previous = state["timer"]["last_reported_remaining"]
    increased = remaining is not None and previous is not None and remaining > previous
    if remaining is not None:
        state["timer"] = {
            "last_reported_remaining": remaining,
            "source": "user_report",
            "reported_at_utc": datetime.now(timezone.utc).isoformat(),
        }
    root.mkdir(parents=True, exist_ok=True)
    for path, content in additions:
        with path.open("x", encoding="utf-8", newline="\n") as output:
            output.write(content)
    atomic_write(state_path, json.dumps(state, ensure_ascii=False, indent=2) + "\n")
    atomic_write(status_path, render_status(state))
    return response_for(state, supplied=remaining is not None, increased=increased)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    for name in ("init", "checkpoint", "status"):
        part = commands.add_parser(name)
        part.add_argument("--root", type=Path, default=Path("exam-notes"))
        if name != "status":
            part.add_argument("--remaining", type=float, help="minutes explicitly reported by the participant")
    args = parser.parse_args()
    try:
        result = session(args.command, args.root, getattr(args, "remaining", None))
    except (OSError, ValueError, TypeError, KeyError) as error:
        print(json.dumps({"error": str(error)}, ensure_ascii=False), file=sys.stderr)
        return 2
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
