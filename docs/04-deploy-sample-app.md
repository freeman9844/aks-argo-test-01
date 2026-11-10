# 04 — Fork에서 샘플 앱 배포

> **실행**: 직접 입력합니다. **개념**: 읽기만 합니다. **예상 출력**: 비교용입니다.

예상 소요 시간: 15분. 첫 동기화·공개 IP 할당 대기를 포함합니다.

## 성공 조건

Application이 자신의 Fork를 바라보고 `Synced`·`Healthy`, nginx replicas 1·Ready 1, 공개 HTTP 응답 200입니다.

## 0. 작업 대상 복원

**실행**
```bash
set -euo pipefail
source "$HOME/.aks-argocd-ws-env"
az account set --subscription "$SUBSCRIPTION_ID"
kubectl config use-context "$CLUSTER"
printf 'Git: %s / branch: %s\n' "$REPO_URL" "$GIT_BRANCH"
```

## 1. 공개 Fork·브랜치·경로 확인

브라우저에서 소유자가 자신의 계정인지 다시 확인합니다. 다음 Git 명령은 공개 저장소를 **읽기만** 하며 clone·commit·push나 쓰기 인증을 하지 않습니다.

**실행**
```bash
SOURCE_REVISION="$(GIT_TERMINAL_PROMPT=0 git ls-remote --exit-code \
  "$REPO_URL" "refs/heads/$GIT_BRANCH" | awk '{print $1}')"
test -n "$SOURCE_REVISION"
export SOURCE_REVISION
export RAW_BASE="https://raw.githubusercontent.com/$GITHUB_OWNER/$GITHUB_REPO/$SOURCE_REVISION"
curl --fail --silent --show-error --max-time 30 "$RAW_BASE/manifests/app/deployment.yaml"
curl --fail --silent --show-error --max-time 30 "$RAW_BASE/manifests/app/service.yaml"
```

404이면 Fork·브랜치·파일 경로를 확인하고 중단합니다. 익명 읽기가 불가능한 저장소에 토큰을 넣어 우회하지 않습니다.

## 2. Application만 부트스트랩

[Application 템플릿](../manifests/argocd/application.yaml)은 Git 저장소 주소와 브랜치를 지정하는 두 자리표시자가 있습니다. 아래에서는 JSON 문자열 이스케이프를 사용해 YAML 문자열로 안전하게 치환합니다. Python 표준 라이브러리만 사용합니다.

**실행**
```bash
export TEMPLATE_FILE="$HOME/$CLUSTER-application.template.yaml"
export APP_FILE="$HOME/$CLUSTER-application.yaml"
curl --fail --silent --show-error --max-time 30 \
  "$RAW_BASE/manifests/argocd/application.yaml" -o "$TEMPLATE_FILE"
python3 - <<'PY'
import json
import os
from pathlib import Path

text = Path(os.environ["TEMPLATE_FILE"]).read_text()
for key, value in {
    "__REPO_URL__": os.environ["REPO_URL"],
    "__GIT_BRANCH__": os.environ["GIT_BRANCH"],
}.items():
    if key not in text:
        raise SystemExit(f"템플릿 자리표시자가 없습니다: {key}")
    text = text.replace(key, json.dumps(value))
if "__REPO_URL__" in text or "__GIT_BRANCH__" in text:
    raise SystemExit("치환되지 않은 자리표시자가 있습니다.")
Path(os.environ["APP_FILE"]).write_text(text)
PY
cat "$APP_FILE"
kubectl apply --dry-run=server -f "$APP_FILE"
kubectl apply -f "$APP_FILE"
```

이 명령은 **Application만** 생성합니다. Deployment·Service는 Argo CD가 Git에서 읽어 생성합니다. 앱 디렉터리를 `kubectl apply`로 직접 적용하지 마세요.

**개념**: `destination.namespace=workshop`과 `CreateNamespace=true`는 앱 namespace를 생성합니다. Application은 `argocd`에 있습니다. `selfHeal`은 수동 변경 복구, `prune`은 Git에서 제거된 관리 리소스의 자동 삭제를 허용하므로 매니페스트를 무심코 삭제하지 않습니다.

## 3. 동기화와 앱 상태 확인

**실행**
```bash
kubectl wait -n argocd application/"$APP_NAME" \
  --for="jsonpath={.status.sync.revision}=$SOURCE_REVISION" --timeout=300s
kubectl wait -n argocd application/"$APP_NAME" \
  --for="jsonpath={.status.sync.status}=Synced" --timeout=300s
kubectl wait -n argocd application/"$APP_NAME" \
  --for="jsonpath={.status.health.status}=Healthy" --timeout=300s
kubectl rollout status deployment/"$APP_NAME" -n "$APP_NAMESPACE" --timeout=180s
kubectl get application "$APP_NAME" -n argocd
kubectl get deployments,pods,services -n "$APP_NAMESPACE"
test "$(kubectl get deployment "$APP_NAME" -n "$APP_NAMESPACE" -o jsonpath='{.spec.replicas}')" = 1
test "$(kubectl get deployment "$APP_NAME" -n "$APP_NAMESPACE" -o jsonpath='{.status.readyReplicas}')" = 1
```

**예상 출력 — 실제 열 구성은 버전에 따라 달라질 수 있습니다**
```text
NAME          SYNC STATUS   HEALTH STATUS
gitops-demo   Synced        Healthy
```

## 4. HTTP 확인

공개되는 것은 nginx 샘플 앱뿐입니다. 관리 화면을 LoadBalancer로 노출하지 않습니다. 학습용 **HTTP**이므로 비밀·개인정보를 입력하지 마세요.

**실행**
```bash
APP_IP=""
for attempt in $(seq 1 60); do
  APP_IP="$(kubectl get service "$APP_NAME" -n "$APP_NAMESPACE" \
    -o jsonpath='{.status.loadBalancer.ingress[0].ip}')"
  if [ -n "$APP_IP" ]; then break; fi
  sleep 5
done
if [ -z "$APP_IP" ]; then
  kubectl describe service "$APP_NAME" -n "$APP_NAMESPACE"
  echo "300초 내 공개 IP가 할당되지 않았습니다." >&2
  exit 1
fi
HTTP_CODE="$(curl --silent --show-error --output /dev/null --write-out '%{http_code}' \
  --connect-timeout 10 --max-time 30 "http://$APP_IP")"
printf 'HTTP: %s / URL: http://%s\n' "$HTTP_CODE" "$APP_IP"
test "$HTTP_CODE" = 200
```

브라우저에서 출력된 `http://<IP>`를 열면 nginx 기본 페이지가 보입니다. `https://`가 아닙니다.

## 문제 해결

| 증상 | 확인과 대응 |
|---|---|
| `ComparisonError`·`SyncError` | `kubectl describe application gitops-demo -n argocd`에서 repoURL·targetRevision·path와 오류 확인 |
| 브랜치를 바꿨는데 반영 안 됨 | Application의 targetRevision과 GitHub 편집 브랜치가 동일한지 확인 |
| `ImagePullBackOff` | nginx 공개 이미지 송신·Docker Hub rate limit 확인. 사용 태그는 `nginx:1.28.3` |
| `Healthy`가 되지 않음 | Pod events·probes·resource requests 확인. sync 성공만으로 앱 정상 판정하지 않음 |
| IP는 있으나 HTTP 실패 | Service events·Pod Ready·EndpointSlice·네트워크 정책 확인 후 요청 재시도 |

[← 03 — extension 설치](03-install-argocd-extension.md) | [다음: 05 — Git 변경·자동 복구](05-gitops-update-self-heal.md)
