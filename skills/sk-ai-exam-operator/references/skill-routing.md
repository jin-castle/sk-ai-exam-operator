# 원본 스킬 팩과 단계별 호출

이 팩은 운영 스킬 1개와 단계별 연결 스킬 10개를 제공한다. 연결 스킬은 실제 원본을 읽어 적용하며 이름만 제시하고 끝내지 않는다. 원본의 파일 바이트와 LICENSE를 보존한다. 자동 발견 시 지원되지 않는 원본까지 등록되는 것을 막기 위해 원본의 `SKILL.md` 파일명만 `SKILL.original.md`로 바꿨다. 매핑·출처·SHA256은 운영 폴더의 `bundle-lock.json`에 있다.

## 공통 실행 계약

- 자료는 제공 환경 안에서 허용된 AI·파일·터미널 도구의 Git Clone/HTTP 다운로드로 가져온다. 외부 브라우저 창·탭을 열거나 직접 접근을 안내하지 않는다. 다운로드 차단을 다른 경로·설정으로 우회하지 않는다. 질문 초안은 참가자의 직접 검토 후 사용하며, 외부 완성 결과물로 제출물을 통째로 대체하지 않는다.

- **세 세션 운영의 기록 위치**: 연결 스킬이 `01_domain.md`~`05_verification.md`(스킬 적용 기록 포함)에 쓰라고 하면, 세션 1은 `exam-notes/10_work_log.md`, 세션 2는 `exam-notes/20_review.md`에 같은 내용을 남긴다. 01~06은 세션 3만 쓴다. 한 세션 운영이면 지시대로 01~05에 쓴다. 다른 세션이 쓴 파일은 고치지 않는다.
- **재실행 출력 분리**: 세션 2·3이 과제 명령을 다시 실행할 때 출력은 `exam-notes/review/`나 임시 폴더로 보내고, 설정을 바꿔야 하면 복사본을 쓴다. 세션 1의 결과물·설정을 덮어쓰지 않는다. 출력 위치를 바꿀 수 없으면 실행하지 말고 발견·미검증으로 남긴다.
- 과제의 요구·최신 응시 안내·사용자가 승인한 운영 흐름이 우선한다. AI 금지 후속 단계·시간 만료 보고는 모든 하위 스킬에 앞서 확인한다. 운영 스킬의 기록·판단 출처·잔여 시간 규칙을 그대로 적용한다.
- 첫 시작 시 팩 검증을 한 번 한다. 저장소에서는 `python -X utf8 -B scripts/check_bundle.py --root .`, 설치 후에는 `python -X utf8 -B ACTUAL_OPERATOR_DIR/scripts/check_bundle.py --installed-root ACTUAL_SKILLS_PARENT`를 사용한다. 경로는 실제 설치 위치로 바꾼다. Python이 없으면 기본 파일 도구로 11개 SKILL.md와 잠금 파일에 적힌 원본·LICENSE·지원 문서를 확인하고 해시 확인 불가를 밝힌다. 새 런타임을 설치하지 않는다.
- 현재 스킬 목록·파일 경로를 확인한다. 호스트가 실제 Skill 호출 도구를 제공하면 정확한 이름으로 호출한다. 그런 도구가 없거나 목록 반영이 지연됐으면 해당 연결 스킬의 **실제 SKILL.md를 파일 도구로 읽고**, 지정된 원본과 필요한 지원 문서를 읽어 현재 대화에서 수행한다. 가짜 slash 명령·존재하지 않는 도구를 만들지 않는다. 이는 파일 기반 적용이며 호스트의 정식 등록 성공과 구분한다.
- 해당 버전 원본을 처음 적용할 때 전체를 읽고 지원 문서는 필요한 것만 추가한다. 동일 버전의 원본·공통 계약이 현재 문맥에 남아 있으면 재진입 때 재사용하고 필요한 절만 다시 확인한다. 압축·세션 변경으로 내용을 잃었거나 버전·파일이 바뀌면 관련 원본과 계약을 다시 읽는다. 재사용은 앞선 실제 읽기 기록에 연결하며, 읽지 않은 원본을 적용했다고 기록하지 않는다. 원본 내부의 상대 경로는 `upstream/<project>/`의 같은 상대 위치로 매핑한다. 원본이 `SKILL.md`를 가리키면 실제 포함된 `SKILL.original.md`로 매핑한다. `~/.claude/skills/gstack/` 경로도 포함된 `upstream/gstack/` 문서 경로로 매핑하되 없는 실행 바이너리를 실행하지 않는다.
- 적용은 **시험용 연결 스킬 + 원본 절차의 제한 적용**이다. gstack의 전체 런타임, 원본 모든 gate 통과, Ouroboros MCP 실행을 했다고 말하지 않는다. 생략한 외부 호출·작업공간 도구·독립 검토와 실제 적용한 절차를 구분한다.
- 기본 방식은 현재 제공 환경의 inline 구현이다. 허용 모델·설정을 바꾸거나 외부 AI·개인 키·Codex 업데이트·MCP·Bun·uvx·새 런타임을 설치하지 않는다. Computer Use·자동 브라우저·원격 PR/댓글/telemetry·시험자료 외부 전송·Git Push를 하지 않는다. 원본 명령을 일괄 복사해 실행하지 않는다.
- 재승인으로 단계마다 멈추지 않는다. 이미 승인된 가역적 계획·구현·검사·기록은 계속하고 업무 정책의 중요한 공백만 참가자에게 확인한다. 참가자가 원본에 없는 이유·선택·검사 결과를 했다고 쓰지 않는다.

## 실제 단계별 연결

| 역할 | 상황 | 읽어 적용할 연결 스킬 | 원본 |
|---|---|---|---|
| 1(한 세션)·3(세 세션) | 시작 직후 문제 구조화·시각화 | `sk-exam-frame` | Superpowers brainstorming(Visual Companion 서버 제외) |
| 1 | 초반 업무 사례·규칙·예외, 또는 새 정책 공백 | `sk-exam-interview` | Ouroboros interview + socratic-interviewer/seed-closer |
| 1 | 최소 설계·요구 변화 | `sk-exam-design` | gstack plan-eng-review + 관련 상세 절 |
| 1 | 설계가 정해졌고 구현 작업 분해 필요 | `sk-exam-plan` | Superpowers writing-plans |
| 1 | 첫 흐름·필수 기능 구현, 검토 발견 반영 | `sk-exam-implement` | Superpowers executing-plans |
| 1·2 | 규칙별 검사(1), 독립 검산·실패 먼저(2) | `sk-exam-test` | Superpowers test-driven-development |
| 1 | 재현된 실패 | `sk-exam-debug` | Superpowers systematic-debugging |
| 1 | 중요한 AI 수정 제안 | `sk-exam-review-response` | Superpowers receiving-code-review |
| 2 | 통합 변경·누락·회귀 검토, 조건 변경 재실행 | `sk-exam-review` | gstack review + checklist/관련 specialist |
| 1·2·3 | 최종 저장·제출 확인(1), 마지막 변경 뒤 재검사(2), 문서 주장과 코드·검사 대조(3) | `sk-exam-verify` | Superpowers verification-before-completion |

역할별 절차는 roles.md, 시간 기준은 operation.md를 따른다. 스킬 10개를 매번 차례로 모두 실행하지 않는다. 실제 정책·구현 상태에 필요한 단계를 고르며, 테스트·디버깅·제안 심사는 중간에 재진입할 수 있다. 남은 15분 이내에는 verify를 우선하고 제출을 막는 결함의 가능한 최소 수정에만 debug/test/implement를 연결한다.

## 스킬 적용 기록

`05_verification.md`에 기존 형식을 해치지 않는 짧은 기록을 추가한다.

| 단계/기능 | 연결 스킬 | 실제 읽은 원본·지원 파일 | 적용·중요 생략 | 실행 근거/미검증 |
|---|---|---|---|---|

기록은 실제로 읽고 수행한 뒤 작성한다. 스킬 파일 읽기는 테스트 통과가 아니다. 같은 단계의 반복 기록은 바뀐 사실만 갱신한다. 이 기록을 위해 별도 중복 문서를 만들거나 참가자의 판단 이력을 연출하지 않는다.
