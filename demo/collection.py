"""Bounded HTTP retrieval. Confido itself performs no I/O."""
import base64
import hashlib
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
import json
import os
from pathlib import Path
import secrets
import time
from urllib.parse import urlsplit
import httpx
import confido_verifier
from .run import LiveRun

MAX_BODY = 4 * 1024 * 1024
MAX_METADATA = 64 * 1024
KDS = "https://kdsintf.amd.com/vcek/v1"
_cache = {}


def load_policy(path):
    path = Path(path)
    with path.open("rb") as source:
        raw = source.read(MAX_METADATA + 1)
    if len(raw) > MAX_METADATA: raise ValueError("Application policy exceeds limit")
    app = json.loads(raw)
    if app.get("schema_version") != 2:
        raise ValueError("Application policy version 2 required")
    origin = urlsplit(app["origin"])
    if origin.scheme != "https" or not origin.hostname or origin.username or origin.password or origin.path not in ("", "/") or origin.query or origin.fragment:
        raise ValueError("Expected bare HTTPS origin")
    policy_path = (path.parent / app["verifier_policy"]).resolve()
    if not policy_path.is_relative_to(path.parent.resolve()):
        raise ValueError("Verifier policy must be local to the policy directory")
    with policy_path.open("rb") as source:
        policy = source.read(MAX_METADATA + 1)
    if len(policy) > MAX_METADATA:
        raise ValueError("Policy exceeds limit")
    app = dict(app, verifier_bytes=policy, verifier=json.loads(policy))
    return app


def fetch(url, *, method="GET", body=None, limit=MAX_BODY, untrusted=False, token=None, timeout=30):
    headers = {"Accept": "application/vnd.github.raw+json" if url.startswith("https://api.github.com/") else "application/json", "User-Agent": "confido-caller/0.4.0"}
    if token:
        headers["Authorization"] = "Bearer " + token
        headers["Accept"] = "application/vnd.github.raw+json"
    deadline = time.monotonic() + timeout
    # New client per operation: no bootstrap cookies or credentials leak forward.
    with httpx.Client(verify=not untrusted, follow_redirects=False, trust_env=False, timeout=timeout) as client:
        with client.stream(method, url, json=body, headers=headers) as response:
            if response.is_redirect:
                raise ValueError("HTTP redirect rejected")
            response.raise_for_status()
            data = bytearray()
            for chunk in response.iter_bytes():
                if time.monotonic() >= deadline:
                    raise ValueError("HTTP retrieval deadline expired")
                if len(data) + len(chunk) > limit:
                    raise ValueError("HTTP body exceeds limit")
                data.extend(chunk)
            if time.monotonic() >= deadline:
                raise ValueError("HTTP retrieval deadline expired")
            return bytes(data), dict(response.headers)


def kds(url):
    now = time.monotonic()
    if url in _cache and _cache[url][0] > now:
        return _cache[url][1]
    deadline = now + 60
    for attempt in range(3):
        if time.monotonic() >= deadline: raise ValueError("KDS deadline expired")
        try:
            data, _ = fetch(url, limit=MAX_METADATA, timeout=min(15, max(0.01, deadline - time.monotonic())))
            if len(_cache) >= 128:
                _cache.pop(next(iter(_cache)))
            _cache[url] = (time.monotonic() + 3600, data)
            return data
        except httpx.HTTPStatusError as error:
            if error.response.status_code not in (429, 500, 502, 503, 504) or attempt == 2:
                raise
            retry = error.response.headers.get("retry-after", str(2**attempt))
            try:
                delay = float(retry)
            except ValueError:
                delay = (parsedate_to_datetime(retry) - datetime.now(timezone.utc)).total_seconds()
            delay = max(0, delay)
            if not delay < deadline - time.monotonic():
                raise ValueError("KDS retry exceeds deadline") from error
            time.sleep(delay)
    raise RuntimeError("KDS unavailable")


def collect_and_verify(app, *, progress=None):
    emit = progress or (lambda message: None)
    nonce = secrets.token_bytes(32)
    started = time.monotonic()
    deadline = started + 120
    nonce_base64 = base64.b64encode(nonce).decode()
    emit('Fresh 32-byte challenge generated')
    emit('POST ' + app['origin'].rstrip('/') + '/tee-report: sending nonce in JSON body (base64: ' + nonce_base64 + ')')
    report, headers = fetch(app["origin"].rstrip("/") + "/tee-report", method="POST", body={"nonce": nonce_base64}, untrusted=app.get("allow_untrusted_bootstrap", False))
    if "no-store" not in [x.strip().lower() for x in headers.get("cache-control", "").split(",")]:
        raise ValueError("Report must declare Cache-Control: no-store")
    emit(f'Report received: {len(report)} bytes; awaiting local verification')
    emit('Inspecting untrusted SNP selectors for AMD endorsement retrieval')
    req = confido_verifier.inspect_requirements(report)
    chip = req["chip_id"]
    product = req["product"] or app["verifier"]["platform"]["product"]
    if product not in ("Milan", "Genoa") or product != app["verifier"]["platform"]["product"] or len(chip) != 128 or any(c not in "0123456789abcdef" for c in chip):
        raise ValueError("Unsupported KDS selector")
    tcb = req["tcb"]
    if len(tcb) != 4 or any(not isinstance(v, int) or not 0 <= v <= 255 for v in tcb):
        raise ValueError("Invalid KDS TCB selector")
    product_kds = KDS + "/" + product
    emit('AMD product=' + product + '; requested TCB=' + json.dumps(tcb))
    emit('Retrieving AMD ASK/ARK chain from ' + product_kds + '/cert_chain')
    chain = kds(product_kds + "/cert_chain")
    emit(f'AMD chain available: {len(chain)} bytes; retrieving chip-specific VCEK')
    vcek = kds(product_kds + "/" + chip + "?" + "&".join(f"{name}={value:02}" for name, value in zip(("blSPL", "teeSPL", "snpSPL", "ucodeSPL"), tcb)))
    ref = app["verifier"]["reference"]
    # Policy path validation is repeated before using it as a network locator.
    import re
    if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", ref["repository"]) or not re.fullmatch(r"[a-f0-9]{40}", ref["commit"]) or any(not re.fullmatch(r"[A-Za-z0-9_.-]+", s) or s in (".", "..") for s in ref["path"].split("/")):
        raise ValueError("Invalid immutable reference locator")
    url = f'https://api.github.com/repos/{ref["repository"]}/contents/{ref["path"]}?ref={ref["commit"]}'
    emit("Retrieving pinned reference: " + url)
    reference, _ = fetch(url, token=os.environ.get("CONFIDO_TRS_TOKEN"))
    collection_finished = time.monotonic()
    if collection_finished >= deadline:
        raise ValueError("Challenge deadline expired")
    at = int(time.time())
    emit("Inputs collected; starting local evidence verification")
    verify_started = time.monotonic()
    if verify_started >= deadline:
        raise ValueError("Challenge deadline expired before verification")
    result = confido_verifier.verify(report, chain, vcek, reference, app["verifier_bytes"], nonce, at)
    verify_finished = time.monotonic()
    if verify_finished >= deadline:
        raise ValueError("Challenge deadline expired during verification")
    timings = {"collection_ms": (collection_finished - started) * 1000,
               "verification_ms": (verify_finished - verify_started) * 1000}
    emit(f'Inputs collected in {timings["collection_ms"]:.1f} ms; local verification completed in {timings["verification_ms"]:.2f} ms')
    archive = {"schema_version": 2, "mode": "live_collection", "origin": app["origin"],
               "inputs": {name: base64.b64encode(data).decode() for name, data in [("report", report), ("amd_chain", chain), ("vcek", vcek), ("reference", reference)]},
               "context": {"expected_nonce_base64": base64.b64encode(nonce).decode(), "evaluation_unix_seconds": at}, "verification": result}
    return LiveRun(result, archive, deadline, hashlib.sha256(app["verifier_bytes"]).hexdigest(), timings)
