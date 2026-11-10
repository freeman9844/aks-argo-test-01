# 01 — 사전 준비

> **실행**: 직접 입력합니다. **개념**: 읽기만 합니다. **예상 출력**: 실제 결과와 비교하며 입력하지 않습니다.

예상 소요 시간: 10분. 공급자 등록·권한 부여는 행사 전에 완료하는 것을 권장합니다.

## 성공 조건

올바른 Azure 구독, 필요한 권한·공급자 등록, Cloud Shell 도구, 자신의 공개 Fork와 기본 브랜치를 확인합니다.

## 1. Cloud Shell과 구독

[Azure portal](https://portal.azure.com)의 상단 Cloud Shell 아이콘을 열고 **Bash**를 선택합니다. 로컬 PowerShell에서 아래 Bash 명령을 실행하지 마세요. 첫 실행의 스토리지·네트워크 설정은 조직 정책에 맞게 선택합니다. 임시 세션에서는 홈 파일이 다음 세션에 남지 않을 수 있습니다.

**실행**
```bash
set -euo pipefail
az account list --query '[].{Name:name,Default:isDefault}' -o table
read -r -p "실습에 사용할 구독 이름: " SUBSCRIPTION_NAME
az account set --subscription "$SUBSCRIPTION_NAME"
az account show --query '{Name:name,State:state}' -o table
az version --query '"azure-cli"' -o tsv
kubectl version --client
```

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

**실행**
```bash
for provider in Microsoft.ContainerService Microsoft.Kubernetes Microsoft.KubernetesConfiguration; do
  az provider show --namespace "$provider" --query '{Provider:namespace,State:registrationState}' -o table
done
```

모두 `Registered`여야 합니다. 미등록일 때만 등록 권한을 가진 사용자가 다음을 실행합니다. 등록은 수 분 이상 걸릴 수 있습니다.

**실행 — 미등록인 경우에만**
```bash
for provider in Microsoft.ContainerService Microsoft.Kubernetes Microsoft.KubernetesConfiguration; do
  az provider register --namespace "$provider" --wait
  test "$(az provider show --namespace "$provider" --query registrationState -o tsv)" = Registered
done
```

## 3. 자신의 GitHub Fork 준비

이 워크샵이 **게시된 GitHub 저장소 페이지**에서 **Fork → Create fork**를 선택합니다. 원본 URL은 배포자가 제공해야 하며, 참고용 Application Routing 저장소를 Fork하는 것이 아닙니다.

1. 소유자가 자신의 계정이고 공개 저장소인지 확인합니다.
2. **Code** 화면의 브랜치 선택기에서 기본 브랜치 이름을 확인합니다. `main`이라고 가정하지 않습니다.
3. Fork에 `manifests/app/deployment.yaml`이 있는지 확인합니다.

이후 변경은 GitHub 웹 편집으로 동일 브랜치에 직접 커밋합니다. 터미널에 GitHub PAT·SSH 키를 설정하지 않습니다. private 저장소는 이 실습 범위 밖입니다.

## 4. 변수 설정과 저장

새 실습에서 **한 번만** 실행합니다. 이미 실습을 시작했다면 아래의 복원 절차를 사용하세요.

**실행**
```bash
if [ -e "$HOME/.aks-argocd-ws-env" ]; then
  echo "기존 실습 환경 파일이 있습니다. 덮어쓰지 말고 복원 절차를 사용하세요." >&2
  exit 1
fi
read -r -p "Fork 소유자(GitHub 계정): " GITHUB_OWNER
read -r -p "Fork 저장소 이름: " GITHUB_REPO
read -r -p "확인한 기본 브랜치 이름: " GIT_BRANCH
test -n "$GITHUB_OWNER" && test -n "$GITHUB_REPO" && test -n "$GIT_BRANCH"
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

브라우저의 Fork URL과 출력값을 비교합니다. 리소스 이름·공개 URL·선택한 구독의 식별자만 저장하며 자격 증명은 포함하지 않습니다.

## 5. 새 세션에서 재개하는 경우

**실행**
```bash
set -euo pipefail
source "$HOME/.aks-argocd-ws-env"
az account set --subscription "$SUBSCRIPTION_ID"
az account show --query '{Name:name,State:state}' -o table
printf '실습 그룹: %s / AKS: %s\n' "$RESOURCE_GROUP" "$CLUSTER"
```

환경 파일이 사라졌다면 새 SUFFIX를 생성하지 마세요. portal의 실습 태그와 기존 AKS 이름으로 원래 값을 확인하고 4절의 변수를 **기존 이름으로** 재설정·저장합니다. 삭제 대상을 특정할 수 없다면 추측하지 말고 관리자에게 확인합니다.

## 문제 해결

| 증상 | 대응 |
|---|---|
| Cloud Shell 시작 실패 | 조직의 스토리지·네트워크 정책 확인. Azure CLI 로그인 정보를 공유하지 않음 |
| `AuthorizationFailed` | 오류의 action·scope를 관리자에게 전달하고 필요한 범위의 권한 확인 |
| Fork에 앱 파일이 없음 | 참고 저장소가 아닌 이번 워크샵의 공개 저장소를 Fork했는지 확인 |
| 환경 파일이 없음 | 5절의 복구 수행. 새 리소스 생성으로 진행하지 않음 |

[← README](../README.md) | [다음: 02 — 환경 준비](02-environment-setup.md)
