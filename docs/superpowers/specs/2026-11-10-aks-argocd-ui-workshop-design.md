# AKS Argo CD 워크샵 UI 중심 전환 설계

작성일: 2026-11-10

상태: 사용자 승인 완료 (2026-11-10)

## 의도와 결정

Kubernetes는 알지만 Azure는 초급인 참가자가 Argo CD의 앱 배포·동기화·상태·삭제를 화면에서 확인하도록 기존 워크샵을 전환한다. 새 앱이나 Azure 서비스를 추가하는 작업이 아니라 기존 6개 모듈의 진행 방식을 바꾸는 변경이다.

사용자는 관리 화면을 공개하지 않는 **참가자 PC의 로컬 포트포워딩**을 선택했다. 기존의 Cloud Shell만으로 진행한다는 조건은 로컬 Azure CLI·kubectl 준비가 필요한 구성으로 바뀐다.

## 목표와 비목표

- 목표: UI 로그인, NEW APP, 첫 수동 SYNC, 자동 동기화·Prune·Self Heal 활성화, Git 변경 관찰, cascading deletion을 단계별로 안내한다.
- 유지: 공개 Fork·GitHub 웹 편집, nginx, 단일 Application·AKS, 비HA extension, replicas 1 → 2 → 수동 3 → 자동 복구 2.
- CLI 유지: Azure 리소스 생성·extension 설치·UI 연결 준비, drift를 만드는 수동 변경 1회, namespace·extension·리소스 그룹 정리.
- 비목표: UI용 공개 LoadBalancer·Ingress·도메인·SSO·TLS 인증서 발급, 실제 Azure 리허설, 저장소 공개 여부 변경.

## 접근 방식

| 방식 | 장단점 | 결정 |
|---|---|---|
| 참가자 PC의 로컬 포트포워딩 | 관리 화면 공개와 추가 IP 비용 없음. PC 도구 설치·별도 Azure 로그인 필요 | 사용자 선택 |
| 참가자 공인 IP 제한 HTTPS LoadBalancer | Cloud Shell 흐름 유지. 외부 관리 endpoint·추가 IP·삭제 절차 필요 | 제외 |

## 변경 설계

1. **01 사전 준비:** 로컬 Azure CLI·kubectl 준비와 PC에서 AKS API에 접근할 수 있어야 함을 추가한다. 참가자용 로컬 명령은 Windows PowerShell을 기준으로 제안한다. macOS·Linux 사용자는 별도 설치 안내를 참조하며, 이번 기본 명령을 모든 OS에서 그대로 실행할 수 있다고 설명하지 않는다.
2. **02 환경 준비:** 기존 Cloud Shell 생성 흐름을 유지한다. 이후 PC에서 사용할 구독·리소스 그룹·AKS 이름을 확인하는 절차를 둔다.
3. **03 extension 설치·UI 접속:** 설치 검증 후 로컬 PowerShell에서 Azure 로그인·구독 선택·기존 AKS의 kubeconfig 취득을 안내한다. `127.0.0.1:8080`에서 Service의 HTTPS 포트로 포워딩하고 브라우저에서 로컬 HTTPS로 접속한다. 포워딩 터미널은 열어 둔다. Cloud Shell의 localhost와 PC의 localhost를 혼동하지 않게 한다.
4. **초기 로그인:** 실습 클러스터의 초기 관리자 비밀번호를 참가자 PC에서만 취득한다. 비밀번호를 Git·환경 파일·문서 출력 예시·스크린샷에 남기지 않는다. 로컬 주소의 자체 서명 인증서 주의사항과 비밀번호 변경·초기 비밀번호 Secret 정리를 안내한다. 실제 비밀을 문서 작성 중 조회하지 않는다.
5. **04 앱 배포:** CLI Application 렌더링·적용을 기본 흐름에서 제거한다. UI에서 이름 `gitops-demo`, project `default`, 자신의 Fork·브랜치, `manifests/app`, in-cluster·`workshop`, namespace 자동 생성 옵션을 입력한다. 첫 Sync는 Manual로 진행해 OutOfSync에서 Synced·Healthy로 바뀌는 과정과 Deployment·Service·Pod 트리를 확인한다. 앱 HTTP 확인도 UI의 Service 상태와 브라우저를 중심으로 한다.
6. **05 GitOps:** UI에서 자동 동기화·Prune·Self Heal을 활성화한 후 GitHub 웹에서 replicas를 2로 커밋한다. UI에서 반영 revision과 Deployment·Pod 상태를 확인한다. drift 생성의 `kubectl scale`은 Cloud Shell에서 한 번 실행하고 결과는 UI로 관찰한다. CLI 검증은 문제 해결용 보조 경로로만 제공한다.
7. **06 정리:** UI에서 Application의 자식 리소스를 포함한 foreground cascading deletion을 수행한다. 완료 후 로컬 포트포워딩을 중단하고 Cloud Shell에서 namespace·extension·전용 그룹을 제거한다. UI 접속 불가·중도 종료의 기존 안전한 정리 경로는 유지한다.
8. **참고 YAML:** 기존 Application 템플릿은 기본 실행 경로가 아닌 자동 동기화 설정 이후의 참고 예제로 명시한다. 앱 Deployment·Service를 직접 적용하는 우회 안내는 추가하지 않는다.
9. **README·기존 설계/계획:** 로컬 설치 없음·UI 비공개와 UI 미사용의 혼동·CLI 부트스트랩 기본 경로 등 변경과 충돌하는 설명을 함께 갱신한다. 공개 Fork 실습에 필요한 원본 공개 상태 확인은 유지한다.

## 제약과 검증

- 약 90분 실습 목표는 유지하되 로컬 도구 설치는 사전 준비 시간으로 구분한다. 실제 소요 시간은 리허설 전에는 확정하지 않는다.
- Argo CD server의 TLS·Service 공개 설정을 바꾸지 않고 기본 HTTPS를 포워딩한다. extension 관리 ConfigMap을 직접 편집하지 않는다.
- UI의 정확한 레이블·메뉴 위치는 버전에 따라 달라질 수 있다고 명시하고 공식 가이드와 대조한다. 직접 캡처하지 않은 화면을 실측 스크린샷으로 제시하지 않는다.
- 회귀 테스트 3개를 유지하고 문서 링크, Bash·PowerShell 구문, YAML 및 단계 간 이름·정책·삭제 순서를 검사한다.
- 실제 로그인·브라우저 UI·Sync·HTTP·삭제는 별도 Azure 리허설 승인 전에는 미검증으로 표시한다.
- GitHub push·공개 전환과 실제 Azure 리소스 실행은 문서 수정 승인과 구분한다.

## 구현자 판단

Windows PowerShell 기본 안내, 6개 모듈 유지, 로컬 도구 설치를 사전 준비로 분리하는 것은 작성자의 제안이다. 구체적인 명령·UI 필드 설명·진단 절차는 공식 문서를 확인해 작성한다.

## 근거

- https://argo-cd.readthedocs.io/en/stable/getting_started/
- https://argo-cd.readthedocs.io/en/stable/user-guide/auto_sync/
- https://argo-cd.readthedocs.io/en/stable/user-guide/app_deletion/
- https://learn.microsoft.com/azure/azure-arc/kubernetes/tutorial-use-gitops-argocd
