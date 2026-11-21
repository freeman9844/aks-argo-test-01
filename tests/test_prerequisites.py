import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
DOC = (ROOT / "docs" / "01-prerequisites.md").read_text(encoding="utf-8")
SETUP = (ROOT / "docs" / "02-environment-setup.md").read_text(encoding="utf-8")
CLEANUP = (ROOT / "docs" / "06-cleanup.md").read_text(encoding="utf-8")
git = shutil.which("git")
git_bash = Path(git).parent.parent / "bin" / "bash.exe" if git else None
BASH = os.environ.get("BASH_PATH") or (
    str(git_bash) if git_bash and git_bash.exists() else shutil.which("bash")
)


class PrerequisiteCommandsTests(unittest.TestCase):
    def run_bash(self, code, input_text="", env=None):
        self.assertIsNotNone(BASH, "Bash가 필요합니다. BASH_PATH를 지정하세요.")
        result = subprocess.run(
            [BASH, "-c", "set -euo pipefail\n" + code],
            input=input_text.encode("utf-8"), capture_output=True,
            env=dict(os.environ, **(env or {})),
        )
        result.stdout = result.stdout.decode("utf-8")
        result.stderr = result.stderr.decode("utf-8")
        return result

    def bash_block(self, heading, doc=DOC):
        section = doc.partition(heading)[2]
        match = re.search(r"```bash\n(.*?)\n```", section, re.S)
        self.assertIsNotNone(match, f"실행 가능한 Bash 블록이 없습니다: {heading}")
        return match[1]

    def test_empty_fork_fields_stop_before_resource_preparation(self):
        start = DOC.index('read -r -p "Fork 소유자')
        end = DOC.index('SUBSCRIPTION_ID="$(az account show', start)
        code = DOC[start:end] + '\nprintf "ACCEPTED\\n"'
        for inputs in ("\nrepo\nmain\n", "owner\n\nmain\n", "owner\nrepo\n\n"):
            with self.subTest(inputs=inputs):
                result = self.run_bash(code, inputs)
                self.assertNotEqual(result.returncode, 0)
                self.assertNotIn("ACCEPTED", result.stdout)
                self.assertTrue(result.stderr)
        result = self.run_bash(code, "owner\nrepo\nmain\n")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("ACCEPTED", result.stdout)

    def test_home_loss_restores_existing_names_without_creating_resources(self):
        code = self.bash_block("### 5.2.")
        azure = r'''
az() {
  case "$1 $2" in
    "account set") test "$4" = "existing-subscription" ;;
    "account show") printf 'subscription-id\n' ;;
    "group show")
      test "$4" = "rg-existing"
      case "$6" in
        location) printf 'koreacentral\n' ;;
        tags.workload) printf 'aks-argocd-workshop\n' ;;
        tags.environment) printf 'workshop\n' ;;
        *) return 91 ;;
      esac ;;
    *) echo "허용되지 않은 Azure 작업: $*" >&2; return 92 ;;
  esac
}
'''
        with tempfile.TemporaryDirectory() as home:
            result = self.run_bash(
                azure + code + '\nsource "$HOME/.aks-argocd-ws-env"\n'
                'printf "RESULT:%s:%s:%s:%s\\n" "$RESOURCE_GROUP" "$CLUSTER" '
                '"$GIT_BRANCH" "$AKS_CREATION_ATTEMPTED"',
                "existing-subscription\nrg-existing\naks-existing\nowner\nrepo\nfeature/keep\n",
                {"HOME": home},
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("RESULT:rg-existing:aks-existing:feature/keep:unknown", result.stdout)
            self.assertTrue((Path(home) / ".aks-argocd-ws-env").exists())

    def test_lost_kubeconfig_is_reacquired_before_context_selection(self):
        code = self.bash_block("### 5.3.")
        clients = r'''
az() {
  case "$1 $2" in
    "aks get-credentials")
      test "$4" = "rg-existing"
      test "$6" = "aks-existing"
      printf 'aks-existing' > "$HOME/recovered-context" ;;
    "aks show") printf 'MC_existing\n' ;;
    *) return 93 ;;
  esac
}
kubectl() {
  test "$1 $2" = "config use-context"
  test "$3" = "aks-existing"
  test "$(cat "$HOME/recovered-context")" = "$3"
}
'''
        with tempfile.TemporaryDirectory() as home:
            result = self.run_bash(
                clients + code,
                env={"HOME": home, "RESOURCE_GROUP": "rg-existing", "CLUSTER": "aks-existing"},
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual((Path(home) / "recovered-context").read_text(), "aks-existing")

    def test_namespace_absence_does_not_block_extension_cleanup(self):
        code = self.bash_block("### 3.3.", CLEANUP)
        clients = r'''
kubectl() {
  test "$1 $2 $3" = "delete namespace workshop" || return 90
  if [ "$NAMESPACE_STATE" = forbidden ]; then
    echo 'Forbidden' >&2
    return 1
  fi
  for arg do
    if [ "$arg" = --ignore-not-found=true ]; then return 0; fi
  done
  echo 'Namespace not found' >&2
  return 1
}
az() {
  test "$*" = "k8s-extension delete --resource-group rg-lab --cluster-name aks-lab --cluster-type managedClusters --name argocd --yes" || return 91
  echo EXTENSION_REMOVED
}
'''
        env = {
            "APP_NAMESPACE": "workshop", "RESOURCE_GROUP": "rg-lab",
            "CLUSTER": "aks-lab", "EXTENSION_NAME": "argocd",
        }
        result = self.run_bash(clients + code, env={**env, "NAMESPACE_STATE": "missing"})
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("EXTENSION_REMOVED", result.stdout)
        result = self.run_bash(clients + code, env={**env, "NAMESPACE_STATE": "forbidden"})
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Forbidden", result.stderr)
        self.assertNotIn("EXTENSION_REMOVED", result.stdout)

    def test_group_cleanup_only_succeeds_with_node_group_absence_or_known_no_attempt(self):
        check = self.bash_block("## 2.", CLEANUP)
        delete = self.bash_block("## 4.", CLEANUP)
        azure = r'''
unset NODE_RESOURCE_GROUP AKS_CREATION_ATTEMPTED
RESOURCE_GROUP=rg-lab CLUSTER=aks-lab
if [ -n "$ATTEMPT" ]; then AKS_CREATION_ATTEMPTED="$ATTEMPT"; fi
az() {
  case "$*" in
    "resource list -g rg-lab --resource-type Microsoft.ContainerService/managedClusters "*)
      if [ "$HAS_CLUSTER" = yes ]; then echo '/resource/aks-lab'; fi ;;
    "aks show -g rg-lab -n aks-lab --query nodeResourceGroup -o tsv")
      echo MC_lab ;;
    "group delete --name rg-lab --yes --no-wait") echo WORKSHOP_DELETE ;;
    "group exists --name rg-lab") echo false ;;
    "group exists --name MC_lab") echo false; echo NODE_GROUP_CHECKED >&2 ;;
    *) echo "unexpected Azure command: $*" >&2; return 90 ;;
  esac
}
'''
        with tempfile.TemporaryDirectory() as home:
            for attempt, has_cluster, status in [
                ("false", "no", 0), ("true", "no", 1), ("", "no", 1), ("false", "yes", 0),
            ]:
                with self.subTest(attempt=attempt, has_cluster=has_cluster):
                    result = self.run_bash(azure + check + "\n" + delete, env={
                        "HOME": home, "ATTEMPT": attempt, "HAS_CLUSTER": has_cluster,
                    })
                    self.assertEqual(result.returncode, status, result.stderr)
                    self.assertIn("WORKSHOP_DELETE", result.stdout)
                    self.assertEqual("NODE_GROUP_CHECKED" in result.stderr, has_cluster == "yes")

    def test_aks_create_records_attempt_even_when_creation_fails(self):
        initialize = self.bash_block("## 4.", DOC)
        create = self.bash_block("## 2.", SETUP)
        azure = r'''
az() {
  case "$1 $2" in
    "account show") echo subscription-id ;;
    "aks create") echo CREATE_FAILED >&2; return 33 ;;
    *) return 90 ;;
  esac
}
'''
        with tempfile.TemporaryDirectory() as home:
            env = {"HOME": home}
            verify = '\nsource "$HOME/.aks-argocd-ws-env"\nprintf "%s" "${AKS_CREATION_ATTEMPTED:-unknown}"'
            result = self.run_bash(azure + initialize + verify, "owner\nrepo\nmain\n", env)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue(result.stdout.endswith("false"), result.stdout)
            result = self.run_bash(azure + '\nsource "$HOME/.aks-argocd-ws-env"\n' + create, env=env)
            self.assertEqual(result.returncode, 33, result.stderr)
            self.assertIn("CREATE_FAILED", result.stderr)
            self.assertEqual(self.run_bash(verify, env=env).stdout, "true")

    def test_missing_cloud_shell_context_does_not_block_local_cleanup(self):
        code = self.bash_block("이 실습의 `$CLUSTER` 컨텍스트만", CLEANUP)
        kubernetes = r'''
CLUSTER=aks-lab
kubectl() {
  case "$*" in
    "config get-contexts -o name") echo aks-other ;;
    "config delete-context aks-lab") echo 'Context not found' >&2; return 1 ;;
    *) return 90 ;;
  esac
}
'''
        result = self.run_bash(kubernetes + code)
        self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == "__main__":
    unittest.main()
