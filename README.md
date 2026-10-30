# SK AI Exam Operator — v2.2.0 원본 포함 스킬 팩

SK AI 해커톤·Probe의 180분 과제에서 담당자 답변을 업무 규칙·기능·예외·판단·검증 MD로 연결하고, 남은 시간과 실제 상태에 따라 인터뷰·계획·구현·테스트·개선을 이어가는 개인 운영 팩입니다. 대회나 원본 프로젝트의 공식 시험 스킬은 아닙니다.

**[시험 시작 때 한 번 입력할 설치·시작 프롬프트](EXAM_PROMPTS.md)**를 사용하세요. 고정 ref는 `v2.2.0`입니다. 기존 버전 태그는 이동하지 않습니다.

## v2.2.0 실행 근거 검사

- 선택적 `evidence_guard.py`가 등록한 필수 항목과 실제 검사 명령을 연결합니다.
- 관련 소스·설정·입력·테스트의 내용과 파일 메타데이터를 실행 전후·현재 시점에 비교합니다. 일반적인 임시 수정 후 복원도 재검사를 요구합니다.
- 최신 실패·시간 초과·실행 불가·거부된 검사, 누락되거나 변경된 로그를 과거 성공으로 가리지 않습니다.
- 상태 조회는 읽기 전용이며, 기존 본문 MD·타이머를 수정하지 않습니다. Python 표준 라이브러리만 사용합니다.
- [사용법과 감지 범위](skills/sk-ai-exam-operator/references/evidence-guard.md)를 확인하세요. 등록한 항목·지정한 파일 범위의 실행 기록 검사이며, 업무 정답·테스트 충분성·수동 UI 확인을 자동 판정하지 않습니다.

## v2.1.0 운영 보완

- 주요 선택·첫 흐름에서 참가자가 먼저 설명하고 실제 코드와 대조한다. 답변이 없으면 이해 미확인으로 둔다.
- 현재 문맥에 남은 동일 버전 원본은 재사용하고, 문맥·버전 변경 때 다시 읽는다.
- 과제에 해당하는 입력·권한·민감 정보·저장 위험을 실제 검사 또는 미검증 이유에 연결한다.
- 스킬 사용량보다 사용자 흐름과 업무 반례를 우선한다. [모의 검증 방법과 결과](VALIDATION.md)를 참고한다.

원본을 직접 설치할지 고민한다면 [원본과 시험용 팩 비교](CHOOSING_SKILLS.md)를 참고하세요. 시험용 팩은 원본보다 코딩 능력이 높다는 주장이 아니라, 시험 조건에 맞춘 운영 계층입니다.

## 함께 설치되는 10개 진입점

| 스킬 이름 | 역할·원본 |
|---|---|
| `sk-ai-exam-operator` | 운영·시간·MD·단계 연결 |
| `sk-exam-interview` | ouroboros · interview |
| `sk-exam-design` | gstack · plan-eng-review |
| `sk-exam-plan` | superpowers · writing-plans |
| `sk-exam-implement` | superpowers · executing-plans |
| `sk-exam-test` | superpowers · test-driven-development |
| `sk-exam-debug` | superpowers · systematic-debugging |
| `sk-exam-review-response` | superpowers · receiving-code-review |
| `sk-exam-review` | gstack · review |
| `sk-exam-verify` | superpowers · verification-before-completion |

운영 스킬이 상황에 맞는 연결 스킬의 실제 `SKILL.md`, 해당 원본과 필요한 지원 문서를 읽고 적용합니다. 같은 시험 대화에서 참가자가 스킬을 매번 호출할 필요는 없습니다. 호스트의 실제 호출 도구가 없거나 목록 반영 전이라면 파일 기반 적용으로 진행하고 그 사실을 구분합니다.

## 원본이 실제로 포함되는 범위

- Superpowers: `skills/` 전체 원본·지원 파일, MIT LICENSE.
- gstack: `plan-eng-review/`, `review/`의 원본·지원 파일, MIT LICENSE.
- Ouroboros: interview 원본, socratic-interviewer·seed-closer 보조 프롬프트, MIT LICENSE.

고정 커밋의 **124개 원본 파일을 바이트 그대로 보존**했습니다. 이 수는 원본 스킬 지침 18개와 지원 파일 106개의 합계이며, 설치 진입점은 위의 10개입니다. 원본 `SKILL.md`의 파일명만 `SKILL.original.md`로 저장해 호스트가 지원되지 않는 원본을 별도 스킬로 자동 등록하는 것을 막습니다. [잠금 파일](skills/sk-ai-exam-operator/bundle-lock.json)에 원래 경로·저장 경로·SHA256, [원본 고지](THIRD_PARTY_NOTICES.md)에 출처와 LICENSE가 있습니다. 원본은 운영 스킬 하위 `upstream/`에 함께 설치되고, 9개 연결 스킬은 그 파일을 사용합니다.

원본의 전체 실행 환경까지 설치하지는 않습니다. gstack의 바이너리·Bun·브라우저·telemetry·외부 모델, Ouroboros의 MCP·uvx, Superpowers의 자동 작업공간 전환·merge/push 등은 실행하지 않습니다. 연결 스킬이 원본 절차 중 실제 적용한 부분과 중요 생략을 기록합니다. [호출 계약](skills/sk-ai-exam-operator/references/skill-routing.md)을 참고하세요.

## 설치와 확인

기본 `skill-installer`에서 [설치 프롬프트](EXAM_PROMPTS.md)에 나열한 **10개 경로를 함께 설치**해야 합니다. 운영 스킬 하나만 설치하면 원본은 포함되지만 9개 연결 진입점은 누락됩니다. 기존 대상이 있으면 덮어쓰지 않고 충돌 없는 별도 `--dest`에 팩 전체를 설치해 파일로 적용할 수 있습니다. 목록 등록을 위해 제공 Codex를 업데이트하지 않습니다.

기존 Python으로 체크아웃 검증:

```text
python -X utf8 -B scripts/check_bundle.py --root .
python -X utf8 -B -m unittest discover -s tests -v
```

설치 후 검증:

```text
python -X utf8 -B ACTUAL_OPERATOR_DIR/scripts/check_bundle.py --installed-root ACTUAL_SKILLS_PARENT
```

검증기는 10개 진입점·원본 고정 커밋·124개 SHA256·LICENSE·경로·연결을 읽기 전용으로 확인합니다. 이 결과는 원본 전체 런타임 동작이나 실제 시험 PC 호환성의 증명이 아닙니다. Python이 없으면 파일 확인으로 진행하고 해시 검증 불가를 밝힙니다. 새 런타임이 필요하지 않습니다.

## 기록과 시간 운영

현재 과제의 `exam-notes/` 또는 기존 지정 양식을 사용합니다.

| 기본 문서 | 내용 |
|---|---|
| `01_domain.md` | 담당자 답변·규칙·근거·미확인 |
| `02_requirements.md` | 기능·필요 조건·수용 기준·짧은 실행 계획 |
| `03_exceptions.md` | 예외·기대 처리·코드·검사 연결 |
| `04_decisions.md` | 실제 AI 제안·참가자의 실제 선택과 이유 |
| `05_verification.md` | 실제 검사·시스템 흐름·한계·스킬 적용 기록 |

잔여 시간은 참가자가 실제 화면에서 확인해 전달한 값만 사용합니다. 자동 타이머·알람·브라우저·제출 자동화는 없습니다. 이미 확인한 정책·기존 구현·검사 기록을 재사용합니다. 선택적 `exam_session.py`는 시간 보고와 빈 양식을 관리하며 본문을 덮어쓰지 않습니다.

## 사용 경계

최신 응시 안내와 제공 환경의 허용 범위가 우선합니다. 실제 과제 데이터·답변·로그를 이 공개 저장소로 Push하지 않습니다. 참가자가 밝히지 않은 판단 이유나 실행하지 않은 테스트 결과를 만들지 않습니다. AI 금지 후속 서술형에 들어갔다는 보고가 오면 문항 분석·답안·첨삭·파일 작업을 멈춥니다.

## 도구·자료 안내에 맞춘 반입

개인 사전 제작 지침·Skill·템플릿·코드의 공개 후 반입 허용 안내에 맞춰 구성했습니다. 응시 환경 안에서 AI를 통해 Git Clone/HTTP 다운로드로 받으며 외부 브라우저 직접 접근·개인 PC 파일 업로드·시험자료 외부 전송·Git Push·차단 우회를 하지 않습니다. 질문 초안은 참가자가 직접 검토한 뒤 사용하고, 외부 완성 결과물로 제출물을 통째로 대체하지 않습니다. 사용한 저장소는 2차 예선 결과 통지 전까지 공개 상태를 유지해야 합니다. 이 설명은 제공된 안내와의 대조이며 주최사의 별도 승인·평가 결과를 보장하지 않습니다.
