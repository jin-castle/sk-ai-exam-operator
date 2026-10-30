# SK AI Exam Operator

SK AI 해커톤·Probe의 180분 과제를 위한 개인 운영 스킬입니다. 담당자 답변을 업무 규칙·기능·예외·판단·검증 기록으로 연결하고, 참가자가 알려주는 남은 시간과 실제 진행 상태에 따라 다음 작업을 정합니다. 대회 주최사나 플랫폼의 공식 스킬은 아닙니다.

## 설치 위치와 버전

- 공개 저장소: https://github.com/jin-castle/sk-ai-exam-operator
- 버전 ref: `v1.0.0`
- 설치할 경로: `skills/sk-ai-exam-operator`
- 스킬 이름: `sk-ai-exam-operator`
- 원본: [SKILL.md](skills/sk-ai-exam-operator/SKILL.md)
- 시험용 입력문: [EXAM_PROMPTS.md](EXAM_PROMPTS.md)

태그를 다른 커밋으로 옮기지 않습니다. 고정 커밋 SHA를 확인한 경우 `v1.0.0` 대신 해당 SHA로 설치할 수 있습니다.

## 빠른 시작

시험 제공 환경의 Codex에 아래 설치 요청을 입력합니다. 설치와 시작을 같은 대화에서 처리하는 입력문은 [EXAM_PROMPTS.md](EXAM_PROMPTS.md)에 있습니다.

```text
$skill-installer 공개 저장소 https://github.com/jin-castle/sk-ai-exam-operator 에서
ref v1.0.0, 경로 skills/sk-ai-exam-operator 의 스킬만 설치해줘.
기존 같은 이름의 스킬이 있으면 덮어쓰지 말고 원본과 비교해줘.
Codex 업데이트, 외부 AI·개인 키, Computer Use, 외부 전송·Git Push는 하지 마.
```

설치 후 호스트의 스킬 목록 반영을 확인하고 다음 턴에 시작합니다. 파일 설치와 목록 인식은 별개입니다. 목록 반영이 늦어지면 설치된 `SKILL.md`를 직접 읽어 현재 대화에서 적용할 수 있습니다. 이를 정식 목록 인식 성공으로 기록하지 않습니다.

```text
$sk-ai-exam-operator 시험 운영을 시작해줘.
화면에서 확인한 남은 시간은 180분이야.
과제와 기존 파일을 먼저 확인하고, 담당자 질문·MD 기록·구현·검증을 이어가줘.
```

`180`은 실제 화면의 값으로 바꿉니다. 시간이 아직 확인되지 않았다면 알려주지 않아도 되며, 스킬은 현재 잔여 시간을 180분으로 가정하지 않습니다.

## 어떻게 운영하나

초반에는 과제·업무 정책·성공 기준을 확인하고, 중반에는 작은 사용자 흐름을 구현해 직접 사용과 코드 검사로 개선합니다. 후반에는 필수 흐름 완성·통합 검증·본인의 설명·저장·제출 확인에 집중합니다.

사용자가 담당자 답변이나 새 시간 보고를 전달하면 바뀐 기록만 갱신합니다. 같은 시험 대화에서 스킬을 매번 다시 호출할 필요는 없습니다. 최신 잔여 시간은 사용자가 보고한 값만 사용하며, 이전 값은 ‘마지막 보고’로 표시합니다.

| 기본 기록 | 내용 |
|---|---|
| `exam-notes/01_domain.md` | 답변·업무 규칙·출처·미확인 |
| `exam-notes/02_requirements.md` | 기능·필요 조건·수용 기준 |
| `exam-notes/03_exceptions.md` | 예외·기대 처리·구현·검증 연결 |
| `exam-notes/04_decisions.md` | 실제 AI 제안·참가자의 선택·실제 이유 |
| `exam-notes/05_verification.md` | 실제 실행·직접 관찰·시스템 흐름·한계 |

과제 지정 양식이나 동등한 기록이 있으면 재사용합니다. 선택적 스크립트는 기존 본문 기록을 덮어쓰지 않습니다. 기록용 폴더와 상태 파일은 이 저장소의 `.gitignore`에 포함돼 있습니다.

## 의존성과 한계

- 핵심 운영은 Markdown 지침과 기본 코드 도구로 가능합니다.
- Python이 이미 있으면 표준 라이브러리만 쓰는 선택적 보조 스크립트로 시간 보고와 빈 양식을 관리할 수 있습니다. 새 Python이나 패키지를 설치할 필요는 없습니다.
- Ouroboros·gstack·Superpowers는 선택적 참고 대상입니다. 이 저장소에 원본 런타임을 포함하거나 자동 설치하지 않습니다.
- 다른 스킬의 정식 실행과 해당 원칙을 참고한 별도 프롬프트를 구분합니다.
- 타이머 읽기·자동 감소·알람·브라우저 자동화·제출 자동화는 없습니다.
- 참가자가 말하지 않은 판단 이유나 실행하지 않은 테스트 결과를 만들지 않습니다.
- AI 금지 후속 서술형에 들어갔다는 보고가 오면 문항 분석·답안·첨삭·파일 작업을 멈춥니다.

실제 시험의 반입·AI·모델·자동화·공개 유지 조건은 최신 응시 안내가 우선합니다. 준비 단계의 이 공개 소스 게시와 시험자료의 외부 전송은 구분해야 합니다. 시험 중에는 시험자료나 생성 기록을 이 저장소로 Push하지 않습니다.

## 선택적 도우미

아래는 명령 형태입니다. `SKILL_DIR`와 작업 경로는 현재 환경의 실제 위치를 사용합니다. 시간 값도 실제 보고값으로 바꿉니다.

```text
python SKILL_DIR/scripts/exam_session.py init --root exam-notes --remaining 180
python SKILL_DIR/scripts/exam_session.py checkpoint --root exam-notes --remaining 72
python SKILL_DIR/scripts/exam_session.py status --root exam-notes
```

`status`는 읽기 전용입니다. 새 시간 보고 없는 재실행은 기존 시간과 보고 시각을 보존합니다. 스크립트가 보여주는 권고 구간은 실제 기능 완료 여부를 뜻하지 않습니다.

## 준비 단계 검증

기존 Python 환경에서 저장소 루트 기준으로 실행할 수 있습니다. 시험 시작 시 이 전체 검사를 반복할 필요는 없습니다.

```text
python -B -m unittest discover -s tests -v
```

검사는 시간 경계·미보고·재개·기존 문서 보존·잘못된 입력·상태 충돌·읽기 전용 조회를 확인합니다. 실제 시험 플랫폼 호환성이나 생성 앱의 동작을 검증하는 테스트는 아닙니다.

원본 스킬의 선택적 연결은 [references/operation.md](skills/sk-ai-exam-operator/references/operation.md)를 참조합니다. 이 저장소에는 담당자 실제 답변, 시험 데이터, 응시 로그, 개인 연락처·인증 정보가 포함되지 않습니다.
