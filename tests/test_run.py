"""Exercise user launchers against a Docker CLI stub, without a Docker daemon."""

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from contextlib import contextmanager
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STUB = '''import json, os, sys, time
from pathlib import Path
args = sys.argv[1:]
root = Path(os.environ["FAKE_DOCKER_DIR"])
with (root / "calls.jsonl").open("a") as stream:
    stream.write(json.dumps(args) + "\\n")
if args[0] == "info":
    print(os.environ.get("FAKE_DOCKER_ENGINE", "linux"))
elif args[:2] == ["image", "inspect"]:
    sys.exit(0 if (root / "image").exists() else 1)
elif args[0] == "pull":
    (root / "image").touch()
elif args[0] == "run":
    if os.environ.get("FAKE_BROWSER_WAIT"):
        deadline = time.monotonic() + 5
        while not (root / "opened.json").exists() and time.monotonic() < deadline:
            time.sleep(0.01)
    sys.exit(int(os.environ.get("FAKE_DOCKER_STATUS", "0")))
'''


class LauncherTests(unittest.TestCase):
    def launchers(self):
        if os.name == "nt":
            return [("Windows", ["cmd.exe", "/d", "/c", str(ROOT / "run.cmd")])]
        result = [("shell", ["sh", str(ROOT / "run")])]
        if powershell := shutil.which("pwsh"):
            result.append(("PowerShell", [powershell, "-NoLogo", "-NoProfile", "-File", str(ROOT / "run.ps1")]))
        return result

    @contextmanager
    def docker(self, launcher):
        with tempfile.TemporaryDirectory(prefix="demo launcher ") as directory:
            root = Path(directory)
            stub = root / "stub.py"
            stub.write_text(STUB)
            executable = root / ("docker.cmd" if os.name == "nt" else "docker")
            executable.write_text(
                f'@"{sys.executable}" "{stub}" %*\n' if os.name == "nt"
                else f'#!{sys.executable}\n' + STUB
            )
            executable.chmod(0o700)
            policies = root / "policies with spaces"
            policies.mkdir()
            env = dict(os.environ, PATH=str(root) + os.pathsep + os.environ["PATH"],
                       FAKE_DOCKER_DIR=str(root), GENXT_DEMO_IMAGE="example/demo:test",
                       GENXT_DEMO_BROWSER="manual",
                       GENXT_DEMO_STATE_VOLUME="demo-test-state",
                       XDG_CACHE_HOME=str(root / "cache"), XDG_CONFIG_HOME=str(root / "config"),
                       XDG_DATA_HOME=str(root / "data"))
            env.pop("GENXT_DEMO_POLICY_DIR", None)
            def invoke(*args, **extra):
                return subprocess.run(launcher + list(args), input="", text=True,
                                      capture_output=True, env=dict(env, **extra))
            def calls():
                return [json.loads(row) for row in (root / "calls.jsonl").read_text().splitlines()]
            yield invoke, calls, policies

    @unittest.skipIf(os.name == "nt", "Exercises the Unix host opener")
    def test_mac_opens_only_the_local_handoff_and_preserves_docker_status(self):
        launcher = ["sh", str(ROOT / "run")]
        with self.docker(launcher) as (invoke, calls, policies):
            root = policies.parent
            for name, content in (
                ("uname", "#!/bin/sh\nprintf 'Darwin\\n'\n"),
                ("curl", "#!/bin/sh\nprintf 'synthetic-flow-id'\n"),
                ("open", f'#!{sys.executable}\nimport json, sys\n'
                         f'from pathlib import Path\nPath({str(root / "opened.json")!r}).write_text(json.dumps(sys.argv[1:]))\n'),
            ):
                path = root / name
                path.write_text(content)
                path.chmod(0o700)
            result = invoke(GENXT_DEMO_BROWSER="auto", FAKE_BROWSER_WAIT="1", FAKE_DOCKER_STATUS="7")
            self.assertEqual(result.returncode, 7, result.stderr)
            run = next(c for c in calls() if c[0] == "run")
            handoff = next(arg.split("=", 1)[1] for arg in run if arg.startswith("GENXT_DEMO_BROWSER_HANDOFF="))
            self.assertEqual(json.loads((root / "opened.json").read_text()),
                             ["http://localhost:8765/browser/" + handoff])

    def test_manual_browser_mode_and_invalid_selection(self):
        for name, launcher in self.launchers():
            with self.subTest(launcher=name), self.docker(launcher) as (invoke, calls, _):
                self.assertEqual(invoke(GENXT_DEMO_BROWSER="manual").returncode, 0)
                run = next(c for c in calls() if c[0] == "run")
                self.assertFalse(any(arg.startswith("GENXT_DEMO_BROWSER_HANDOFF=") for arg in run))
                self.assertNotEqual(invoke(GENXT_DEMO_BROWSER="invalid").returncode, 0)
                self.assertEqual(sum(c[0] == "run" for c in calls()), 1)

    def test_first_launch_pulls_once_and_reuses_image_and_state(self):
        for name, launcher in self.launchers():
            with self.subTest(launcher=name), self.docker(launcher) as (invoke, calls, _):
                for _ in range(2):
                    result = invoke()
                    self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(sum(c[0] == "pull" for c in calls()), 1)
                runs = [c for c in calls() if c[0] == "run"]
                self.assertEqual(len(runs), 2)
                for args in runs:
                    self.assertIn("127.0.0.1:8765:8765", args)
                    self.assertIn("type=volume,source=demo-test-state,target=/state", args)
                    self.assertEqual(args[args.index("--platform") + 1], "linux/amd64")

    def test_update_pulls_image_and_shows_info_without_sign_in(self):
        for name, launcher in self.launchers():
            with self.subTest(launcher=name), self.docker(launcher) as (invoke, calls, _):
                result = invoke("--update")
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertTrue(any(c[0] == "pull" for c in calls()))
                run = next(c for c in calls() if c[0] == "run")
                self.assertEqual(run[-3:], ["python3", "-m", "demo.runtime"])
                self.assertNotIn("--publish", run)

    def test_windows_container_engine_is_rejected_before_start(self):
        for name, launcher in self.launchers():
            with self.subTest(launcher=name), self.docker(launcher) as (invoke, calls, _):
                self.assertNotEqual(invoke(FAKE_DOCKER_ENGINE="windows").returncode, 0)
                self.assertEqual([c[0] for c in calls()], ["info"])

    def test_policy_path_with_spaces_and_container_failure_are_preserved(self):
        for name, launcher in self.launchers():
            with self.subTest(launcher=name), self.docker(launcher) as (invoke, calls, policies):
                result = invoke(GENXT_DEMO_POLICY_DIR=str(policies), FAKE_DOCKER_STATUS="7")
                self.assertEqual(result.returncode, 7, result.stderr)
                run = next(c for c in calls() if c[0] == "run")
                self.assertIn(f"type=bind,source={policies},target=/policies,readonly", run)


if __name__ == "__main__":
    unittest.main()
