---
name: sk-exam-design
description: "SK AI 시험 운영 중 첫 설계 또는 요구 변경에서 범위·구조·실패 경로를 검토할 때 사용한다. 운영 스킬이 이 단계로 연결하거나 참가자가 명시 요청하면 적용한다."
---

# 설계 검토

이 파일은 원본과 별개로 작성한 시험용 연결 스킬이다. 원본을 실제로 읽고 허용된 절차를 적용한다. 원본 전체 런타임 실행과 구분한다.

## 먼저 읽을 파일

1. 형제 폴더 `../sk-ai-exam-operator/references/skill-routing.md`의 공통 실행 계약.
2. 형제 운영 스킬의 `upstream/gstack/plan-eng-review/SKILL.original.md` 원본 전체. 아래 지원 문서의 경로는 해당 프로젝트의 `upstream/gstack/` 기준이다.

최초 적용에는 위 원본을 읽는다. 동일 버전 원본과 공통 계약이 현재 문맥에 남아 있는 재진입에는 재사용하고 필요한 절만 확인한다. 문맥을 잃거나 파일이 바뀌면 다시 읽고, 실제 최초 읽기와 재사용을 구분한다.

원본이 없거나 잠금 해시가 맞지 않으면 원본 적용 성공으로 표시하지 않는다. 문제를 짧게 알리고 운영 스킬의 기본 도구로 가능한 작업을 이어간다. 준비되지 않은 명령·별도 런타임을 설치하지 않는다.

## 현재 단계의 적용

- 원본과 `plan-eng-review/sections/review-sections.md`의 Architecture / Code Quality / Tests / Performance 중 실제 과제에 관련된 절을 읽는다. `sections/checklist.md`는 누락 점검용이며 상세 절 읽기를 대신하지 않는다.
- 입력→업무 규칙→상태·저장→사용자 결과→실패 복구를 실제 파일·제약에 맞춰 검토한다. 선택지의 이익·비용·실패 조건을 비교하고 가장 작은 충분한 구조를 제안한다.
- 의사결정 기록은 `04_decisions.md`, 기능·완료 조건은 `02_requirements.md`, 예외는 `03_exceptions.md`에 연결한다.
- gstack 시작·종료 바이너리, telemetry·brain sync·외부 모델·브라우저·Aside·question preference·review army는 실행하지 않는다. 런타임 로그나 공식 gstack 통과 판정을 생성한 것으로 말하지 않는다. 설계가 충분하고 실행이 이미 승인됐으면 사용자에게 다시 진행 허가를 묻지 않고 계획 단계로 이어간다.

## 결과 연결

현재 사용한 스킬·원본 경로·원본 적용 범위·중요 생략을 `05_verification.md`의 스킬 적용 기록에 짧게 남긴다. 세 세션 운영이면 세션 1은 `exam-notes/10_work_log.md`, 세션 2는 `exam-notes/20_review.md`에 같은 내용을 남기고 세션 3이 01~05로 옮긴다. 파일을 읽은 사실과 검사 실행·기능 완료는 별개다. 끝나면 운영 스킬로 돌아가 남은 시간과 실제 상태에 맞는 다음 한 작업을 이어간다.
