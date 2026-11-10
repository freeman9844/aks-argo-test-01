# 03 — Argo CD extension 설치

> **실행**: 직접 입력합니다. **개념**: 읽기만 합니다. **예상 출력**: 비교용입니다.

예상 소요 시간: 15분. 설치 대기를 포함한 설계 목표입니다.

## 성공 조건

Azure extension이 `Succeeded`, Argo CD Deployment·StatefulSet이 준비 완료입니다. 관리 화면은 공개하지 않습니다.

## 0. 작업 대상 복원

**실행**
```bash
set -euo pipefail
source "$HOME/.aks-argocd-ws-env"
az account set --subscription "$SUBSCRIPTION_ID"
kubectl config use-context "$CLUSTER"
az aks show -g "$RESOURCE_GROUP" -n "$CLUSTER" --query '{State:provisioningState,Identity:identity.type}' -o table
kubectl get nodes
```

관리 ID 기반 AKS가 필요합니다. 앞 모듈의 새 클러스터를 사용하며, 기존 운영 클러스터에 적용하지 않습니다.

## 1. Azure CLI extension 준비

`Microsoft.ArgoCD`는 AKS에 설치되는 **클러스터 extension**, `k8s-extension`은 이를 관리하는 **Azure CLI 확장 패키지**입니다.

**실행**
```bash
installed_extensions="$(az extension list --query '[].name' -o tsv)"
if grep -Fxq k8s-extension <<< "$installed_extensions"; then
  az extension update --name k8s-extension
else
  az extension add --name k8s-extension
fi
az extension show --name k8s-extension --query '{Name:name,Version:version}' -o table
```

## 2. 비HA 설치

[공식 튜토리얼](https://learn.microsoft.com/azure/azure-arc/kubernetes/tutorial-use-gitops-argocd)에 따르면 기본 Redis HA 구성은 노드 4개가 필요합니다. 이 실습은 비용·구성을 줄이기 위해 `redis-ha.enabled=false`를 명시합니다. 운영 환경에서는 별도의 HA·용량·보안 설계가 필요합니다.

**실행**
```bash
az k8s-extension create --resource-group "$RESOURCE_GROUP" \
  --cluster-name "$CLUSTER" --cluster-type managedClusters \
  --name "$EXTENSION_NAME" --extension-type Microsoft.ArgoCD \
  --scope cluster --release-namespace argocd \
  --config "redis-ha.enabled=false"
az k8s-extension show --resource-group "$RESOURCE_GROUP" \
  --cluster-name "$CLUSTER" --cluster-type managedClusters --name "$EXTENSION_NAME" \
  --query '{State:provisioningState,Type:extensionType,Version:version}' -o table
test "$(az k8s-extension show -g "$RESOURCE_GROUP" --cluster-name "$CLUSTER" \
  --cluster-type managedClusters -n "$EXTENSION_NAME" --query provisioningState -o tsv)" = Succeeded
```

GA용 기본 release train을 사용합니다. 출력된 실제 extension 버전을 기록하세요. 이전 `0.0.x`·preview 예제와 설정 키를 섞지 않습니다. 설치 성공만으로 앱 배포가 완료된 것은 아닙니다.

## 3. Kubernetes 구성요소 확인

**실행**
```bash
kubectl get deployments,statefulsets,pods -n argocd
workloads="$(kubectl get deployments,statefulsets -n argocd -o name)"
if [ -z "$workloads" ]; then
  echo "Argo CD 워크로드가 없습니다. extension 상태와 namespace를 확인하세요." >&2
  exit 1
fi
while IFS= read -r workload; do
  kubectl rollout status -n argocd "$workload" --timeout=300s
done <<< "$workloads"
kubectl get pods -n argocd
kubectl get crd applications.argoproj.io
```

application-controller는 Git과 live 상태 비교·동기화, repo-server는 Git 조회·매니페스트 생성, server는 API·UI, Redis는 캐시를 담당합니다. 실제 리소스 이름과 replica 수는 설치 버전의 출력으로 확인합니다.

## 설정 변경 원칙

extension이 관리하는 Argo CD ConfigMap을 `kubectl edit`로 수정하지 않습니다. 필요한 설정은 `az k8s-extension update --config ...` 등 extension 구성 API를 사용합니다. 이 실습에서는 추가 설정 변경이 없습니다.

## 문제 해결

| 증상 | 확인과 대응 |
|---|---|
| extension `Failed`·권한 오류 | `az k8s-extension show` 전체 출력의 error 확인. 공급자·extension 관리 권한 점검 |
| Pod `Pending` | `kubectl describe pod -n argocd <실제 Pod 이름>`과 노드 allocatable 확인. HA=false 설정 확인 |
| `Insufficient cpu`·메모리 | `kubectl describe nodes`로 requests 확인 후 사양·노드 수 조정 여부 결정. 자동 확장으로 숨기지 않음 |
| 이미지 pull 오류 | `kubectl get events -n argocd --sort-by=.lastTimestamp`에서 레지스트리·송신 제한 확인 |
| rollout 제한 시간 초과 | 다음 모듈로 진행하지 말고 해당 workload·Pod·events 확인 |

필요한 송신 대상과 설치 조건은 [공식 튜토리얼의 Network requirements](https://learn.microsoft.com/azure/azure-arc/kubernetes/tutorial-use-gitops-argocd#network-requirements)를 확인합니다.

[← 02 — 환경 준비](02-environment-setup.md) | [다음: 04 — 앱 배포](04-deploy-sample-app.md)
