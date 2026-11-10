# AKS Argo CD extension GitOps 핸즈온 워크샵 설계

작성일: 2026-11-10

상태: 사용자 승인 완료 (2026-11-10)

대상 저장소: 현재 `argo-aks-test-01` 저장소

## 1. 의도와 배경

Kubernetes는 알지만 Azure는 초급인 참가자가 Microsoft 관리형 Argo CD extension을 AKS에 설치하고, Git을 원하는 상태의 기준으로 삼는 배포 방식을 직접 경험하는 한국어 워크샵을 만든다.

참고 워크샵의 번호별 모듈, Cloud Shell(bash), 실행 명령과 예상 출력 구분, 검증, 문제 해결, 비용 안내, 정리 절차를 따른다. Application Routing의 DNS·TLS 실습 자체를 가져오는 것은 아니다. 문구를 복제하지 않고 이 주제에 맞게 새로 작성한다.

## 2. 사용자가 정한 사항

- 대상: Kubernetes 지식이 있는 Azure 초급 사용자.
- 시간: 약 90분.
- 주제: AKS에 Argo CD extension을 설치하고 간단한 샘플 앱을 GitOps 방식으로 배포.
- Git 작업: 참가자가 자신의 GitHub 공개 Fork를 만들고 GitHub 웹 화면에서 매니페스트를 수정·커밋.
- 참고 형식: `freeman9844/ms-aks-approuting-workshop01`.

아래의 세부 구성은 위 조건을 충족하기 위한 작성자의 제안이며, 사용자가 개별적으로 지정한 사항은 아니다.

## 3. 목표, 비목표, 피해야 할 결과

### 목표

1. Cloud Shell에서 구독과 작업 대상을 확인하고 전용 리소스 그룹·AKS를 생성한다.
2. `Microsoft.ArgoCD` extension을 설치하고 Azure 프로비저닝 상태와 Kubernetes 구성요소 준비 상태를 구분해 확인한다.
3. 참가자 자신의 Fork를 바라보는 Argo CD `Application`을 생성한다.
4. Argo CD가 배포한 샘플 앱에 HTTP로 접근한다.
5. GitHub 웹에서 Deployment의 replicas를 1에서 2로 바꿔 커밋하고 자동 동기화·롤아웃을 관찰한다.
6. 클러스터에서 replicas를 3으로 직접 바꾸고 Git의 값인 2로 자동 복구되는 것을 확인한다.
7. 실습 앱과 Azure 리소스를 안전하게 정리하고 삭제 완료를 확인한다.

### 비목표

- CI 파이프라인, 이미지 빌드, ACR, 비공개 Git 저장소 인증.
- Entra SSO, Argo CD 관리 화면 외부 공개, 도메인, DNS, TLS.
- ApplicationSet, 멀티클러스터, HA, 운영 환경 보안·모니터링 전체 구성.
- Helm·Kustomize 학습, Git CLI 쓰기 인증, GitHub Actions.
- 기존 운영 AKS 또는 기존 Argo CD의 변경·마이그레이션.

### 피해야 할 결과

- 샘플 앱을 `kubectl apply`로 직접 배포해 놓고 GitOps 배포로 설명하는 것.
- Fork가 아닌 원본 저장소를 바라봐 참가자의 커밋이 반영되지 않는 것.
- extension의 설치 성공만으로 앱 정상 동작까지 성공했다고 판정하는 것.
- Git 동기화 지연을 무조건 장애로 설명하거나 무제한 대기시키는 것.
- 관리 화면·관리자 자격 증명을 불필요하게 외부에 노출하는 것.
- 학습용 비HA·공개 HTTP 구성을 운영 권장 구성처럼 설명하는 것.
- 검증하지 않은 소요 시간·명령·예상 출력을 실측 결과처럼 제시하는 것.

## 4. 검토한 접근 방식

| 접근 방식 | 장점 | 단점 | 결정 |
|---|---|---|---|
| 공개 Fork + GitHub 웹 편집 + Cloud Shell Azure 작업 | Git 쓰기 자격 증명 없이 자신의 커밋과 동기화를 관찰 | 웹과 터미널 사이를 이동 | 사용자 선택 |
| 공개 Fork + Cloud Shell Git CLI 편집·push | 터미널 중심 개발 흐름과 유사 | GitHub 인증·편집기 안내와 장애 대응이 추가됨 | 90분 입문 실습에서는 제외 |

앱 배포 방식은 단일 클러스터·단일 Application·일반 YAML로 단순화한다. 고급 저장소 구조나 템플릿 도구는 핵심 학습 목표에 비해 설명 부담이 크다.

## 5. 제안 아키텍처와 주요 판단

```text
참가자 ── GitHub 웹 편집·커밋 ──> 자신의 공개 Fork
                                     ^
                                     | Argo CD가 HTTPS로 읽기
Cloud Shell ── Azure CLI ──> AKS [Microsoft.ArgoCD extension]
           └─ kubectl ─────> Application 부트스트랩
                                     |
                                     v
                             workshop 네임스페이스
                             Deployment + Service
                                     ^
                                     | HTTP / 공개 LoadBalancer IP
                               브라우저 또는 curl
```

### AKS와 Azure

- 새 실습 전용 리소스 그룹과 AKS를 생성하는 경로 하나를 기본으로 제공한다.
- AKS는 Automatic이 아닌 명시적으로 구성하는 Standard 클러스터, Free 요금제, 관리 ID 기반으로 제안한다. 정해진 노드 수와 비용·삭제 대상을 설명하기 쉬운 학습용 선택이다.
- 기본 리전은 `koreacentral`, 노드는 `Standard_D2s_v5` 2개를 제안한다. 용량·쿼터·extension 리소스 요구량은 구현 시 리허설로 확인한다. Pending이면 원인을 확인하고 명시적으로 조정하며 자동으로 숨겨서 확장하지 않는다.
- Azure CNI Overlay, 기본 외부 송신, Cloud Shell에서 접근 가능한 공개 API 서버를 사용한다. 사설망·방화벽 전용 환경은 지원 범위에서 제외한다.
- 앱 노출은 Service의 `LoadBalancer`만 사용한다. Application Routing 애드온은 설치하지 않는다.
- 전용 리소스 그룹에 실습 용도 태그를 부여하고, 노드 리소스 그룹 이름도 기록한다.
- 리전·SKU 변경 시 비용과 가용성을 다시 확인하도록 안내한다. 이 설정은 운영 권장 구성이 아니다.

### Argo CD extension

- Helm 직접 설치 대신 `az k8s-extension`의 `Microsoft.ArgoCD`를 사용한다.
- 공식 튜토리얼의 기본 HA 구성은 노드 4개가 필요하므로 `redis-ha.enabled=false`를 명시한 실습용 비HA 구성을 사용한다.
- extension과 Application은 `argocd`, 샘플 앱은 `workshop` 네임스페이스로 분리한다. Application을 여러 네임스페이스에서 감시하는 옵션은 불필요하다.
- extension 구성 변경은 Azure extension 설정을 통해 수행하고 관리형 Argo CD ConfigMap을 직접 편집하지 않는다.
- 핵심 검증은 `kubectl`로 수행한다. Argo CD CLI 설치, UI 로그인, 포트포워딩을 완료 조건으로 삼지 않는다.
- 설치 명령의 성공, extension의 `Succeeded`, 관련 워크로드의 준비 완료를 별도로 확인한다.
- 구현 시 GA 버전과 설정 키를 확인하고 리허설 버전·날짜를 기록한다. 오래된 preview 설치 예제를 섞지 않는다.

### 샘플 앱과 GitOps

- 공개된 고정 버전 nginx 이미지로 Deployment와 LoadBalancer Service를 구성한다. 빌드·데이터베이스·추가 백엔드는 없다.
- 이미지의 정확한 레지스트리·태그, requests/limits, probes는 구현자가 공개 가용성과 리허설 결과를 바탕으로 정한다. `latest`는 사용하지 않는다.
- 앱 매니페스트에는 replicas 1을 명시하고 HPA는 만들지 않는다.
- Fork의 기본 브랜치를 확인해 명시적으로 추적하고, GitHub 웹 편집 시 같은 브랜치로 직접 커밋한다. PR 생성은 요구하지 않는다.
- Application의 `repoURL`은 참가자의 공개 Fork, `path`는 앱 전용 디렉터리, destination은 해당 AKS의 `workshop`이다.
- 자동 동기화와 `selfHeal`을 활성화한다. `prune`도 활성화하되 Git에서 관리 리소스를 제거하면 클러스터에서도 삭제될 수 있음을 경고한다. prune 체험은 기본 실습에 추가하지 않는다.
- Application 생성과 Namespace 생성 설정은 부트스트랩이며, 앱 Deployment·Service를 직접 적용하는 절차와 명확히 구분한다.
- Git 변경 체험은 replicas 1 → 2, drift 체험은 클러스터 수동 변경 2 → 3 → 자동 복구 2로 한정한다.
- 페이지 내용 변경이나 이미지 업그레이드는 필수 범위에 넣지 않는다. Git 변경의 검증 대상은 커밋 revision과 replicas·Ready Pod 수다.
- GitHub 토큰·PAT·SSH 키를 요구하거나 저장하지 않는다.

## 6. 문서 및 파일 구성

```text
README.md
docs/
  01-prerequisites.md
  02-environment-setup.md
  03-install-argocd-extension.md
  04-deploy-sample-app.md
  05-gitops-update-self-heal.md
  06-cleanup.md
  superpowers/specs/...
manifests/
  app/
    deployment.yaml
    service.yaml
  argocd/
    application.yaml
tests/
  ... 구현 시 검증 방식에 맞춰 결정
```

`tests/`의 세부 파일명과 검증 도구는 구현자가 정한다. Application 템플릿은 앱 디렉터리에 넣지 않아 앱이 자기 자신을 관리하지 않게 한다. 원본은 `https://github.com/freeman9844/aks-argo-test-01`이며 2026-11-10 동기화 시점에는 비공개다. 공개 Fork 실습은 배포자가 별도로 공개 전환을 승인·완료한 뒤 진행한다.

문서는 한국어로 작성한다. 각 실습 모듈은 실행·개념 예시·예상 출력의 구분, 소요 시간, 성공 조건, 관련 문제 해결, 이전·다음 링크를 제공한다. 필요한 모듈에는 새 세션에서 변수 복원 절차를 둔다.

상태 파일은 실습 전용 이름으로 Cloud Shell 홈에 저장하고 비밀 값은 포함하지 않는다. 홈 파일이 유지되지 않는 세션도 고려해 변수를 재설정할 수 있게 한다.

README는 학습 목표, 간단한 아키텍처, 사전 요구사항, 모듈 목차, 시간표, 과금 리소스와 정리 주의사항, 공식 참고 링크를 제공한다.

## 7. 90분 구성

| 모듈 | 내용 | 목표 시간 |
|---|---|---|
| 01 | Cloud Shell, 구독·권한·도구, Fork와 변수 준비 | 10분 |
| 02 | 실습 전용 리소스 그룹·AKS 생성 및 연결 | 20분 |
| 03 | extension 설치 및 준비 상태 확인 | 15분 |
| 04 | Application 생성, 최초 동기화, HTTP 검증 | 15분 |
| 05 | Git 커밋 자동 반영과 self-heal 관찰 | 20분 |
| 06 | 리소스 삭제 및 완료 확인 | 10분 |
| 합계 | Azure 프로비저닝·삭제 대기를 포함한 설계 목표 | 90분 |

실측 시간은 아직 없다. 리허설 결과가 90분을 넘으면 먼저 설명량과 반복 대기를 줄이고, 핵심 단계 제거가 필요하면 사용자에게 범위 변경 승인을 받는다. 공급자 등록과 권한 부여는 사전 점검 항목이며, 행사 전에 완료하도록 권장한다.

## 8. 권한, 비용, 장애 대응

- 구독 전체 Owner를 일괄 요구하지 않는다. 리소스 그룹 생성·AKS 생성·extension 관리 권한과 Kubernetes 접근 권한을 구분해 설명한다.
- extension 설치에 필요한 Kubernetes Extension Contributor 또는 해당 작업을 포함하는 상위 역할과 AKS 조회·변경 권한을 공식 문서로 확인한다.
- 리소스 공급자 등록은 구독 수준의 별도 권한이 필요할 수 있으므로 관리자의 사전 등록 경로를 제공한다. 권한이 없으면 진행이 가능한 것처럼 우회하지 않는다.
- 과금 대상은 노드 VM·디스크·Load Balancer·공개 IP·해당 네트워크 사용량 등이다. Free 요금제가 인프라 전체 무료라는 뜻이 아님을 명시한다.
- 단정적인 비용 수치를 만들지 않고 산정 기준·리전·참조일과 Pricing Calculator 링크를 제공한다. 정확한 단가는 구현 시 확인한다.
- 준비 조건 확인은 제한 시간이 있는 대기와 진단 명령을 사용한다. 실패 시 다음 단계로 넘어가지 않는다.
- 주요 장애: 잘못된 구독·컨텍스트, 공급자 미등록, 권한 부족, SKU·쿼터 부족, extension 설치 실패, Pod Pending, Git 주소·브랜치·경로 오류, sync 실패, 외부 IP 대기, HTTP 실패, 자동 복구 미동작.
- Git 갱신은 즉시 반영을 보장하지 않는다. 기본 폴링을 기다리는 방법과 Application refresh를 요청하는 방법을 구분한다. refresh와 수동 앱 배포를 혼동하지 않는다.
- 자동 복구가 빨라 수동 replicas 3을 놓칠 수 있으므로 watch를 먼저 시작하고 다른 터미널에서 변경하는 관찰 절차를 설명한다.

## 9. 정리의 안전성과 완료 기준

- 기본 삭제 대상은 실습용 Azure 리소스 그룹이며 기존 리소스가 없는 전용 그룹이라는 전제를 다시 확인한다.
- 리소스 그룹 삭제 전에 이름·구독·태그와 포함 리소스를 확인하고 명확히 경고한다.
- 앱 정리는 Argo CD controller가 동작하는 동안 수행한다. Application 삭제만으로 자식 리소스가 항상 삭제된다고 가정하지 않는다. 구현자는 명시적 cascading deletion/finalizer 절차를 정하고 검증한다.
- 앱을 정리한 뒤 namespace·extension을 제거하고 리소스 그룹을 삭제한다. 중간 실패와 중도 종료 상태에서도 전용 리소스 그룹 삭제로 정리할 수 있도록 안내한다.
- 삭제 명령 접수와 삭제 완료를 구분하고 실습 리소스 그룹과 기록한 노드 리소스 그룹의 부재를 확인한다. 노드 리소스 그룹을 수동으로 먼저 삭제하지 않는다.
- GitHub Fork는 비용을 발생시키는 Azure 리소스가 아니며, 보관 또는 웹에서 수동 삭제할 수 있다고 안내한다.
- 삭제한 실습을 가리키는 환경변수 파일·kubeconfig 항목은 해당 실습 항목만 정리한다. 다른 설정을 일괄 삭제하지 않는다.

## 10. 검증과 인수 기준

### 정적 검증

- 문서 내부 링크·경로·모듈 연결과 실행 블록 형식을 확인한다.
- YAML 구문과 Application의 repoURL·path·namespace, 자동 동기화·selfHeal·prune 설정을 확인한다.
- 예제 앱에 readiness/liveness probes, requests/limits, 고정 이미지 버전이 있는지 확인한다.
- 실행 가능한 Bash 블록의 문법을 검사하고, 개념 예시·예상 출력은 실행 대상으로 취급하지 않는다.
- 잘못된 상태를 성공으로 처리하거나 무제한 대기하는 검증 로직이 없는지 확인한다.

### 실제 Azure 리허설

사용자의 별도 실행 승인과 사용 가능한 테스트 구독이 있을 때만 유료 리소스를 만든다. 설계 승인만으로 Azure 배포를 승인받았다고 간주하지 않는다.

1. 문서 순서대로 빈 전용 리소스 그룹에서 시작한다.
2. 참가자 역할의 공개 Fork와 실제 웹 커밋을 사용한다. GitHub 쓰기 인증을 참가자 터미널에 요구하지 않는다.
3. extension `Succeeded`, 구성요소 Ready, Application `Synced`·`Healthy`, HTTP 200을 확인한다.
4. Git replicas 변경 커밋의 SHA와 Application의 반영 revision을 비교하고 실제 replicas·Ready 수가 2인지 확인한다.
5. 수동 replicas 변경이 Git 추가 커밋 없이 2로 복구되는지 확인한다.
6. 새 Cloud Shell 세션에서 변수 복원 또는 재설정 후 검증·정리를 이어갈 수 있는지 확인한다.
7. 앱·extension 정리와 Azure 리소스 그룹·노드 리소스 그룹 삭제 완료를 확인한다.
8. 도구·extension 버전, 리전·SKU·노드 수, 단계별 소요 시간, 조정·실패 사항을 기록한다.

실제 리허설을 수행하지 못했다면 정적 검증 결과와 분리해 미검증으로 표시한다.

## 11. 구현자에게 맡기는 사항

- 정확한 이미지 버전, probes·리소스 수치, 실습 리허설에 맞는 timeout.
- 공개되는 원본 저장소 URL과 문서 링크 확정.
- 변수 이름·실습 리소스 접두사·태그·환경 파일 이름.
- Azure CLI·extension의 검증 버전과 지원 설정 키 확인.
- 제한 시간 내 상태 확인 및 실패 진단의 구체적 명령.
- 정적 검증 도구의 최소 구성과 테스트 파일명.

대상 참가자, 90분 목표, GitHub 웹 편집, extension 사용, 관리 화면 비공개라는 범위를 바꾸는 결정은 구현자가 임의로 확대하지 않는다.

## 12. 참고 자료

- 참고 워크샵: https://github.com/freeman9844/ms-aks-approuting-workshop01
- GA 발표: https://techcommunity.microsoft.com/blog/azurearcblog/gitops-with-argo-cd-extension-for-aks-is-now-generally-available/4562231
- 공식 설치·배포 튜토리얼: https://learn.microsoft.com/azure/azure-arc/kubernetes/tutorial-use-gitops-argocd
- 개념 및 구성요소: https://learn.microsoft.com/azure/azure-arc/kubernetes/conceptual-gitops-argocd
- Argo CD 공식 문서: https://argo-cd.readthedocs.io/en/stable/

확인일: 2026-11-10. GA 발표와 설치 튜토리얼은 AKS의 GA와 Arc의 preview를 구분한다. 개념 문서·포털 화면의 남아 있는 preview 표기만으로 AKS extension을 preview라고 단정하지 않는다.
