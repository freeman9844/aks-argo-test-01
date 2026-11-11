# 02. AKS 환경 준비

> 목표 시간 20분. 전용 리소스 그룹과 AKS를 만들고 접속을 확인합니다. 생성 대기를 포함한 목표이며 실측값은 아닙니다.

## 목표

실습 전용 리소스 그룹과 AKS가 생성되고, 올바른 컨텍스트에서 노드 2개가 Ready입니다. 노드 리소스 그룹 이름이 저장되어 있습니다.

## 0. 변수 복원

👁️ **설명**

01에서 저장한 변수를 읽고 실제 배포할 구독·이름·리전을 먼저 확인합니다.

🟢 **실행**

**실행 위치: Cloud Shell Bash**

```bash
set -euo pipefail
source "$HOME/.aks-argocd-ws-env"
az account set --subscription "$SUBSCRIPTION_ID"
az account show --query '{Name:name,State:state}' -o table
printf '생성 대상: %s / %s / %s\n' "$RESOURCE_GROUP" "$CLUSTER" "$LOCATION"
```

📋 **확인**

출력된 구독과 생성 대상이 이번 실습의 값이어야 합니다. 다른 실습 이름이면 생성하지 않습니다.

## 1. 새 전용 리소스 그룹

👁️ **설명**

리소스 그룹은 이번 실습의 자원을 함께 관리하고 정리할 경계입니다.

⚠️ **주의**

기존 서비스가 있는 그룹을 재사용하지 않습니다. 아래부터 VM·디스크·네트워크 리소스에 **비용이 발생**합니다.

🟢 **실행**

**실행 위치: Cloud Shell Bash**

```bash
if [ "$(az group exists --name "$RESOURCE_GROUP")" != false ]; then
  echo "그룹이 이미 존재하거나 조회에 실패했습니다. 기존 실습인지 확인하고 중단하세요." >&2
  exit 1
fi
az group create --name "$RESOURCE_GROUP" --location "$LOCATION" \
  --tags workload=aks-argocd-workshop environment=workshop -o table
```

📋 **확인**

새 그룹이 지정한 이름·리전으로 생성됐고 `workload=aks-argocd-workshop`, `environment=workshop` 태그가 있는지 확인합니다.

## 2. AKS 생성

👁️ **설명**

Automatic이 아닌 일반 Standard 클러스터를 기본 SKU로 생성하고, control plane **Free 요금제**를 선택합니다. Free는 노드 VM·디스크·Load Balancer까지 무료라는 뜻이 아닙니다.

관리 ID·Azure CNI Overlay·노드 2개를 사용하는 학습용 구성이며, 운영용 HA·사설 API·Entra RBAC 설계는 다루지 않습니다. `koreacentral`의 SKU 가용성·쿼터·조직 정책을 사전에 확인하세요. Kubernetes 버전은 이 리전에서 생성 시 지원되는 기본 버전을 사용합니다.

🟢 **실행**

**실행 위치: Cloud Shell Bash**

```bash
az aks create --resource-group "$RESOURCE_GROUP" --name "$CLUSTER" \
  --location "$LOCATION" --tier free \
  --node-count 2 --node-vm-size Standard_D2s_v5 \
  --enable-managed-identity --network-plugin azure --network-plugin-mode overlay \
  --generate-ssh-keys -o table
az aks show --resource-group "$RESOURCE_GROUP" --name "$CLUSTER" \
  --query '{State:provisioningState,Version:kubernetesVersion,Identity:identity.type}' -o table
```

📋 **확인**

`Succeeded`와 관리 ID를 확인합니다. 생성이 실패하면 extension 설치로 넘어가지 말고 에러를 해결하거나 [정리](06-cleanup.md)로 이동합니다. `--generate-ssh-keys`가 생성한 키는 공개 저장소에 넣지 않습니다.

## 3. 접속 및 노드 리소스 그룹 기록

👁️ **설명**

이 AKS의 자격 증명을 취득하고 노드 준비 상태를 확인합니다. 정리에 필요한 관리 노드 그룹 이름도 저장합니다.

🟢 **실행**

**실행 위치: Cloud Shell Bash**

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

📋 **확인**

컨텍스트가 이번 AKS이며 **노드 2개가 모두 Ready**여야 합니다. 아래는 비교용 출력이고 이름·버전은 달라집니다.

```text
NAME                            STATUS   ROLES    AGE   VERSION
aks-nodepool1-example-vmss000000 Ready    <none>   3m    vX.Y.Z
aks-nodepool1-example-vmss000001 Ready    <none>   3m    vX.Y.Z
```

노드 리소스 그룹(`MC_...`)에는 AKS가 관리하는 VM·디스크·네트워크 리소스가 있습니다. 직접 먼저 삭제하지 않습니다.

## 4. 로컬 UI 접속을 위한 대상 이름 확인

👁️ **설명**

다음 모듈에서 **참가자 PC**에 입력할 값입니다. 비밀번호·토큰·kubeconfig가 아니라 기존 리소스의 이름만 확인합니다.

🟢 **실행**

**실행 위치: Cloud Shell Bash**

```bash
az account show --query name -o tsv
printf '리소스 그룹: %s\nAKS 이름: %s\n' "$RESOURCE_GROUP" "$CLUSTER"
```

📋 **확인**

표시된 구독·그룹·AKS 이름을 다음 모듈의 PC 입력값으로 사용합니다. PC에서는 별도로 Azure에 로그인하고 이 클러스터의 자격 증명을 취득합니다. Cloud Shell에서 포워딩한 localhost를 PC의 localhost로 열 수는 없습니다.

## 트러블슈팅

| 증상 | 확인과 대응 |
|---|---|
| `SKUNotAvailable`·`AllocationFailed` | 같은 리전의 SKU 가용성 또는 다른 리전을 확인. 변경한 위치·사양을 환경 파일에도 반영 |
| `QuotaExceeded` | 리전별 vCPU 쿼터를 관리자에게 요청. 실패 상태를 성공으로 처리하지 않음 |
| `RequestDisallowedByPolicy` | 거부된 정책을 확인. 보안 정책을 무력화하지 말고 관리자와 실습 가능 범위 협의 |
| kubectl 접속 실패 | 구독·AKS provisioningState·current-context·공개 API 접근 정책 확인 |
| 노드가 Ready가 아님 | `kubectl describe nodes`, `kubectl get events -A --sort-by=.lastTimestamp` 확인 후 중단 |

## 재개 시 주의

⚠️ **주의**

AKS가 이미 생성됐다면 1~2절을 재실행하지 않고 0절과 3절로 상태를 확인합니다. 생성 실패·중도 종료 상태에서도 전용 리소스 그룹 전체가 정리 대상입니다.

## 완료 체크

- [ ] 이번 실행의 전용 리소스 그룹과 소유 태그를 확인했습니다.
- [ ] AKS가 `Succeeded`이며 관리 ID를 사용합니다.
- [ ] 올바른 컨텍스트에서 노드 2개가 모두 Ready입니다.
- [ ] 관리 노드 그룹 이름을 저장하고 PC에 입력할 대상 이름을 확인했습니다.

## 다음 단계

[← 01. 실습 준비](01-prerequisites.md) | [README](../README.md) | [다음: 03. extension 설치·UI 접속 →](03-install-argocd-extension.md)
