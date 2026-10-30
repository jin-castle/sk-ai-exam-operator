# 시험 시작 시 한 번 입력할 설치·시작 프롬프트 — v2.0.0

공개 저장소: https://github.com/jin-castle/sk-ai-exam-operator · 고정 ref: `v2.0.0`.

이 버전은 운영 스킬 1개 + 단계별 연결 스킬 9개, 원본 3프로젝트의 고정 소스·지원 문서·LICENSE를 함께 설치합니다. 연결 스킬은 원본을 실제 읽어 시험 조건 안에서 수행하며, gstack/Ouroboros의 전체 런타임 설치·실행을 의미하지 않습니다.

## 복사할 프롬프트

`180분`은 화면에서 실제 확인한 값으로 바꿉니다. 확인하지 못했으면 해당 문장을 뺍니다.

```text
공개 저장소 https://github.com/jin-castle/sk-ai-exam-operator 의 고정 ref v2.0.0에서
운영 스킬과 단계별 원본 기반 스킬 팩을 함께 설치하고, 현재 대화에서 시험 운영을 시작해줘.

기본 skill-installer의 install-skill-from-github.py를 찾아 사용해줘.
--repo jin-castle/sk-ai-exam-operator --ref v2.0.0 으로
다음 10개 경로를 --path에 모두 전달해 한 번에 설치해줘:
skills/sk-ai-exam-operator
skills/sk-exam-interview
skills/sk-exam-design
skills/sk-exam-plan
skills/sk-exam-implement
skills/sk-exam-test
skills/sk-exam-debug
skills/sk-exam-review-response
skills/sk-exam-review
skills/sk-exam-verify

먼저 대상 10개 폴더의 존재 여부를 확인해줘. 하나라도 이미 있으면 삭제·덮어쓰기하지 말고, 과제 자료와 분리된 도구 폴더 아래
충돌 없는 새 디렉터리를 --dest로 지정해 10개를 모두 설치하고 그 실제 경로를 사용해줘.
기본 installer가 없으면 허용된 공개 다운로드로 이 ref의 저장소를 도구 폴더에 받아
skills/의 10개 실제 파일을 직접 읽어 적용해줘. 새로운 installer·런타임은 설치하지 마.
네트워크·권한이 막히면 우회하지 말고, 설치 완료라고 하지 않은 채 가능한 기본 도구로 진행해줘.

설치한 운영 폴더의 scripts/check_bundle.py를 읽고, 기존 Python이 있으면 -X utf8 -B 옵션을 붙여
--installed-root 실제_10개_스킬의_부모폴더 로 실행해 10개 진입점·원본 해시·LICENSE를 확인해줘.
다운로드한 체크아웃을 그대로 쓸 때에는 저장소의 scripts/check_bundle.py --root 실제_저장소경로 를 써줘.
Python이 없으면 파일 존재·경로를 확인하고 해시 검증 불가를 구분해줘.

운영 스킬의 실제 SKILL.md와 references/skill-routing.md를 지금 읽어 적용해줘.
호스트 목록 반영을 기다리느라 운영을 멈추지 말고, 목록 반영 전에는 파일 기반 적용이라고 밝혀줘.
이후 단계마다 해당 sk-exam-*의 실제 SKILL.md와 지정 원본·필요한 지원 문서를 읽어 수행해줘.
이름을 추천하는 데서 끝내지 말고 구현·검사까지 이어가되, 원본 전체 런타임 실행과 구분해줘.
설치 문제에 약 3분 이상 매달리지 마. 누락·제한이 있으면 알려주고 가능한 작업을 계속해줘.

화면에서 확인한 남은 시간은 180분이야.
먼저 과제 원문·제공 자료·기존 코드·실행 방법을 확인해줘.
파일로 확인할 사실은 직접 조사하고, 담당자에게 물을 업무 정책·우선순위·예외만 좁혀줘.
담당자와의 대화와 UI 확인은 내가 직접 하고 답변을 전달할게.
답변을 규칙·기능·필요 조건·예외·판단·검증 MD로 연결해줘.
현재 제공 작업공간에서 inline 구현을 기본으로 진행하고, 남은 시간과 실제 상태에 따라
인터뷰→설계→계획→구현↔검사·디버깅→통합 리뷰→최종 검증을 선택해 이어가줘.
실제로 사용한 연결 스킬·원본·적용 범위·중요 생략은 05_verification.md에 짧게 남겨줘.

제공 Codex·허용 모델·최신 응시 안내를 우선하고, Codex 업데이트·외부 AI·개인 키·Astra·
MCP/새 런타임 설치·Computer Use·자동 브라우저·시험자료 외부 전송·Git Push는 하지 마.
원본의 telemetry·외부 리뷰·자동 merge/push·worktree 전환·작업공간 삭제는 실행하지 마.
이미 요청한 가역적 계획·구현·검사·기록은 매 단계 재승인을 묻지 말고 계속해줘.
미확인 업무 정책만 확인하고, 내가 말하지 않은 판단 이유나 실행하지 않은 검사 결과는 만들지 마.
AI 금지 후속 서술형 단계 또는 과제 시간 만료를 알리면 작업을 멈춰줘.
```

한 번 입력하면 이 대화에서 운영이 이어집니다. 스킬 파일을 설치한 사실·파일로 적용한 사실·호스트 목록에 정식 반영된 사실을 구분합니다. 설치 실패 시 기본 도구로 진행한 것은 원본 팩 설치 성공이 아닙니다.

## 설치 도우미의 정확한 인수

기본 도우미가 이미 있는 환경에서 사용하는 인수 예시입니다. 도우미 경로와 Python 실행기는 현재 환경에서 확인합니다.

```text
python -X utf8 -B EXISTING_INSTALLER_PATH --repo jin-castle/sk-ai-exam-operator --ref v2.0.0 --path skills/sk-ai-exam-operator skills/sk-exam-interview skills/sk-exam-design skills/sk-exam-plan skills/sk-exam-implement skills/sk-exam-test skills/sk-exam-debug skills/sk-exam-review-response skills/sk-exam-review skills/sk-exam-verify
```

설치 경로가 이미 있으면 공식 도우미는 중단합니다. 충돌 없는 별도 `--dest`를 쓰면 기존 스킬을 보존하면서 팩 전체를 받을 수 있습니다. 재실행 시 일부만 설치된 상태를 완료로 표시하지 않습니다.

## 설치 후 다음 턴에 명시 호출할 때

```text
$sk-ai-exam-operator 시험 운영을 이어가줘.
화면에서 확인한 남은 시간은 180분이야.
설치된 단계별 연결 스킬과 원본을 실제 읽어 적용하면서 MD 기록·구현·검사를 이어가줘.
```

## 진행 중 전달

```text
담당자 답변: [실제로 받은 답변]
확인된 규칙과 미확인을 구분하고 관련 기능·예외·검사를 MD에 연결해줘.
```

```text
화면에서 확인한 남은 시간은 72분이야.
관찰한 동작: [실제 내용]. 문제: [재현 절차와 현상].
다음 작업과 필요한 연결 스킬을 골라 진행해줘.
```

```text
AI 제안은 [실제 제안]이었고, 나는 [채택/수정/기각/보류]할게.
이유는 [내 실제 이유]야. 근거와 검증을 연결해줘.
```

```text
지금 AI 금지 후속 서술형 단계에 들어갔어. 지원을 멈춰줘.
```
