# 01. 실습 준비

> 목표 시간 10분. 구독·권한·공급자·공개 Fork와 실습 변수를 준비합니다. 로컬 도구 설치·공급자 등록·권한 부여는 행사 전에 완료하며, 설치 시간은 90분 실습 목표에 포함하지 않습니다.

## 목표

올바른 Azure 구독, 필요한 권한·공급자 등록, Cloud Shell 및 로컬 도구, 자신의 공개 Fork와 기본 브랜치를 확인합니다.

## 실행 블록 읽는 법

👁️ **설명**

각 단계는 설명을 읽고 **🟢 실행**을 수행한 뒤 **📋 확인**에서 실제 결과를 비교합니다. 코드 블록 위의 실행 위치를 먼저 확인하세요.

| 표시·문법 | 읽는 방법 |
|---|---|
| Cloud Shell Bash / Windows PowerShell | 서로 다른 터미널입니다. 실행 위치가 다르면 같은 명령을 옮겨 실행하지 않습니다. |
| `set -euo pipefail` | Bash 오류·없는 변수 등을 확인하고 실패한 상태로 계속 진행하지 않기 위한 설정입니다. |
| `source "$HOME/.aks-argocd-ws-env"` | 저장한 기존 실습의 변수를 현재 Bash 세션으로 읽습니다. |
| `$RESOURCE_GROUP`·`$CLUSTER` | 앞서 정한 이름을 사용합니다. 문자열을 임의의 새 이름으로 바꾸지 않습니다. |
| Bash 줄 끝의 `\` | 다음 줄까지 하나의 명령입니다. 코드 블록 전체를 복사합니다. |
| 예상 출력·구조 예시 | 입력할 명령이 아니라 결과를 비교하기 위한 자료입니다. |

⚠️ **주의**

실행이 실패하면 다음 블록으로 넘어가지 않습니다. 셸이 종료됐거나 세션이 바뀌었다면 아래 5절에서 **기존 이름을 복원**합니다. 임시 세션의 환경 파일은 종료 전에 안전하게 보관하며 자격 증명은 공유하지 않습니다.

## 0. 참가자 PC의 로컬 도구 — 사전 설치

👁️ **설명**

Azure 리소스 작업은 **Cloud Shell Bash**, Argo CD UI 접속은 **참가자 PC의 Windows PowerShell**을 사용합니다. 두 환경은 로그인·환경변수·kubeconfig가 별개입니다. Cloud Shell의 환경 파일을 PC에서 source하거나 비밀번호·kubeconfig를 복사하지 않습니다.

- [Windows용 Azure CLI 설치](https://learn.microsoft.com/cli/azure/install-azure-cli-windows)
- [Windows용 kubectl 설치](https://kubernetes.io/docs/tasks/tools/install-kubectl-windows/)

설치 후 PC에서 새 PowerShell 창을 열고 확인합니다. macOS·Linux 사용자는 해당 OS의 공식 설치 안내를 따르며 아래 PowerShell 명령을 그대로 실행하지 않습니다.

🟢 **실행**

**실행 위치: 참가자 PC / Windows PowerShell**

```powershell
$ErrorActionPreference = 'Stop'
az version --output table
if ($LASTEXITCODE -ne 0) { throw '로컬 Azure CLI를 확인하세요.' }
kubectl version --client
if ($LASTEXITCODE -ne 0) { throw '로컬 kubectl을 확인하세요.' }
```

📋 **확인**

Azure CLI와 kubectl의 클라이언트 버전이 표시되고 오류 없이 종료돼야 합니다.

⚠️ **주의**

PC에서 공개 AKS API에 접근할 수 있어야 합니다. 회사 VPN·프록시·방화벽·도구 설치 정책을 미리 확인하세요. 로컬 준비가 안 되었다고 관리 화면을 공개 LoadBalancer로 바꾸거나 TLS를 끄지 않습니다.

## 1. Cloud Shell과 구독

👁️ **설명**

[Azure portal](https://portal.azure.com)의 상단 Cloud Shell 아이콘을 열고 **Bash**를 선택합니다. 로컬 PowerShell에서 아래 Bash 명령을 실행하지 마세요. 첫 실행의 스토리지·네트워크 설정은 조직 정책에 맞게 선택합니다. 임시 세션에서는 홈 파일이 다음 세션에 남지 않을 수 있습니다.

🟢 **실행**

**실행 위치: Cloud Shell Bash**

```bash
set -euo pipefail
az account list --query '[].{Name:name,Default:isDefault}' -o table
read -r -p "실습에 사용할 구독 이름: " SUBSCRIPTION_NAME
az account set --subscription "$SUBSCRIPTION_NAME"
az account show --query '{Name:name,State:state}' -o table
az version --query '"azure-cli"' -o tsv
kubectl version --client
```

📋 **확인**

선택한 실습 구독의 이름과 `Enabled` 상태, Azure CLI·kubectl 버전을 확인합니다.

⚠️ **주의**

명령 실패 시 다음 블록을 계속 실행하지 말고 원인을 해결하세요. `set -e`로 셸이 종료됐다면 Cloud Shell을 다시 열어 변수를 복원합니다. 토큰·자격 증명을 문서나 Git에 저장하지 않습니다.

### 필요한 권한

| 작업 | 필요한 권한·준비 |
|---|---|
| 새 리소스 그룹·AKS 생성과 삭제 | 해당 범위의 리소스 생성·삭제 권한. 실습 구독의 Contributor가 일반적인 예입니다 |
| 공급자 등록 | 구독 수준의 해당 공급자 register 권한. 없으면 관리자에게 사전 등록 요청 |
| extension 설치 | AKS 조회·변경 권한과 Kubernetes Extension Contributor 또는 해당 작업을 포함하는 상위 역할 |
| kubectl 접근 | AKS 사용자 자격 증명 취득과 앱·Application·namespace 관리 권한 |

Owner를 일괄 요구하지 않습니다. 조직의 정책·역할 범위에 따라 Contributor만으로 모든 작업이 허용되지 않을 수 있습니다. 이 실습은 새 학습용 클러스터의 기본 사용자 자격 증명을 사용하며, 운영용 Entra 인증·RBAC 설계를 대신하지 않습니다.

## 2. 공급자 등록

👁️ **설명**

AKS와 클러스터 extension에 필요한 공급자의 등록 상태를 먼저 조회합니다.

🟢 **실행**

**실행 위치: Cloud Shell Bash**

```bash
for provider in Microsoft.ContainerService Microsoft.Kubernetes Microsoft.KubernetesConfiguration; do
  az provider show --namespace "$provider" --query '{Provider:namespace,State:registrationState}' -o table
done
```

📋 **확인**

모두 `Registered`여야 합니다. 미등록일 때만 등록 권한을 가진 사용자가 다음을 실행합니다. 등록은 수 분 이상 걸릴 수 있습니다.

🟢 **실행**

**실행 위치: Cloud Shell Bash / 미등록인 경우에만**

```bash
for provider in Microsoft.ContainerService Microsoft.Kubernetes Microsoft.KubernetesConfiguration; do
  az provider register --namespace "$provider" --wait
  test "$(az provider show --namespace "$provider" --query registrationState -o tsv)" = Registered
done
```

📋 **확인**

등록 요청이 완료되고 세 공급자 모두 `Registered`인지 확인합니다.

## 3. 자신의 GitHub Fork 준비

👁️ **설명**

[원본 저장소](https://github.com/freeman9844/aks-argo-test-01)가 공개 상태인지 먼저 확인한 뒤 **Fork → Create fork**를 선택합니다. 원본은 2026-11-10 배포자 승인으로 공개 전환했습니다. 비공개 Fork에 토큰을 추가하는 방식은 이 실습에 포함하지 않습니다. 참고용 Application Routing 저장소를 Fork하는 것이 아닙니다.

⚠️ **주의**

**개인 GitHub 계정이 필요합니다.** Enterprise Managed User(EMU)는 외부 공개 저장소의 Fork·기여가 제한됩니다. 리허설에서도 `As an Enterprise Managed User, you cannot access this content` 오류로 공개 Fork 생성이 차단됐습니다. 조직 정책을 우회하지 말고, 참가 전에 공개 Fork를 허용하는 개인 계정을 준비하세요.

🟢 **실행**

**실행 위치: GitHub 웹**

1. 소유자가 자신의 계정이고 공개 저장소인지 확인합니다.
2. **Code** 화면의 브랜치 선택기에서 기본 브랜치 이름을 확인합니다. `main`이라고 가정하지 않습니다.
3. Fork에 `manifests/app/deployment.yaml`이 있는지 확인합니다.

📋 **확인**

자신의 공개 Fork URL·기본 브랜치·앱 파일을 확인했습니다. 이후 변경은 GitHub 웹 편집으로 동일 브랜치에 직접 커밋합니다. 터미널에 GitHub PAT·SSH 키를 설정하지 않습니다. private 저장소는 이 실습 범위 밖입니다.

## 4. 변수 설정과 저장

👁️ **설명**

새 실습에서 **한 번만** 실행합니다. 이미 실습을 시작했다면 아래의 복원 절차를 사용하세요.

🟢 **실행**

**실행 위치: Cloud Shell Bash / 새 실습에서 한 번만**

```bash
if [ -e "$HOME/.aks-argocd-ws-env" ]; then
  echo "기존 실습 환경 파일이 있습니다. 덮어쓰지 말고 복원 절차를 사용하세요." >&2
  exit 1
fi
read -r -p "Fork 소유자(GitHub 계정): " GITHUB_OWNER
read -r -p "Fork 저장소 이름: " GITHUB_REPO
read -r -p "확인한 기본 브랜치 이름: " GIT_BRANCH
for name in GITHUB_OWNER GITHUB_REPO GIT_BRANCH; do
  if [ -z "${!name}" ]; then
    printf '필수 입력이 비어 있습니다: %s\n' "$name" >&2
    exit 1
  fi
done
export GITHUB_OWNER GITHUB_REPO GIT_BRANCH
SUBSCRIPTION_ID="$(az account show --query id -o tsv)"
test -n "$SUBSCRIPTION_ID"
SUFFIX="$(date -u +%m%d%H%M%S)-$RANDOM"
export SUBSCRIPTION_ID SUFFIX
export RESOURCE_GROUP="rg-argocd-ws-$SUFFIX"
export CLUSTER="aks-argocd-ws-$SUFFIX"
export LOCATION=koreacentral
export EXTENSION_NAME=argocd APP_NAMESPACE=workshop APP_NAME=gitops-demo
export REPO_URL="https://github.com/$GITHUB_OWNER/$GITHUB_REPO.git"
umask 077
for name in SUBSCRIPTION_ID GITHUB_OWNER GITHUB_REPO GIT_BRANCH SUFFIX RESOURCE_GROUP CLUSTER LOCATION EXTENSION_NAME APP_NAMESPACE APP_NAME REPO_URL; do
  printf 'export %s=%q\n' "$name" "${!name}"
done > "$HOME/.aks-argocd-ws-env"
printf '실습 그룹: %s\n' "$RESOURCE_GROUP"
printf 'Fork: %s / branch: %s\n' "$REPO_URL" "$GIT_BRANCH"
```

📋 **확인**

브라우저의 Fork URL과 출력값을 비교합니다. 리소스 이름·공개 URL·선택한 구독의 식별자만 저장하며 자격 증명은 포함하지 않습니다.

## 5. 새 세션에서 재개하는 경우

### 5.1. 환경 파일이 있는 경우

👁️ **설명**

기존 환경 파일을 읽어 같은 구독·리소스 이름으로 돌아갑니다.

🟢 **실행**

**실행 위치: Cloud Shell Bash**

```bash
set -euo pipefail
source "$HOME/.aks-argocd-ws-env"
az account set --subscription "$SUBSCRIPTION_ID"
az account show --query '{Name:name,State:state}' -o table
printf '실습 그룹: %s / AKS: %s\n' "$RESOURCE_GROUP" "$CLUSTER"
```

📋 **확인**

출력된 구독·그룹·AKS가 원래 실습과 같은지 확인합니다. AKS가 이미 생성되어 있다면 5.3절로 kubeconfig도 복원합니다. 아직 AKS를 만들지 않았다면 02 모듈로 진행합니다.

### 5.2. 환경 파일이 없는 경우

⚠️ **주의**

**4절을 다시 실행하면 새 이름이 생성되므로 사용하지 않습니다.** portal에서 원래 구독·실습 그룹·AKS 이름을 확인한 후 다음을 실행합니다. 삭제 대상을 특정할 수 없다면 추측하지 말고 관리자에게 확인합니다.

🟢 **실행**

**실행 위치: Cloud Shell Bash / 기존 이름만 입력**

```bash
set -euo pipefail
if [ -e "$HOME/.aks-argocd-ws-env" ]; then
  echo "환경 파일이 있습니다. 5.1절에서 복원하세요." >&2
  exit 1
fi
read -r -p "기존 실습의 Azure 구독 이름: " SUBSCRIPTION_NAME
read -r -p "기존 실습 리소스 그룹 이름: " RESOURCE_GROUP
read -r -p "기존 실습 AKS 이름: " CLUSTER
read -r -p "기존 Fork 소유자: " GITHUB_OWNER
read -r -p "기존 Fork 저장소 이름: " GITHUB_REPO
read -r -p "기존 추적 브랜치 이름: " GIT_BRANCH
for name in SUBSCRIPTION_NAME RESOURCE_GROUP CLUSTER GITHUB_OWNER GITHUB_REPO GIT_BRANCH; do
  if [ -z "${!name}" ]; then
    printf '필수 입력이 비어 있습니다: %s\n' "$name" >&2
    exit 1
  fi
done
az account set --subscription "$SUBSCRIPTION_NAME"
SUBSCRIPTION_ID="$(az account show --query id -o tsv)"
test -n "$SUBSCRIPTION_ID"
LOCATION="$(az group show --name "$RESOURCE_GROUP" --query location -o tsv)"
test "$(az group show --name "$RESOURCE_GROUP" --query tags.workload -o tsv)" = aks-argocd-workshop
test "$(az group show --name "$RESOURCE_GROUP" --query tags.environment -o tsv)" = workshop
SUFFIX="${CLUSTER#aks-argocd-ws-}"
EXTENSION_NAME=argocd APP_NAMESPACE=workshop APP_NAME=gitops-demo
REPO_URL="https://github.com/$GITHUB_OWNER/$GITHUB_REPO.git"
umask 077
for name in SUBSCRIPTION_ID GITHUB_OWNER GITHUB_REPO GIT_BRANCH SUFFIX RESOURCE_GROUP CLUSTER LOCATION EXTENSION_NAME APP_NAMESPACE APP_NAME REPO_URL; do
  printf 'export %s=%q\n' "$name" "${!name}"
done > "$HOME/.aks-argocd-ws-env"
source "$HOME/.aks-argocd-ws-env"
printf '복원한 기존 그룹: %s / AKS: %s\n' "$RESOURCE_GROUP" "$CLUSTER"
```

📋 **확인**

이 블록은 리소스를 생성하지 않습니다. 기존 AKS가 정상이라면 5.3절을 실행하고 해당 모듈부터 재개합니다. AKS 생성에 실패했거나 아직 AKS가 없다면 이름을 새로 만들지 말고 02의 상태 확인 또는 06의 중도 종료 정리로 이동합니다.

### 5.3. 기존 AKS의 kubeconfig 복원

👁️ **설명**

환경 변수 복원만으로는 새 세션의 kubeconfig가 생기지 않습니다. **정상 생성된 기존 AKS**에서 다음을 실행합니다. 아직 클러스터가 없다면 실행하지 않습니다.

🟢 **실행**

**실행 위치: Cloud Shell Bash / 정상 생성된 기존 AKS에서만**

```bash
az aks get-credentials --resource-group "$RESOURCE_GROUP" --name "$CLUSTER" \
  --context "$CLUSTER"
kubectl config use-context "$CLUSTER"
NODE_RESOURCE_GROUP="$(az aks show --resource-group "$RESOURCE_GROUP" --name "$CLUSTER" \
  --query nodeResourceGroup -o tsv)"
test -n "$NODE_RESOURCE_GROUP"
export NODE_RESOURCE_GROUP
printf 'export NODE_RESOURCE_GROUP=%q\n' "$NODE_RESOURCE_GROUP" >> "$HOME/.aks-argocd-ws-env"
```

📋 **확인**

자격 증명 취득 후 올바른 컨텍스트로 전환됐고, 실제 관리 노드 그룹 이름이 환경 파일에 기록됐는지 확인합니다.

## 트러블슈팅

| 증상 | 대응 |
|---|---|
| Cloud Shell 시작 실패 | 조직의 스토리지·네트워크 정책 확인. Azure CLI 로그인 정보를 공유하지 않음 |
| `AuthorizationFailed` | 오류의 action·scope를 관리자에게 전달하고 필요한 범위의 권한 확인 |
| Fork에 앱 파일이 없음 | 참고 저장소가 아닌 이번 워크숍의 공개 저장소를 Fork했는지 확인 |
| 환경 파일이 없음 | 5절의 복구 수행. 새 리소스 생성으로 진행하지 않음 |

## 완료 체크

- [ ] 로컬 Azure CLI·kubectl 버전과 PC의 AKS API 접근 조건을 확인했습니다.
- [ ] 실습 구독·권한·공급자 등록 상태를 확인했습니다.
- [ ] 자신의 공개 Fork URL·기본 브랜치·앱 파일을 확인했습니다.
- [ ] 환경 파일에 실습 이름을 저장하고 기존 실행의 복구 방법을 이해했습니다.

## 다음 단계

[← README](../README.md) | [다음: 02. AKS 환경 준비 →](02-environment-setup.md)
