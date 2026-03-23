import os
import stat
import subprocess
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
ROCKIT_SCRIPT = REPO_ROOT / "rockit.sh"


class RockitCliTests(unittest.TestCase):
    def test_deploy_pushes_generated_folder_to_quest(self):
        with tempfile.TemporaryDirectory() as workspace:
            workspace_path = Path(workspace)
            bin_dir = workspace_path / "bin"
            bin_dir.mkdir()

            output_dir = workspace_path / "Fixture Song Ragnarock"
            output_dir.mkdir()
            zip_path = workspace_path / "fixture.zip"
            zip_path.write_bytes(b"fixture")
            adb_log = workspace_path / "adb.log"

            self._write_executable(
                bin_dir / "uv",
                f"""#!/bin/bash
printf '%s\n' 'Starting converter'
printf '%s\n' 'Output folder: {output_dir}'
""",
            )
            self._write_executable(
                bin_dir / "adb",
                """#!/bin/bash
{
  printf '%s' "$1"
  shift
  for arg in "$@"; do
    printf '|%s' "$arg"
  done
  printf '\n'
} >> "$ADB_LOG"

case "$1" in
  get-state)
    printf 'device\n'
    exit 0
    ;;
  shell)
    exit 0
    ;;
  push)
    exit 0
    ;;
esac

exit 0
""",
            )

            result = subprocess.run(
                ["bash", str(ROCKIT_SCRIPT), "--deploy", str(zip_path)],
                cwd=REPO_ROOT,
                env=self._build_env(bin_dir, adb_log=adb_log),
                capture_output=True,
                text=True,
            )

            self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)
            self.assertIn("Quest deployment completed successfully!", result.stdout)
            self.assertEqual(
                adb_log.read_text(encoding="utf-8").splitlines(),
                [
                    "get-state",
                    "shell|mkdir -p '/sdcard/Android/data/com.wanadev.ragnarockquest/files/CustomSongs'",
                    f"shell|rm -rf '/sdcard/Android/data/com.wanadev.ragnarockquest/files/CustomSongs/{output_dir.name}'",
                    f"push|{output_dir}|/sdcard/Android/data/com.wanadev.ragnarockquest/files/CustomSongs/",
                ],
            )

    def test_deploy_requires_adb(self):
        with tempfile.TemporaryDirectory() as workspace:
            workspace_path = Path(workspace)
            bin_dir = workspace_path / "bin"
            bin_dir.mkdir()

            zip_path = workspace_path / "fixture.zip"
            zip_path.write_bytes(b"fixture")

            self._write_executable(
                bin_dir / "uv",
                """#!/bin/bash
printf '%s\n' 'Output folder: /tmp/should-not-matter'
""",
            )

            result = subprocess.run(
                ["bash", str(ROCKIT_SCRIPT), "--deploy", str(zip_path)],
                cwd=REPO_ROOT,
                env=self._build_env(bin_dir),
                capture_output=True,
                text=True,
            )

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("adb is required for --deploy", result.stdout)
            self.assertNotIn("Starting converter", result.stdout)

    def test_default_conversion_does_not_require_adb(self):
        with tempfile.TemporaryDirectory() as workspace:
            workspace_path = Path(workspace)
            bin_dir = workspace_path / "bin"
            bin_dir.mkdir()

            zip_path = workspace_path / "fixture.zip"
            zip_path.write_bytes(b"fixture")

            self._write_executable(
                bin_dir / "uv",
                """#!/bin/bash
printf '%s\n' 'Output folder: /tmp/no-deploy'
""",
            )

            result = subprocess.run(
                ["bash", str(ROCKIT_SCRIPT), str(zip_path)],
                cwd=REPO_ROOT,
                env=self._build_env(bin_dir),
                capture_output=True,
                text=True,
            )

            self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)
            self.assertNotIn("adb is required", result.stdout)

    def _build_env(self, bin_dir: Path, adb_log: Path | None = None) -> dict[str, str]:
        env = os.environ.copy()
        env["PATH"] = f"{bin_dir}:{env['PATH']}"
        if adb_log is not None:
            env["ADB_LOG"] = str(adb_log)
        return env

    def _write_executable(self, path: Path, content: str) -> None:
        path.write_text(content, encoding="utf-8")
        path.chmod(path.stat().st_mode | stat.S_IXUSR)


if __name__ == "__main__":
    unittest.main()
