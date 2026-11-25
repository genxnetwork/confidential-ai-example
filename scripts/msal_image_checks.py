"""Check packaged MSAL sign-in and recovery with synthetic CIAM HTTP responses.

Build the image first. This opt-in check needs Docker but no live identity or
provider credentials. It uses the image's test probe, a disposable state volume,
and a callback published only on host loopback. All owned resources are removed.
"""

import argparse
import json
import shlex
import subprocess
import time
import uuid
from urllib.request import Request, urlopen


def check_image(image, docker):
    """Exercise separate container lifetimes without printing tokens or auth bodies."""
    prefix = "msal-check-" + uuid.uuid4().hex[:12]
    volume = prefix + "-state"
    containers = []

    def command(*args):
        return subprocess.check_output([*docker, *args], text=True, timeout=60).strip()

    command("volume", "create", volume)
    try:
        for phase, marker in (
            ("signin", "SIGN_IN_OK"), ("outage", "OUTAGE_PRESERVED_CACHE"),
            ("recover", "RESTART_SILENT_RENEWAL_OK"), ("cached", "RESTART_CACHE_HIT_OK"),
            ("logoff", "LOCAL_LOGOFF_OK"),
        ):
            name = prefix + "-" + phase
            containers.append(name)
            args = ["run", "-d", "--name", name, "-v", volume + ":/state",
                    "-e", "PYTHONPATH=/app/tests"]
            if phase == "signin":
                args.extend(["-p", "127.0.0.1::8765"])
            command(*args, image, "python3", "-m", "identity_image_probe", phase)
            if phase == "signin":
                deadline = time.monotonic() + 20
                while True:
                    logs = command("logs", name)
                    ready = next((line for line in logs.splitlines()
                                  if line.startswith("CALLBACK_READY ")), None)
                    if ready:
                        break
                    if time.monotonic() >= deadline or command("inspect", "-f", "{{.State.Running}}", name) != "true":
                        raise RuntimeError("Packaged callback did not become ready")
                    time.sleep(0.2)
                address = command("port", name, "8765/tcp")
                response = json.loads(ready.removeprefix("CALLBACK_READY "))
                # This is the synthetic fixture's response, never a live auth code.
                from urllib.parse import urlencode
                request = Request("http://" + address + "/", data=urlencode(response).encode(),
                                  headers={"Content-Type": "application/x-www-form-urlencoded"})
                with urlopen(request, timeout=10) as reply:
                    if reply.status != 200:
                        raise RuntimeError("Packaged callback rejected the fixture")
            status = command("wait", name)
            logs = command("logs", name)
            if status != "0" or marker not in logs:
                raise RuntimeError("Packaged identity phase failed: " + phase)
            print("PASS " + phase, flush=True)
        print("Automated image checks passed; live Entra browser sign-in remains separate.")
    finally:
        for name in containers:
            subprocess.run([*docker, "rm", "-f", name], stdout=subprocess.DEVNULL,
                           stderr=subprocess.DEVNULL, timeout=30)
        command("volume", "rm", volume)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--image", required=True)
    parser.add_argument("--docker", default="docker", help="Docker command, e.g. 'sudo -n docker'")
    args = parser.parse_args()
    check_image(args.image, shlex.split(args.docker))


if __name__ == "__main__":
    main()
