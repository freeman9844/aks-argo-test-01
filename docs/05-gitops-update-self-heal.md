# 05 — Git 변경 반영과 자동 복구

> **실행**: 직접 입력합니다. **개념**: 읽기만 합니다. **예상 출력**: 비교용입니다.

예상 소요 시간: 20분.

## 성공 조건

GitHub 웹 커밋의 SHA가 Application에 반영되고 replicas·Ready 수가 2입니다. 이후 클러스터를 수동으로 3으로 변경해도 Git 추가 커밋 없이 2로 복귀합니다.

## 0. 작업 대상 복원

**실행**
```bash
set -euo pipefail
source "$HOME/.aks-argocd-ws-env"
az account set --subscription "$SUBSCRIPTION_ID"
kubectl config use-context "$CLUSTER"
kubectl get application "$APP_NAME" -n argocd
kubectl get deployment "$APP_NAME" -n "$APP_NAMESPACE"
```

04 모듈의 replicas 1 배포가 정상인 상태에서 시작합니다.

## 1. GitHub 웹에서 replicas 변경

자신의 Fork에서 Application이 추적하는 브랜치를 선택합니다. `manifests/app/deployment.yaml`을 열고 연필 아이콘으로 다음 한 줄만 변경합니다.

**개념 — 편집 후 값**
```yaml
spec:
  replicas: 2
```

**Commit changes**를 선택하고 **현재 브랜치에 직접 커밋**합니다. PR이나 다른 브랜치로만 커밋하면 현재 Application은 변경을 읽지 못합니다. 커밋 화면에서 **전체 SHA**를 복사합니다.

## 2. 새 revision과 실제 배포 확인

Git 폴링은 즉시 실행을 보장하지 않습니다. 기본 폴링은 통상 약 3분 이내 주기로 동작하지만 설치 설정·부하에 따라 달라집니다. 다음은 최대 5분씩 상태를 기다립니다.

**실행**
```bash
read -r -p "방금 웹에서 만든 커밋의 전체 SHA: " EXPECTED_REVISION
if [[ ! "$EXPECTED_REVISION" =~ ^[0-9a-f]{40}$ ]]; then
  echo "축약 SHA 대신 전체 40자리 커밋 SHA를 입력하세요." >&2
  exit 1
fi
kubectl wait -n argocd application/"$APP_NAME" \
  --for="jsonpath={.status.sync.revision}=$EXPECTED_REVISION" --timeout=300s
kubectl wait -n argocd application/"$APP_NAME" \
  --for="jsonpath={.status.sync.status}=Synced" --timeout=300s
kubectl wait -n argocd application/"$APP_NAME" \
  --for="jsonpath={.status.health.status}=Healthy" --timeout=300s
kubectl wait -n "$APP_NAMESPACE" deployment/"$APP_NAME" \
  --for="jsonpath={.spec.replicas}=2" --timeout=180s
kubectl rollout status deployment/"$APP_NAME" -n "$APP_NAMESPACE" --timeout=180s
kubectl get application "$APP_NAME" -n argocd -o jsonpath='{.status.sync.revision}{"\n"}'
kubectl get deployment "$APP_NAME" -n "$APP_NAMESPACE"
test "$(kubectl get deployment "$APP_NAME" -n "$APP_NAMESPACE" -o jsonpath='{.status.readyReplicas}')" = 2
```

**예상 출력 — AGE는 예시**
```text
NAME          READY   UP-TO-DATE   AVAILABLE   AGE
gitops-demo   2/2     2            2           15m
```

페이지는 같은 nginx 페이지입니다. 바뀐 것은 replicas이며 이번 단계는 페이지 내용 변경 실습이 아닙니다.

### 지연될 때의 진단

먼저 Application의 repoURL·targetRevision·path와 conditions를 확인합니다.

**실행 — 대기 실패 시에만**
```bash
kubectl describe application "$APP_NAME" -n argocd
kubectl annotate application "$APP_NAME" -n argocd argocd.argoproj.io/refresh=normal --overwrite
```

refresh는 Git 상태를 다시 비교하도록 요청하는 것이며 앱을 직접 적용하거나 수동 sync로 우회하는 것이 아닙니다. 오류를 해결한 뒤 2절을 다시 실행하세요.

## 3. 수동 변경과 self-heal 관찰

**개념**: Git이 원하는 값 2입니다. 사람이 kubectl로 3으로 바꾸면 `selfHeal: true`인 Argo CD가 차이를 감지해 2로 되돌립니다. Pod 3개가 모두 Ready가 되기 전에 복구될 수도 있습니다.

첫 번째 Cloud Shell에서 watch를 시작합니다.

**실행 — 첫 번째 터미널**
```bash
kubectl get deployment "$APP_NAME" -n "$APP_NAMESPACE" --watch
```

Cloud Shell의 새 세션 기능 또는 별도 portal 탭에서 두 번째 Bash 터미널을 엽니다. 홈 파일이 공유되지 않으면 [01의 복구 절차](01-prerequisites.md#5-새-세션에서-재개하는-경우)로 기존 값을 복원합니다. 아래에서는 kubeconfig도 다시 취득합니다. 연결 중인 클러스터 이름을 확인한 후 수동으로 변경합니다.

**실행 — 두 번째 터미널**
```bash
set -euo pipefail
source "$HOME/.aks-argocd-ws-env"
az account set --subscription "$SUBSCRIPTION_ID"
az aks get-credentials --resource-group "$RESOURCE_GROUP" --name "$CLUSTER" \
  --context "$CLUSTER"
kubectl config use-context "$CLUSTER"
BEFORE_REVISION="$(kubectl get application "$APP_NAME" -n argocd -o jsonpath='{.status.sync.revision}')"
test -n "$BEFORE_REVISION"
kubectl scale deployment "$APP_NAME" -n "$APP_NAMESPACE" --replicas=3
kubectl wait -n "$APP_NAMESPACE" deployment/"$APP_NAME" \
  --for="jsonpath={.spec.replicas}=2" --timeout=180s
kubectl rollout status deployment/"$APP_NAME" -n "$APP_NAMESPACE" --timeout=180s
test "$(kubectl get deployment "$APP_NAME" -n "$APP_NAMESPACE" -o jsonpath='{.status.readyReplicas}')" = 2
AFTER_REVISION="$(kubectl get application "$APP_NAME" -n argocd -o jsonpath='{.status.sync.revision}')"
test "$BEFORE_REVISION" = "$AFTER_REVISION"
kubectl get deployment "$APP_NAME" -n "$APP_NAMESPACE"
printf 'Git 변경 없이 복구: %s\n' "$AFTER_REVISION"
```

첫 터미널에서 replicas 변화와 최종 `2/2`를 관찰하고 **Ctrl+C**로 watch를 종료합니다. 일시적인 세 번째 Pod를 놓쳐도 scale 명령 성공·spec.replicas 복귀·최종 Ready·동일 revision으로 검증합니다. GitHub 파일의 replicas도 여전히 2인지 확인합니다.

## 문제 해결

| 증상 | 확인과 대응 |
|---|---|
| 새 SHA로 갱신 안 됨 | 다른 브랜치·다른 Fork·PR에만 커밋하지 않았는지 확인 |
| SHA는 새 값이지만 replicas 1 | sync 오류·실제 Git 파일·추적 path 확인. revision만으로 성공 판정하지 않음 |
| 3에서 복귀하지 않음 | Application의 자동 동기화·selfHeal·controller 상태 확인 |
| Ready 수가 2가 아님 | `kubectl describe deployment`와 Pod events 확인. HPA를 추가하지 않음 |

참고: [Argo CD Automated Sync Policy](https://argo-cd.readthedocs.io/en/stable/user-guide/auto_sync/).

[← 04 — 앱 배포](04-deploy-sample-app.md) | [다음: 06 — 정리](06-cleanup.md)
