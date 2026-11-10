# AKS Argo CD UI 중심 워크샵 구현 계획 (Implementation Plan)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans for the user's previously selected direct execution method. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 기존 워크샵의 설치 이후 앱 작업을 로컬 포트포워딩으로 접속한 Argo CD UI 중심으로 전환한다.

**Architecture:** Azure 작업은 기존 Cloud Shell Bash를 유지한다. 참가자 PC의 Windows PowerShell에서 Azure 로그인·kubeconfig 취득 후 `127.0.0.1:8080`을 Argo CD HTTPS 포트에 포워딩한다. 앱 생성·첫 Sync·자동 동기화·상태·삭제는 UI에서 진행하고 GitHub 웹 편집과 drift 명령 1회는 유지한다.

**Tech Stack:** Markdown, Azure CLI, kubectl, Windows PowerShell, Bash, Argo CD UI, 기존 Kubernetes YAML과 Python unittest.

**Spec:** `docs\superpowers\specs\2026-11-10-aks-argocd-ui-workshop-design.md` — 승인 완료.

## Global Constraints

- 기존 6개 모듈·단일 nginx 앱·공개 Fork·비HA AKS 구성을 유지한다.
- 관리 화면용 LoadBalancer·Ingress·도메인·SSO는 추가하지 않는다.
- 로컬 포워딩은 `127.0.0.1:8080`에서 Service의 HTTPS 포트로 연결한다. Cloud Shell localhost를 PC localhost로 설명하지 않는다.
- Windows PowerShell 로컬 명령과 Cloud Shell Bash 명령의 실행 위치를 명시한다.
- 로컬 Azure CLI·kubectl 설치는 약 90분 실습 전 준비로 구분한다.
- 초기 비밀번호는 참가자 PC에서만 취득하고 Git·환경 파일·스크린샷에 남기지 않는다. 문서 작성 중 실제 비밀을 조회하지 않는다.
- 앱 생성은 UI Manual 정책, 첫 수동 Sync 후 자동 Sync·Prune·Self Heal 활성화 순서다.
- Git replicas 1 → 2 → 수동 3 → 자동 복구 2를 유지한다.
- 실제 Azure·UI 리허설, 저장소 공개 전환, 원격 push는 별도 승인 범위다.
- 문서·선언형 설정 작업은 승인된 인수 조건과 정적 검사로 검증한다. 새 범용 테스트 프레임워크를 만들지 않는다.

## Review Focus

1. PC와 Cloud Shell 변수·kubeconfig 혼동: 로컬에서 기존 구독·그룹·AKS를 명시적으로 입력해 취득해야 한다. Task 1의 세션 분리 점검으로 확인한다.
2. PowerShell의 native 실패: `$ErrorActionPreference`만 믿지 않고 Azure CLI·kubectl 실패를 명시적으로 중단해야 한다. Task 1의 명령별 exit code 점검으로 확인한다.
3. Manual Sync와 namespace 생성: 새 namespace가 없는 상태에서도 UI 설정으로 생성되고 첫 Sync 전 성공으로 판정하지 않아야 한다. Task 2의 UI 입력표·인수 시나리오로 확인한다.
4. 자동 동기화·revision·Ready 관찰: 자동 정책 활성화 전 Git 변경으로 넘어가거나 revision만으로 성공 판정하지 않아야 한다. Task 2의 단계 순서로 확인한다.
5. cascading deletion과 접속 중단: 앱·자식 리소스를 먼저 정리하고 포워딩·extension을 종료해야 한다. Task 2의 정상·중도 종료 경로로 확인한다.

---

## 파일과 공통 인터페이스

| 파일 | 변경 책임 |
|---|---|
| `docs\01-prerequisites.md` | 로컬 도구·네트워크 사전 준비 추가. 기존 환경 복구 블록 유지 |
| `docs\02-environment-setup.md` | 로컬에서 사용할 기존 대상 이름 확인 |
| `docs\03-install-argocd-extension.md` | 로컬 연결·로그인·초기 비밀번호·포워딩과 종료 |
| `docs\04-deploy-sample-app.md` | UI NEW APP·첫 Sync·리소스 트리·HTTP 확인 |
| `docs\05-gitops-update-self-heal.md` | UI 자동 정책·Git 변경·drift 복구 관찰 |
| `docs\06-cleanup.md` | UI cascading deletion·포워딩 종료·기존 Azure 정리 |
| `README.md` | 로컬 준비·UI 흐름·아키텍처·검증 상태 |
| 기존 CLI 중심 설계·계획 | 과거 설계 중 UI 변경분이 새 승인 설계로 대체됐음을 명시 |

기존 앱 YAML 3개와 `tests\test_prerequisites.py`는 유지한다. Application YAML은 UI 자동 정책 설정 후의 참고 상태이며 기본 실행 파일이 아니다. UI는 `gitops-demo`, `default`, 자신의 Fork·실제 브랜치, `manifests/app`, `https://kubernetes.default.svc`, `workshop`을 사용한다.

로컬 변수는 `$SubscriptionName`, `$ResourceGroup`, `$Cluster`이며 Cloud Shell의 환경 파일을 PC에서 source하지 않는다. PC용 블록은 `powershell`, Cloud Shell은 `bash`, 예시 출력은 `text` 펜스를 사용한다.

### Task 1: 로컬 도구와 UI 접속

**Files:** 수정 `docs\01-prerequisites.md`, `docs\02-environment-setup.md`, `docs\03-install-argocd-extension.md`.

**Interfaces:** 기존 Cloud Shell의 리소스 이름을 입력받아 로컬 PC에 유효한 kubeconfig·UI 세션을 제공한다. Argo CD의 기존 `argocd-server` ClusterIP·HTTPS 설정은 바꾸지 않는다.

- [ ] **1. 로컬 사전 준비를 추가한다.** Windows용 Azure CLI·kubectl 공식 설치 링크와 `az version`, `kubectl version --client` 확인을 제공하고 설치 시간을 실습 시간과 분리한다.
- [ ] **2. 02에 인계 값을 추가한다.** Cloud Shell에서 구독 이름·리소스 그룹·AKS 이름을 출력한다. PC에 비밀·kubeconfig를 복사하는 안내는 만들지 않는다.
- [ ] **3. 03에 로컬 연결을 작성한다.** 별도 Windows PowerShell에서 로그인, 비어 있지 않은 대상 입력, 구독 선택·확인, get-credentials·컨텍스트 확인을 순서대로 수행하고 각 native 실패를 명시적으로 중단한다.
- [ ] **4. 로그인·포워딩을 작성한다.** PC의 다른 창에서 초기 비밀번호를 직접 조회해 클립보드로 전달하며 출력 예시에는 넣지 않는다. UI에서 비밀번호 변경·재로그인 확인 후 초기 Secret을 정리한다. 포워딩은 foreground로 유지하고 `https://127.0.0.1:8080` 접속과 자체 서명 인증서 주의사항을 설명한다.
- [ ] **5. 인수 시나리오를 점검한다.** PC 로컬 로그인과 Cloud Shell이 독립이고, 두 번째 PC 창에 변수 자동 공유를 가정하지 않으며, 포워딩 실패·8080 충돌·인증서·재접속의 진단 경로가 있어야 한다.
- [ ] **6. 문법·회귀 검사 후 커밋한다.** `python -m unittest discover -s tests -p 'test_*.py' -v`, 변경 Bash의 `bash -n`, 로컬 PowerShell의 `System.Management.Automation.Language.Parser` 검사, `git diff --check`가 성공해야 한다. 커밋 메시지: `docs: add local Argo CD UI access preparation`.

### Task 2: UI 앱 생성·GitOps·삭제

**Files:** 수정 `docs\04-deploy-sample-app.md`, `docs\05-gitops-update-self-heal.md`, `docs\06-cleanup.md`.

**Interfaces:** Task 1의 UI 세션과 기존 공개 Fork를 사용한다. 결과는 앱 Synced·Healthy·HTTP 200, Git revision·replicas/Ready 2, 마지막의 cascading deletion이다.

- [ ] **1. 04를 UI 기본 흐름으로 교체한다.** 필드별 입력표, Manual 정책, Auto-Create Namespace, 첫 SYNC·SYNCHRONIZE와 리소스 트리 확인을 작성한다. CLI Application 렌더링·적용은 기본 경로에서 제거하고 기존 템플릿은 참고 상태로 연결한다.
- [ ] **2. 04의 관찰 기준을 작성한다.** OutOfSync·Missing과 Synced·Healthy를 구분하고 Service의 live 상태에서 외부 IP를 찾아 브라우저로 HTTP 앱을 확인한다. 이름만 보고 다른 리소스를 선택하지 않게 한다.
- [ ] **3. 05를 UI 중심으로 교체한다.** 자동 Sync·Prune·Self Heal을 먼저 활성화하고 GitHub 웹에서 replicas 2 커밋 후 UI에서 revision·Deployment·Pod Ready를 비교한다. drift 명령 1회는 기존 Cloud Shell에서 실행하고 UI에서 Git 추가 커밋 없는 2 복귀를 관찰한다.
- [ ] **4. 06의 정상 앱 정리를 UI로 바꾼다.** 대상 앱 이름과 foreground cascading deletion을 확인한 후 앱·자식 리소스 삭제를 기다린다. PC 포워딩을 Ctrl+C로 중단한 뒤 Cloud Shell에서 namespace·extension·그룹을 제거한다. UI 불가 시 기존 finalizer 기반 CLI 정리를 진단용 대안으로 유지한다.
- [ ] **5. UI 필드·실패 경로를 공식 가이드와 대조한다.** 레이블의 버전 차이, namespace 옵션 누락, 잘못된 Fork·브랜치, 자동 정책 누락, 빠른 self-heal, cascading 삭제 미선택을 설명한다. 직접 실행·캡처한 것처럼 말하지 않는다.
- [ ] **6. 문법·회귀 검사 후 커밋한다.** 같은 회귀 명령·Bash 검사·`git diff --check`가 성공해야 한다. 커밋 메시지: `docs: move application lifecycle to Argo CD UI`.

### Task 3: 전체 문서와 검증 기록 정합성

**Files:** 수정 `README.md`, `docs\superpowers\specs\2026-11-10-aks-argocd-workshop-design.md`, `docs\superpowers\plans\2026-11-10-aks-argocd-workshop.md`; 필요한 모듈의 관련 설명만 수정.

**Interfaces:** Task 1~2의 실제 문서 흐름을 단일 진입점과 공식 참고 링크에 반영한다.

- [ ] **1. README와 과거 설계 설명을 갱신한다.** 로컬 준비·UI 로그인·NEW APP·수동 첫 Sync·UI 관리·포트포워딩을 아키텍처와 목표에 반영한다. 과거 CLI 부트스트랩·UI 미사용 설계는 새 승인 설계로 대체되었다고 명시한다. 원본 비공개 제한과 실제 리허설 미실시를 유지한다.
- [ ] **2. 전체 정적 검증을 수행한다.** 회귀 테스트 전체, 문서 상대 링크·모듈 연결, 실행 Bash와 PowerShell 파싱, YAML 3개 파싱, 이름·브랜치·정책·삭제 순서 일관성, `git diff --check`를 확인한다. UI prose 자체에 상수 확인 테스트나 새 프레임워크를 추가하지 않는다.
- [ ] **3. 검증 기록을 갱신한다.** 제거된 Python 렌더러 검증을 현재 기본 경로의 검증처럼 표시하지 않는다. 로컬 UI·실제 배포·복구·삭제·90분은 미검증으로 남긴다. 커밋 메시지: `docs: align workshop overview with UI workflow`.
- [ ] **4. 최종 독립 검토와 인계를 수행한다.** 기존 직접 구현 방식대로 전체 변경을 한 번 독립 검토한다. 중요한 문제는 재현 가능한 검사로 수정·재검증하고, 원격 push는 사용자 승인 범위에 맞게 수행한다.

## 자체 검토

설계의 로컬 설치·접속·비밀번호·세션 분리는 Task 1, 앱 UI 생명주기·GitOps·정리는 Task 2, 90분 목표·참고 YAML·문서와 검증 상태 일관성은 Task 3에 대응한다. 실제 Azure 실행과 공개 전환은 포함하지 않는다. Review Focus 다섯 조건을 각각 담당 작업의 인수·실패 점검에 배치했다.
