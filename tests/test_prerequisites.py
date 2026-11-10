import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
DOC = (ROOT / "docs" / "01-prerequisites.md").read_text(encoding="utf-8")
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

    def recovery_block(self, heading):
        section = DOC.partition(heading)[2]
        match = re.search(r"```bash\n(.*?)\n```", section, re.S)
        self.assertIsNotNone(match, "실행 가능한 복구 절차가 없습니다.")
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
        code = self.recovery_block("### 5.2.")
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
                'printf "RESULT:%s:%s:%s\\n" "$RESOURCE_GROUP" "$CLUSTER" "$GIT_BRANCH"',
                "existing-subscription\nrg-existing\naks-existing\nowner\nrepo\nfeature/keep\n",
                {"HOME": home},
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("RESULT:rg-existing:aks-existing:feature/keep", result.stdout)
            self.assertTrue((Path(home) / ".aks-argocd-ws-env").exists())

    def test_lost_kubeconfig_is_reacquired_before_context_selection(self):
        code = self.recovery_block("### 5.3.")
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


if __name__ == "__main__":
    unittest.main()
