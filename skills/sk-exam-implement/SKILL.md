---
name: sk-exam-implement
description: "SK AI 시험 운영 중 확정된 기능과 실행 계획을 작은 단위로 구현할 때 사용한다. 운영 스킬이 이 단계로 연결하거나 참가자가 명시 요청하면 적용한다."
---

# 계획 실행

이 파일은 원본과 별개로 작성한 시험용 연결 스킬이다. 원본을 실제로 읽고 허용된 절차를 적용한다. 원본 전체 런타임 실행과 구분한다.

## 먼저 읽을 파일

1. 형제 폴더 `../sk-ai-exam-operator/references/skill-routing.md`의 공통 실행 계약.
2. 형제 운영 스킬의 `upstream/superpowers/skills/executing-plans/SKILL.original.md` 원본 전체. 아래 지원 문서의 경로는 해당 프로젝트의 `upstream/superpowers/` 기준이다.

원본이 없거나 잠금 해시가 맞지 않으면 원본 적용 성공으로 표시하지 않는다. 문제를 짧게 알리고 운영 스킬의 기본 도구로 가능한 작업을 이어간다. 준비되지 않은 명령·별도 런타임을 설치하지 않는다.

## 현재 단계의 적용

- 계획과 업무 근거를 함께 읽고 첫 미완료 작업부터 직접 구현한다. 원본의 brief→작업→검사→완료 조건 확인→ledger 갱신 순서를 적용한다. `02_requirements.md`의 기존 작업 상태를 ledger로 재사용한다.
- 기능의 의미를 정하는 정책 공백은 AI가 Ruling으로 확정하지 않는다. 코드 구현상의 가역적 선택은 근거를 알리고 진행하되 AI 판단과 참가자 판단을 구분한다.
- 변경할 업무 동작에는 `sk-exam-test`, 재현된 실패에는 `sk-exam-debug`, 완료 주장에는 `sk-exam-verify`를 연결한다. 중요한 로직은 실패를 입증하는 검사→최소 구현→동일 검사 재실행으로 닫는다.
- 원본의 worktree·SDD workspace 스크립트·별도 모델의 reviewer·finishing-a-development-branch·자동 commit/merge/push·workspace 삭제는 실행하지 않는다. 현재 제공 폴더·허용 도구·기존 MD로 작업하며, 독립 리뷰가 없으면 자기 검토로 명시한다. 남은 15분 안에는 운영 스킬의 최소 수정 경계를 따른다.

## 결과 연결

현재 사용한 스킬·원본 경로·원본 적용 범위·중요 생략을 `05_verification.md`의 스킬 적용 기록에 짧게 남긴다. 파일을 읽은 사실과 검사 실행·기능 완료는 별개다. 끝나면 운영 스킬로 돌아가 남은 시간과 실제 상태에 맞는 다음 한 작업을 이어간다.
