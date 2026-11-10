# AKS Argo CD extension 워크샵 구현 계획 (Implementation Plan)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Kubernetes 지식이 있는 Azure 초급자가 약 90분 동안 AKS Argo CD extension 설치, 자신의 공개 GitHub Fork 기반 앱 배포·변경·자동 복구·정리를 체험하는 한국어 워크샵을 만든다.

**Architecture:** Azure 작업은 Cloud Shell(bash), Git 변경은 GitHub 웹 편집으로 진행한다. 새 AKS에 비HA extension을 설치하고, 단일 Application이 Fork의 일반 YAML을 읽어 nginx Deployment와 LoadBalancer Service를 관리한다. Argo CD 관리 화면은 외부에 공개하지 않는다.

**Tech Stack:** Azure CLI, k8s-extension CLI extension, kubectl, Bash, Kubernetes YAML, Argo CD Application, GitHub 웹 UI, Markdown. 정적 확인에는 Python과 사용 가능한 YAML 파서를 활용하고 앱 런타임 의존성은 추가하지 않는다.

**Spec:** `docs\superpowers\specs\2026-11-10-aks-argocd-workshop-design.md` — 사용자 승인 완료.

## Global Constraints

- 대상: Kubernetes 지식이 있는 Azure 초급 사용자.
- 시간: 약 90분.
- Git 작업: 참가자가 자신의 GitHub 공개 Fork를 만들고 GitHub 웹 화면에서 매니페스트를 수정·커밋.
- 문서는 한국어로 작성한다.
- Helm 직접 설치 대신 `az k8s-extension`의 `Microsoft.ArgoCD`를 사용한다.
- 기본 리전은 `koreacentral`, 노드는 `Standard_D2s_v5` 2개를 제안한다.
- extension과 Application은 `argocd`, 샘플 앱은 `workshop` 네임스페이스로 분리한다.
- 앱 노출은 Service의 `LoadBalancer`만 사용한다. Application Routing 애드온은 설치하지 않는다.
- Git 변경 체험은 replicas 1 → 2, drift 체험은 클러스터 수동 변경 2 → 3 → 자동 복구 2로 한정한다.
- 페이지 내용 변경이나 이미지 업그레이드는 필수 범위에 넣지 않는다.
- 실제 리허설을 수행하지 못했다면 정적 검증 결과와 분리해 미검증으로 표시한다.
- 명령·소요 시간·비용을 실측으로 오인시키지 않는다. 유료 Azure 리소스 생성은 별도 승인이 필요하다.
- 구현 전 현재 작업 트리와 승인 설계를 확인하고, 기존 사용자 변경을 덮어쓰지 않는다.
- 원본 저장소의 공개 URL을 추정하지 않는다. 현재 Git remote가 없으므로 게시 전 Fork 안내 링크를 확정해야 한다.
- 새 테스트 프레임워크나 범용 문서 검사기를 만들지 않는다. 이 작업은 문서·선언형 매니페스트 중심이며 정적 검사와 실제 실습 시나리오로 검증한다.

## Review Focus

1. 원본·Fork·브랜치·디렉터리 혼동: 원본 수정 권한이나 PAT 없이 참가자의 커밋이 관찰되어야 한다. 작업 2의 Fork 시나리오로 검증한다.
2. 새 Cloud Shell 세션 또는 환경 파일 유실: 구독·리소스 이름을 재확인한 뒤 재개하며 다른 리소스를 생성·삭제하지 않아야 한다. 작업 1의 세션 복구 시나리오로 검증한다.
3. 공급자·권한·쿼터·설치 실패: 실패를 드러내고 진행을 멈추며 진단 경로를 제공해야 한다. 작업 1·2의 사전 점검·대기 실패 시나리오로 검증한다.
4. 폴링 지연과 빠른 self-heal: 잘못된 성공 판정 없이 commit SHA·replicas·Ready 수를 확인해야 한다. 작업 3의 동기화·복구 시나리오로 검증한다.
5. 중간 실패와 Application finalizer: controller 제거 순서로 삭제가 막히거나 공인 IP·노드 리소스가 남지 않아야 한다. 작업 3·5의 정리 시나리오로 검증한다.

---

## 파일 구성과 책임

| 파일 | 책임 |
|---|---|
| `README.md` | 개요·아키텍처·목차·90분 시간표·비용·검증 상태 |
| `docs\01-prerequisites.md` | Cloud Shell·구독·권한·도구·Fork·변수 |
| `docs\02-environment-setup.md` | 전용 리소스 그룹·AKS 생성·연결 |
| `docs\03-install-argocd-extension.md` | 비HA extension 설치·준비 상태 검증 |
| `docs\04-deploy-sample-app.md` | Application 부트스트랩·최초 동기화·HTTP 검증 |
| `docs\05-gitops-update-self-heal.md` | 웹 커밋·revision 검증·drift 복구 |
| `docs\06-cleanup.md` | 정상·중도 종료의 안전한 정리 |
| `manifests\app\deployment.yaml` | nginx Deployment의 Git 기준 상태 |
| `manifests\app\service.yaml` | 앱의 공개 HTTP LoadBalancer |
| `manifests\argocd\application.yaml` | 참가자 Fork를 지정하는 Application 템플릿 |

`tests\` 디렉터리는 검증 코드가 필요해졌을 때만 추가한다. 현재 계획은 별도 검사 제품을 만들지 않으며 임시 검증 산출물은 세션 작업 공간에만 둔다.

## 공통 인터페이스

- 환경 파일: `~/.aks-argocd-ws-env`. 비밀 값 없이 `export` 문만 저장하며 이미 존재하면 덮어쓰기 전에 내용을 확인한다.
- 사용자 설정: `GITHUB_OWNER`, `GITHUB_REPO`, `GIT_BRANCH`, `LOCATION=koreacentral`.
- 생성 값: `SUFFIX`, `RESOURCE_GROUP=rg-argocd-ws-${SUFFIX}`, `CLUSTER=aks-argocd-ws-${SUFFIX}`.
- 고정 값: `EXTENSION_NAME=argocd`, `APP_NAMESPACE=workshop`, `APP_NAME=gitops-demo`.
- 파생 값: `REPO_URL=https://github.com/${GITHUB_OWNER}/${GITHUB_REPO}.git`, `NODE_RESOURCE_GROUP`.
- Kubernetes 리소스 이름: Application·Deployment·Service 모두 `gitops-demo`. Deployment selector와 Pod label은 `app: gitops-demo`.
- Application 템플릿: `__REPO_URL__`, `__GIT_BRANCH__` 두 자리표시자만 사용한다. 앱 디렉터리에 템플릿·설명용 YAML을 섞지 않는다.
- 문서 코드 펜스: 실행할 셸 명령은 `bash`, 설명·예상 출력은 `text`, 매니페스트는 `yaml`. 파일 시스템 경로는 실행 환경에 맞춘다. 참가자용 Bash 경로를 Windows 경로로 바꾸지 않는다.
- 각 모듈은 실행·개념 예시·예상 출력 범례, 소요 시간, 성공 조건, 관련 문제 해결, 이전·다음 링크를 제공한다.

### Task 1: Azure 초급자를 위한 환경 준비 경로

**Files:** 생성 `docs\01-prerequisites.md`, `docs\02-environment-setup.md`.

**Interfaces:** 승인 설계와 공통 인터페이스를 입력으로 받아, 연결 가능한 AKS·저장된 환경 파일·`NODE_RESOURCE_GROUP`을 후속 모듈에 제공한다.

- [ ] **1. 사전 점검 인수 시나리오를 문서의 성공 조건에 정의한다.** 올바른 구독 이름, 자신의 공개 Fork, 실제 기본 브랜치, 필요한 공급자 등록·권한, 실행 가능한 Azure CLI·kubectl이 확인되어야 생성 단계로 진행한다.
- [ ] **2. `01`을 작성한다.** Cloud Shell Bash 선택, 구독 선택·재확인, GitHub Fork 웹 생성, 실제 기본 브랜치 확인, 변수 설정·저장·복원 순서를 제공한다. 원본 저장소에 대한 쓰기 권한과 PAT는 요구하지 않는다. 비공개 Fork와 잘못된 브랜치의 진단 방법을 제공한다.
- [ ] **3. `02`를 작성한다.** 태그 `workload=aks-argocd-workshop`, `environment=workshop`의 새 전용 리소스 그룹에 관리 ID·2노드·Free 요금제·Azure CNI Overlay AKS를 생성한다. 실습용 Standard와 요금제 Free의 의미를 구분하고 고정 Kubernetes 버전을 근거 없이 지정하지 않는다. 자격 증명 취득 후 현재 컨텍스트·노드 Ready·노드 리소스 그룹을 확인한다.
- [ ] **4. 권한·실패 시나리오를 점검한다.** 공급자 미등록·등록 권한 없음·VM SKU 또는 쿼터 부족일 때 출력 확인과 관리자 사전 준비 경로가 있어야 한다. 동일 이름의 기존 리소스가 있으면 무조건 재사용하지 않고 확인하도록 한다. 실패한 명령 뒤에 성공 조건이 충족된 것처럼 다음 단계로 넘어가는 안내가 없어야 한다.
- [ ] **5. 새 세션 시나리오를 점검한다.** 환경 파일이 있으면 복원 후 구독·클러스터를 재확인하고, 파일이 없으면 기존 이름을 입력해 재설정한다. 복원 중 새 SUFFIX를 생성하거나 기존 리소스 그룹을 자동 삭제하지 않아야 한다.
- [ ] **6. 문서 검사를 실행하고 커밋한다.** `git diff --check`가 출력 없이 성공해야 한다. 실제 Azure 실행 여부는 별도 기록하며, 커밋 메시지는 `docs: add Azure prerequisites and AKS setup`으로 한다.

### Task 2: extension과 단일 GitOps 애플리케이션

**Files:** 생성 `docs\03-install-argocd-extension.md`, `docs\04-deploy-sample-app.md`, `manifests\app\deployment.yaml`, `manifests\app\service.yaml`, `manifests\argocd\application.yaml`.

**Interfaces:** 작업 1의 환경 변수·AKS를 사용한다. 후속 작업에 자동 동기화된 `gitops-demo` Application과 replicas 1의 Deployment, HTTP 200을 반환하는 Service를 제공한다.

- [ ] **1. 최초 배포 인수 시나리오를 정의한다.** extension `Succeeded`, 관련 워크로드 Ready, Application `Synced`·`Healthy`, nginx HTTP 200이 각각 별도의 성공 조건이어야 한다.
- [ ] **2. 앱 매니페스트를 작성한다.** 공개 nginx 이미지의 실제 고정 태그를 확인해 사용하고 초기 replicas 1, CPU·메모리 requests/limits, `/` HTTP readiness/liveness probes를 지정한다. Service는 TCP 80을 nginx의 HTTP 포트로 전달하는 LoadBalancer이며 관리 화면을 노출하지 않는다.
- [ ] **3. Application 템플릿을 작성한다.** namespace `argocd`, project `default`, source path `manifests/app`, destination `https://kubernetes.default.svc`와 `workshop`을 지정한다. 자동 sync·prune·selfHeal·`CreateNamespace=true`와 `resources-finalizer.argocd.argoproj.io`를 명시한다. finalizer가 controller 동작에 의존함을 정리 문서에 연결한다.
- [ ] **4. `03`을 작성한다.** `k8s-extension`의 확인·설치 또는 업데이트, `Microsoft.ArgoCD` 생성에 `redis-ha.enabled=false` 지정, extension 상태와 실제 리소스 이름 확인, 관련 워크로드 준비 상태 점검을 제공한다. 제한 시간 초과 시 events·상태·Pod 진단으로 멈춘다. 필요한 CLI extension 외에 사용하지 않는 패키지는 설치하지 않는다.
- [ ] **5. `04`를 작성한다.** 자신의 Fork·브랜치·앱 디렉터리가 공개 조회되는지 확인하고 템플릿의 두 자리표시자를 환경 변수로 렌더링해 Application만 적용한다. 부트스트랩과 앱의 GitOps 배포를 구분한다. 예상 출력의 SHA·공인 IP는 예시라고 표시한다.
- [ ] **6. Fork와 잘못된 입력 시나리오를 점검한다.** 원본 저장소 URL, 존재하지 않는 브랜치·경로, 치환되지 않은 자리표시자에 대해 확인 명령과 수정 위치가 있어야 한다. `kubectl apply -f manifests/app`로 실패를 우회하지 않아야 한다.
- [ ] **7. 정적 검사 후 커밋한다.** YAML 문법 검사와 `git diff --check`를 실행한다. YAML 파서는 `python -c "import yaml"`로 가용성을 확인하고, 없을 때만 세션 작업 공간의 임시 가상 환경에 PyYAML을 설치한다. 실제 클러스터가 없다면 schema·동기화·HTTP 검증은 미실시로 남긴다. 커밋 메시지는 `feat: add managed Argo CD sample deployment`로 한다.

### Task 3: Git 변경·자동 복구·안전한 정리

**Files:** 생성 `docs\05-gitops-update-self-heal.md`, `docs\06-cleanup.md`.

**Interfaces:** 작업 2의 `gitops-demo` Application·Deployment·Service와 작업 1의 리소스 이름을 사용한다. revision·replicas 관찰 결과와 정리 완료 기준을 제공한다.

- [ ] **1. Git 변경 인수 시나리오를 정의한다.** GitHub 웹에서 자신의 Fork의 `manifests/app/deployment.yaml`을 열고 동일 브랜치에 replicas 1 → 2를 직접 커밋한다. 커밋 SHA와 Application revision 일치, `Synced`·`Healthy`, replicas·Ready 수 2를 함께 확인해야 한다.
- [ ] **2. `05`의 변경 반영 절차를 작성한다.** 기본 폴링의 대기 시간과 제한 시간을 설명한다. 새 Git revision 확인을 위한 Application refresh annotation은 별도 진단 경로로 제공하고 수동 sync·앱 직접 적용과 구분한다.
- [ ] **3. `05`의 drift 절차를 작성한다.** 첫 터미널에서 Deployment watch를 시작하고 두 번째 Cloud Shell에서 변수를 복원·구독·컨텍스트를 확인한 뒤 `kubectl scale deployment gitops-demo -n workshop --replicas=3`을 실행한다. Git 커밋 없이 replicas 2로 복귀하고 Ready 수가 2로 수렴하는지 확인한다. 순간 값 3을 놓칠 수 있음을 설명한다.
- [ ] **4. `06`의 정상 정리를 작성한다.** 구독·전용 리소스 그룹 이름·태그·포함 리소스를 먼저 표시한다. controller가 동작할 때 finalizer가 설정된 Application을 삭제하고 앱 Deployment·Service·외부 노출 제거를 기다린 뒤 앱 namespace, extension, 전용 리소스 그룹 순서로 제거한다. 명령 접수와 삭제 완료를 구분한다.
- [ ] **5. 중도 종료 시나리오를 작성한다.** extension 설치 전 실패, 앱 배포 중 실패, controller가 이미 삭제되어 finalizer가 멈춘 경우를 다룬다. 전용 그룹이 맞는지 확인한 뒤 그룹 전체 삭제로 정리하는 경로를 제공한다. 무조건적인 finalizer 제거·노드 리소스 그룹 선삭제·다른 kubeconfig 삭제는 하지 않는다.
- [ ] **6. 정리 완료 조건을 점검하고 커밋한다.** 기록된 실습 그룹과 노드 그룹 부재 확인, 해당 실습 환경 파일·kubeconfig 항목만 제거, GitHub Fork 보관 또는 웹 삭제 안내가 있어야 한다. `git diff --check` 후 `docs: add GitOps update self-heal and cleanup labs`로 커밋한다.

### Task 4: README 통합과 전체 정적 검증

**Files:** 생성 `README.md`; 필요 시 이전 작업의 문서·매니페스트 수정.

**Interfaces:** 작업 1~3의 여섯 모듈을 연결하고, 초보 참가자가 따라갈 단일 진입점과 검증 상태를 제공한다.

- [ ] **1. README를 작성한다.** 개요·학습 목표·텍스트 또는 Mermaid 아키텍처·요구 권한·공개 Fork 조건·모듈 링크·10/20/15/15/20/10분 시간표·비용·태그·공식 링크를 포함한다. UI·DNS·TLS·SSO·ACR는 다루지 않는다고 명시한다.
- [ ] **2. 출처와 비용 정보를 점검한다.** 설계의 공식 링크로 GA와 Arc preview를 구분하고 VM·디스크·Load Balancer·공개 IP 등 과금과 Pricing Calculator를 안내한다. 검증 날짜·도구 버전은 실제 확인한 값만 넣는다. 원본 저장소가 아직 게시되지 않았으면 Fork 링크 확정이 남았음을 명시한다.
- [ ] **3. 상대 링크를 검증한다.** README와 여섯 모듈의 모든 상대 링크·매니페스트 참조를 실제 파일 기준으로 확인하고 이전·다음 이동을 처음부터 끝까지 따라간다. 설계·계획 문서가 실습 모듈로 잘못 연결되지 않아야 한다.
- [ ] **4. Bash 블록의 문법을 검증한다.** `bash --version`으로 실행 가능성을 먼저 확인한다. 실행용 `bash` 펜스만 임시 파일로 추출하고 `bash -n <임시 파일>`이 모두 성공하는지 확인한다. WSL 실행 별칭만 있고 실제 Bash가 없으면 Cloud Shell 등 실행 가능한 Bash에서 수행하며 미실시를 성공으로 처리하지 않는다. heredoc·변수 치환·개행 continuation이 블록 단독으로 완결되어야 한다.
- [ ] **5. 모든 YAML을 파싱하고 템플릿을 점검한다.** 사용 가능한 PyYAML의 `yaml.safe_load_all`로 세 파일을 읽어 문법 오류가 없는지 확인한다. 템플릿을 예시 Fork URL·브랜치로 임시 렌더링하고 자리표시자가 남지 않는지 확인한다. 파싱 성공은 Kubernetes schema 검증이나 실제 배포 성공을 뜻하지 않는다.
- [ ] **6. 전체 안내를 순서대로 읽어 교차 검증한다.** 변수·리소스 이름·namespace·Git branch·앱 path·정리 순서가 공통 인터페이스와 일치해야 한다. `git diff --check`를 실행하고 임시 검사 파일을 정리한다.
- [ ] **7. 검증 상태를 명시하고 커밋한다.** 실제 실행 전에는 README에 정적 검증 결과와 Azure 리허설 미실시를 구분한다. `docs: complete workshop navigation and validation notes`로 커밋한다.

### Task 5: 별도 승인 후 실제 Azure 리허설

**Files:** `README.md`와 관련 모듈의 검증 상태·관측 결과만 수정.

**Interfaces:** 작업 4까지의 완성된 문서를 사용한다. 실제 실행 근거가 있는 검증 버전·소요 시간·제약 사항을 제공한다.

- [ ] **1. 실행 승인을 확인한다.** 테스트 구독·비용 발생·공개 HTTP 앱 생성·전용 그룹 삭제를 포함하는 별도 승인을 받기 전에는 실행하지 않는다. 승인 없이는 리허설을 보류하고 미실시로 전달한다.
- [ ] **2. 첫 사용자 경로를 실행한다.** 공개 게시된 워크샵의 실제 Fork를 사용하고 문서의 명령만으로 모듈 01~04를 진행한다. 리소스 생성 전에는 구독·리전·쿼터와 실제 가격 조건을 확인한다. 매니페스트의 서버 측 dry-run, extension 상태, Ready·Synced·Healthy·HTTP 200을 기록한다.
- [ ] **3. GitOps 동작을 실행한다.** GitHub 웹 커밋 1 → 2와 SHA·revision 일치, 수동 변경 3 → 2, 최종 Ready 2를 검증한다. drift 변경 전후 Git SHA가 동일해야 한다.
- [ ] **4. 복구·정리를 실행한다.** 새 세션에서 변수 복원 후 모듈 06을 진행하고 finalizer·Service 제거, extension 제거, 실습 그룹·노드 그룹 삭제 완료를 확인한다. 남은 리소스가 있으면 원인과 비용 위험을 먼저 보고하고 해결한다.
- [ ] **5. 결과를 반영한다.** 실제 도구·extension 버전, 리전·SKU·노드 수, 단계별 시간, 실패·수정 사항을 기록한다. 90분 초과 시 반복 대기와 설명을 먼저 조정하고 핵심 학습 목표 변경이 필요하면 사용자 승인을 받는다.
- [ ] **6. 변경된 파일만 재검증하고 커밋한다.** 관련 정적 검사를 재실행하고 `docs: record verified Azure workshop rehearsal`로 커밋한다. 완료 보고는 문서 작성·정적 검사·실제 리허설을 구분한다.

## 커밋 및 실행 유의사항

- 각 커밋에는 실행 세션에 해당하는 `Co-authored-by`와 `Copilot-Session` trailer를 포함한다.
- Git 원격 게시·push와 GitHub Fork 생성은 별도 권한·승인 범위를 확인한다. 워크샵 작성만으로 현재 저장소를 공개하지 않는다.
- 로컬 문서 작성 완료와 참가자가 실행할 수 있는 공개 배포 완료를 구분한다. 공개 URL이 없으면 그 한계를 인계한다.

## 자체 검토 결과

- 설계 1~4의 의도·대상·접근 방식은 README와 공통 제약, 설계 5~6의 구조·기술 선택은 작업 1~3에 대응한다.
- 설계 7~8의 시간·권한·비용·장애 대응은 작업 1·2·4, 설계 9의 안전한 삭제는 작업 3·5가 담당한다.
- 설계 10의 정적 검사와 실제 검증은 작업 4·5로 분리했다. 설계 11의 구현자 판단은 이미지·리소스 수치·timeout·공개 URL 확인 단계에 남겼다.
- Review Focus 다섯 조건을 각각 담당 작업의 인수·실패 시나리오에 배치했다.
- 함수·클래스의 신규 API는 없으며 변수·리소스 이름·템플릿 자리표시자를 공통 인터페이스로 통일했다.
- 작업 5는 승인이 필요한 유료 검증으로 명시했으며, 승인 없이 구현자가 자동 실행하지 않는다.

## 실행 기록 — 2026-11-10

- Task 1~4 구현 및 정적 검증 완료. 실제 Azure 리허설인 Task 5는 별도 승인 전 보류.
- 최종 독립 검토에서 빈 입력 검증과 홈·kubeconfig 복구 문제를 발견해 수정.
- 필요한 동작 회귀 검사만 `tests\test_prerequisites.py`에 추가. 표준 unittest와 Bash를 사용하며 별도 테스트 프레임워크는 추가하지 않음.
- 회귀 검사 3개, 문서 7개 링크, 실행 Bash 블록 32개, YAML 3개 정적 검증 통과.
