# 06 — 정리

> **실행**: 직접 입력합니다. **개념**: 읽기만 합니다. **예상 출력**: 비교용입니다.

예상 소요 시간: 10분 목표. Azure 삭제 대기가 더 길어질 수 있으며, 삭제 요청 접수만으로 완료라고 보지 않습니다.

## 성공 조건

실습 리소스 그룹과 AKS 관리 노드 리소스 그룹이 모두 없어지고 해당 실습의 로컬 설정만 정리됩니다.

> **삭제 주의:** 이 모듈은 실습 전용 리소스 그룹의 모든 리소스를 삭제합니다. 기존 서비스가 들어 있는 그룹에 실행하지 마세요. GitHub Fork 삭제는 별개입니다.

## 1. 삭제 대상 확인 — 정상·중도 종료 공통

**실행**
```bash
set -euo pipefail
source "$HOME/.aks-argocd-ws-env"
az account set --subscription "$SUBSCRIPTION_ID"
az account show --query '{Name:name,State:state}' -o table
az group show --name "$RESOURCE_GROUP" --query '{Name:name,Tags:tags}' -o json
az resource list --resource-group "$RESOURCE_GROUP" --query '[].{Name:name,Type:type}' -o table
test "$(az group show -n "$RESOURCE_GROUP" --query tags.workload -o tsv)" = aks-argocd-workshop
test "$(az group show -n "$RESOURCE_GROUP" --query tags.environment -o tsv)" = workshop
read -r -p "삭제할 실습 리소스 그룹 이름을 다시 입력: " CONFIRM_GROUP
if [ "$CONFIRM_GROUP" != "$RESOURCE_GROUP" ]; then
  echo "이름이 일치하지 않습니다. 삭제를 중단합니다." >&2
  exit 1
fi
```

환경 파일이 없다면 [01의 복구 절차](01-prerequisites.md#5-새-세션에서-재개하는-경우)를 사용합니다. 그룹이 이미 없다면 삭제를 다시 실행하지 말고 기록한 노드 그룹의 부재를 확인한 후 5절로 이동합니다.

## 2. 노드 리소스 그룹 이름 확인

AKS 생성에 성공했다면 환경 파일에 기록되어 있습니다. 생성 중 중단했다면 그룹 안에 AKS 리소스가 있는지 먼저 확인합니다.

**실행**
```bash
CLUSTER_ID="$(az resource list -g "$RESOURCE_GROUP" \
  --resource-type Microsoft.ContainerService/managedClusters \
  --query "[?name=='$CLUSTER'].id | [0]" -o tsv)"
if [ -n "$CLUSTER_ID" ]; then
  NODE_RESOURCE_GROUP="$(az aks show -g "$RESOURCE_GROUP" -n "$CLUSTER" --query nodeResourceGroup -o tsv)"
  test -n "$NODE_RESOURCE_GROUP"
  export NODE_RESOURCE_GROUP
  printf 'export NODE_RESOURCE_GROUP=%q\n' "$NODE_RESOURCE_GROUP" >> "$HOME/.aks-argocd-ws-env"
fi
printf '실습 그룹: %s / 노드 그룹: %s\n' "$RESOURCE_GROUP" "${NODE_RESOURCE_GROUP:-미생성 또는 미확인}"
```

AKS가 전혀 생성되지 않았다면 노드 그룹도 없을 수 있습니다. 생성 실패·삭제 중인 AKS에 노드 그룹이 남았는지 불명확하면 portal의 활동 로그·리소스 목록으로 확인합니다. 이름을 추측해 삭제하지 않습니다.

## 3. 정상 경로 — controller가 동작하는 경우

앱은 Git에서 관리되므로 Deployment·Service만 수동 삭제하면 다시 생성될 수 있습니다. 먼저 Application을 삭제합니다. 템플릿의 finalizer가 controller에 자식 리소스 정리를 요청합니다.

**실행 — 정상 배포를 완료한 경우**
```bash
kubectl config use-context "$CLUSTER"
kubectl get application "$APP_NAME" -n argocd -o jsonpath='{.metadata.finalizers}{"\n"}'
kubectl delete application "$APP_NAME" -n argocd --wait=true --timeout=300s
remaining="$(kubectl get deployments,services -n "$APP_NAMESPACE" -o name)"
if [ -n "$remaining" ]; then
  printf '앱 리소스가 남아 있습니다:\n%s\n' "$remaining" >&2
  exit 1
fi
kubectl delete namespace "$APP_NAMESPACE" --wait=true --timeout=180s
az k8s-extension delete --resource-group "$RESOURCE_GROUP" \
  --cluster-name "$CLUSTER" --cluster-type managedClusters --name "$EXTENSION_NAME" --yes
```

Application 삭제가 timeout이면 extension을 먼저 제거하지 않습니다. controller·Application·Service events를 확인합니다. finalizer가 없거나 앱이 남으면 다음의 전용 그룹 전체 정리 경로로 이동합니다.

### 중도 종료 경로

AKS 생성 실패, extension 설치 실패, Application 미생성, controller가 이미 제거되어 finalizer가 멈춘 경우에는 **3절을 건너뛰고** 1~2절의 삭제 대상 확인 후 4절로 이동합니다. 클러스터 내부 정리가 불가능해도 전용 Azure 그룹 삭제로 AKS와 관리 노드 리소스를 정리할 수 있습니다.

finalizer를 무조건 강제 제거하거나 노드 그룹·공인 IP를 개별적으로 먼저 삭제하지 않습니다.

## 4. 전용 그룹 삭제 및 완료 대기

1절에서 확인한 전용 그룹만 삭제합니다.

**실행**
```bash
az group delete --name "$RESOURCE_GROUP" --yes --no-wait
for attempt in $(seq 1 120); do
  GROUP_EXISTS="$(az group exists --name "$RESOURCE_GROUP")"
  if [ "$GROUP_EXISTS" = false ]; then break; fi
  sleep 10
done
if [ "$GROUP_EXISTS" != false ]; then
  echo "20분 내 그룹 삭제가 완료되지 않았습니다. portal의 삭제 오류를 확인하세요." >&2
  exit 1
fi
if [ -n "${NODE_RESOURCE_GROUP:-}" ]; then
  for attempt in $(seq 1 60); do
    NODE_GROUP_EXISTS="$(az group exists --name "$NODE_RESOURCE_GROUP")"
    if [ "$NODE_GROUP_EXISTS" = false ]; then break; fi
    sleep 10
  done
  if [ "$NODE_GROUP_EXISTS" != false ]; then
    echo "AKS 노드 그룹이 아직 남아 있습니다. 비용과 AKS 삭제 오류를 확인하세요." >&2
    exit 1
  fi
else
  echo "노드 그룹 이름이 없습니다. AKS 생성 이력과 잔여 노드 리소스를 확인한 뒤 완료로 판정하세요." >&2
  exit 1
fi
```

조회 권한 오류는 `false`로 간주하지 않습니다. 삭제 중인 리소스·오류·잠금은 portal에서 확인하고 해결합니다. 노드 그룹이 남았거나 그 상태를 확인하지 못했다면 정리 완료가 아닙니다.

## 5. 해당 실습의 로컬 흔적

**실행 — Azure 삭제 완료 확인 후**
```bash
kubectl config get-contexts
```

목록에서 이 실습의 `$CLUSTER` 컨텍스트만 확인한 뒤 삭제합니다.

**실행**
```bash
kubectl config delete-context "$CLUSTER"
```

kubeconfig의 사용자·클러스터 항목은 다른 컨텍스트가 참조할 수 있으므로 일괄 삭제하지 않습니다. 필요하면 `kubectl config view`에서 참조 관계를 확인한 후 이 실습 전용 항목만 수동 제거합니다. kubeconfig 내용에는 자격 증명이 있을 수 있으므로 공유하지 마세요.

**실행 — 이 실습에서 생성한 세 파일만**
```bash
rm -f -- "$HOME/$CLUSTER-application.template.yaml" "$HOME/$CLUSTER-application.yaml"
rm -- "$HOME/.aks-argocd-ws-env"
```

GitHub Fork는 남겨도 Azure 요금이 발생하지 않습니다. 삭제하려면 자신의 Fork의 **Settings → General → Danger Zone → Delete this repository**에서 대상 소유자·이름을 재확인하세요.

## 문제 해결

| 증상 | 확인과 대응 |
|---|---|
| Application `Terminating` | controller가 실행 중인지 확인. 이미 제거됐다면 전용 Azure 그룹 전체 삭제 경로 사용 |
| 리소스 그룹 삭제 거부 | 리소스 잠금·권한·정책 확인. 임의로 조직 보안 설정을 해제하지 않음 |
| 노드 그룹·LB·IP 잔존 | AKS 삭제 상태와 활동 로그 확인. 비용 위험을 알리고 해결 전에는 완료로 기록하지 않음 |
| kubeconfig 컨텍스트 없음 | AKS 생성 전에 중단했거나 이미 정리했는지 확인. 다른 컨텍스트 삭제로 대체하지 않음 |

[← 05 — Git 변경·자동 복구](05-gitops-update-self-heal.md) | [README로 돌아가기](../README.md)
