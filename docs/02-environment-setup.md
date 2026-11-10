# 02 — 환경 준비

> **실행**: 직접 입력합니다. **개념**: 읽기만 합니다. **예상 출력**: 비교용입니다.

예상 소요 시간: 20분. AKS 생성 대기를 포함한 목표이며 실측값은 아닙니다.

## 성공 조건

실습 전용 리소스 그룹과 AKS가 생성되고, 올바른 컨텍스트에서 노드 2개가 Ready입니다. 노드 리소스 그룹 이름이 저장되어 있습니다.

## 0. 변수 복원

**실행**
```bash
set -euo pipefail
source "$HOME/.aks-argocd-ws-env"
az account set --subscription "$SUBSCRIPTION_ID"
az account show --query '{Name:name,State:state}' -o table
printf '생성 대상: %s / %s / %s\n' "$RESOURCE_GROUP" "$CLUSTER" "$LOCATION"
```

## 1. 새 전용 리소스 그룹

기존 서비스가 있는 그룹을 재사용하지 않습니다. 아래부터 VM·디스크·네트워크 리소스에 **비용이 발생**합니다.

**실행**
```bash
if [ "$(az group exists --name "$RESOURCE_GROUP")" != false ]; then
  echo "그룹이 이미 존재하거나 조회에 실패했습니다. 기존 실습인지 확인하고 중단하세요." >&2
  exit 1
fi
az group create --name "$RESOURCE_GROUP" --location "$LOCATION" \
  --tags workload=aks-argocd-workshop environment=workshop -o table
```

## 2. AKS 생성

**개념**: Automatic이 아닌 일반 Standard 클러스터를 기본 SKU로 생성하고, control plane **Free 요금제**를 선택합니다. Free는 노드 VM·디스크·Load Balancer까지 무료라는 뜻이 아닙니다.

관리 ID·Azure CNI Overlay·노드 2개를 사용하는 학습용 구성이며, 운영용 HA·사설 API·Entra RBAC 설계는 다루지 않습니다. `koreacentral`의 SKU 가용성·쿼터·조직 정책을 사전에 확인하세요. Kubernetes 버전은 이 리전에서 생성 시 지원되는 기본 버전을 사용합니다.

**실행**
```bash
az aks create --resource-group "$RESOURCE_GROUP" --name "$CLUSTER" \
  --location "$LOCATION" --tier free \
  --node-count 2 --node-vm-size Standard_D2s_v5 \
  --enable-managed-identity --network-plugin azure --network-plugin-mode overlay \
  --generate-ssh-keys -o table
az aks show --resource-group "$RESOURCE_GROUP" --name "$CLUSTER" \
  --query '{State:provisioningState,Version:kubernetesVersion,Identity:identity.type}' -o table
```

`Succeeded`와 관리 ID를 확인합니다. 생성이 실패하면 extension 설치로 넘어가지 말고 에러를 해결하거나 [정리](06-cleanup.md)로 이동합니다. `--generate-ssh-keys`가 생성한 키는 공개 저장소에 넣지 않습니다.

## 3. 접속 및 노드 리소스 그룹 기록

**실행**
```bash
az aks get-credentials --resource-group "$RESOURCE_GROUP" --name "$CLUSTER" \
  --context "$CLUSTER"
kubectl config use-context "$CLUSTER"
kubectl config current-context
kubectl wait --for=condition=Ready nodes --all --timeout=300s
kubectl get nodes
NODE_RESOURCE_GROUP="$(az aks show --resource-group "$RESOURCE_GROUP" \
  --name "$CLUSTER" --query nodeResourceGroup -o tsv)"
test -n "$NODE_RESOURCE_GROUP"
export NODE_RESOURCE_GROUP
printf 'export NODE_RESOURCE_GROUP=%q\n' "$NODE_RESOURCE_GROUP" >> "$HOME/.aks-argocd-ws-env"
printf 'AKS 관리 노드 그룹: %s\n' "$NODE_RESOURCE_GROUP"
```

**예상 출력 — 이름과 버전은 달라집니다**
```text
NAME                            STATUS   ROLES    AGE   VERSION
aks-nodepool1-example-vmss000000 Ready    <none>   3m    vX.Y.Z
aks-nodepool1-example-vmss000001 Ready    <none>   3m    vX.Y.Z
```

노드 리소스 그룹(`MC_...`)에는 AKS가 관리하는 VM·디스크·네트워크 리소스가 있습니다. 직접 먼저 삭제하지 않습니다.

## 문제 해결

| 증상 | 확인과 대응 |
|---|---|
| `SKUNotAvailable`·`AllocationFailed` | 같은 리전의 SKU 가용성 또는 다른 리전을 확인. 변경한 위치·사양을 환경 파일에도 반영 |
| `QuotaExceeded` | 리전별 vCPU 쿼터를 관리자에게 요청. 실패 상태를 성공으로 처리하지 않음 |
| `RequestDisallowedByPolicy` | 거부된 정책을 확인. 보안 정책을 무력화하지 말고 관리자와 실습 가능 범위 협의 |
| kubectl 접속 실패 | 구독·AKS provisioningState·current-context·공개 API 접근 정책 확인 |
| 노드가 Ready가 아님 | `kubectl describe nodes`, `kubectl get events -A --sort-by=.lastTimestamp` 확인 후 중단 |

## 재개 시 주의

AKS가 이미 생성됐다면 1~2절을 재실행하지 않고 0절과 3절로 상태를 확인합니다. 생성 실패·중도 종료 상태에서도 전용 리소스 그룹 전체가 정리 대상입니다.

[← 01 — 사전 준비](01-prerequisites.md) | [다음: 03 — extension 설치](03-install-argocd-extension.md)
