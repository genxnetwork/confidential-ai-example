"""Presentation of completed Rust checks; no verification is performed here."""

import hashlib
import json
import os
import sys
from datetime import datetime, timezone

_COLOR = {
    "heading": "\033[36m",
    "ok": "\033[32m",
    "warn": "\033[33m",
    "error": "\033[31m",
    "reference": "\033[34m",
    "muted": "\033[38;5;240m",
}
_IMA_FIELDS = (
    "name",
    "PCR",
    "template_hash",
    "ima_template",
    "filedata_alg",
    "filedata_hash",
    "filename_hint",
)
_LABELS = {
    "endorsements": "AMD certificate chain",
    "snp_signature": "SNP report signature",
    "vcek_correspondence": "VCEK correspondence and TCB consistency",
    "platform_policy": "Platform policy",
    "hcl_key": "HCL → AK",
    "quote_signature": "Quote signature",
    "quote_binding": "Quote nonce/certificate/IMA binding",
    "quoted_pcrs": "Signed PCR mapping",
    "reference": "Pinned reference",
    "ima_reference": "IMA reference",
    "boot_aggregate": "Boot aggregate",
    "pcr10": "PCR 10",
}


def color(text, kind):
    mode = os.environ.get("CONFIDO_COLOR", "auto").lower()
    if mode == "never" or (
        mode != "always" and (not sys.stdout.isatty() or "NO_COLOR" in os.environ)
    ):
        return str(text)
    return f"{_COLOR[kind]}{text}\033[0m"


def format_utc(value):
    moment = (
        value
        if isinstance(value, datetime)
        else datetime.fromtimestamp(value, timezone.utc)
    )
    return moment.astimezone(timezone.utc).strftime("%d.%m.%Y %H:%M:%S UTC")


def _safe(value):
    return "".join(ch if ch.isprintable() else f"\\x{ord(ch):02x}" for ch in str(value))


def _short(value, length=20):
    value = str(value)
    return value if len(value) <= length else value[:length] + "…"


def _styled(message):
    message = _safe(message)
    label = message.lstrip()
    indent = message[: len(message) - len(label)]
    for word, kind in [("PASSED", "ok"), ("FAILED", "error")]:
        if label.startswith(word + " "):
            return indent + color(word, kind) + label[len(word) :]
    if label.startswith("module "):
        number, _, detail = label[7:].partition(" ")
        body, separator, verdict = detail.rpartition("  ")
        if separator and verdict in ("MATCH", "MISMATCH", "UNVERIFIED"):
            kind = {"MATCH": "ok", "MISMATCH": "error", "UNVERIFIED": "warn"}[verdict]
            detail = body + separator + color(verdict, kind)
        return "          " + color(number, "muted") + "  " + detail
    if label.startswith(
        ("VERIFICATION RESULTS", "IMA entries", "Received IMA", "Legacy result")
    ):
        return color(message, "heading")
    return message


def line(message):
    """A completed-check row has no fabricated execution timestamp."""
    print(_styled(message), flush=True)


def log(message):
    """Timestamp an actual caller event as it occurs."""
    stamp = datetime.now(timezone.utc).strftime("%H:%M:%S")
    print(f"{color('[' + stamp + ']', 'muted')} {_styled(message)}", flush=True)


def _json(raw):
    if isinstance(raw, dict):
        return raw
    try:
        value = json.loads(raw)
        return value if isinstance(value, dict) else {}
    except (TypeError, ValueError):
        return {}


def _fingerprint(values):
    raw = bytes(values)
    return f"{len(raw):,} bytes · SHA-256 {_short(hashlib.sha256(raw).hexdigest())}"


def _module_verdicts(result, reference, entries):
    """Use the verifier's reference stage before comparing display-only rows."""
    checks = {check["stage"]: check for check in result["checks"]}
    if checks.get("reference", {}).get("status") != "passed":
        return None
    comparison = checks.get("ima_reference")
    if comparison is None:
        return None
    if comparison["status"] == "passed":
        return ["MATCH"] * len(entries)
    if comparison.get("reason") != "measurement_mismatch":
        return None
    trusted = _json(reference).get("ima_measurements")
    if not isinstance(trusted, list):
        return None
    return [
        "MATCH"
        if index < len(trusted)
        and isinstance(entry, dict)
        and isinstance(trusted[index], dict)
        and all(entry.get(field) == trusted[index].get(field) for field in _IMA_FIELDS)
        else "MISMATCH"
        for index, entry in enumerate(entries)
    ]


def describe_modules(report, emit=line, *, verdicts=None):
    evidence = report.get("evidence", {})
    entries = evidence.get("ima_measurements", []) if isinstance(evidence, dict) else []
    if not isinstance(entries, list):
        emit("Received IMA list is malformed")
        return
    boots = sum(
        isinstance(e, dict)
        and e.get("filename_hint", e.get("name")) == "boot_aggregate"
        for e in entries
    )
    label = (
        "Received IMA entries (unverified)"
        if verdicts is None
        else "IMA entries for reference comparison"
    )
    emit(
        f"{label}: {len(entries)} — {boots} boot aggregate, {len(entries) - boots} modules; collector order"
    )
    width = max(3, len(str(max(0, len(entries) - 1))))
    for index, entry in enumerate(entries):
        verdict = verdicts[index] if verdicts is not None else "UNVERIFIED"
        if not isinstance(entry, dict):
            emit(f"module {index:0{width}d} <malformed entry>  {verdict}")
            continue
        emit(
            f"module {index:0{width}d} {_short(entry.get('name', '?'), 55)}  "
            f"{_short(entry.get('filedata_alg', '?'), 16)}:{entry.get('filedata_hash', '?')}"
            f"  {verdict}"
        )


def _context(stage, check, result, report, emit):
    artifacts = result.get("verified_artifacts", {})
    evidence = report.get("evidence", {})
    if not isinstance(evidence, dict):
        evidence = {}
    passed = check["status"] == "passed"
    if stage == "endorsements":
        for key, label in [
            ("amd_chain_pem", "AMD chain input"),
            ("vcek_der", "VCEK input"),
        ]:
            digest = result.get("input_sha256", {}).get(key)
            if digest:
                emit(f"          {label} SHA-256 {_short(digest)}")
    elif stage == "snp_signature" and "report" in evidence:
        emit("          SNP/HCL bytes: " + _fingerprint(evidence["report"]))
    elif stage == "platform_policy":
        platform = result.get("verified_claims", {}).get("platform")
        if passed and platform:
            emit(
                f"          {platform['product']}; TCB "
                + ".".join(map(str, platform["reported_tcb"]))
                + "; launch measurement "
                + _short(platform["launch_measurement"])
            )
    elif stage == "hcl_key" and artifacts.get("vtpm_key_sha256"):
        emit("          AK SHA-256 " + _short(artifacts["vtpm_key_sha256"]))
    elif stage in ("quote_signature", "quote"):
        quote = evidence.get("quote", {})
        emit(
            f"          Quote message {len(quote.get('message', []))} bytes; "
            f"signature {len(quote.get('signature', []))} bytes"
        )
    elif stage == "quote_binding" and passed and artifacts.get("certificate_sha256"):
        emit(
            "          Bound certificate DER SHA-256 "
            + _short(artifacts["certificate_sha256"])
        )
    elif stage == "quoted_pcrs" and passed:
        for bank in evidence.get("quote", {}).get("pcr_banks", []):
            values = bank.get("pcr_values", [])
            if len(values) > 10:
                emit(
                    f"          {bank['algo']}: {len(values)} PCR values; PCR 10 = {bytes(values[10]).hex()}"
                )
    elif stage == "reference":
        ref = result.get("reference", {})
        if ref:
            emit(
                f"          {ref['repository']}/{ref['path']}@{_short(ref['commit'], 12)}"
            )
        digest = result.get("input_sha256", {}).get("reference_json")
        if digest:
            emit("          Reference input SHA-256 " + _short(digest))
    elif stage == "pcr10":
        emit(
            "          Method: "
            + result.get("coverage", {}).get("pcr10_method", "not evaluated")
        )


def describe_verification(result, report=None, reference=None, emit=line):
    """Render actual check order, inserting evidence at its relevant stage."""
    report = _json(report)
    emit("VERIFICATION RESULTS  " + format_utc(result["evaluated_at"]))
    emit(
        "  Report SHA-256 "
        + _short(result["report_sha256"])
        + " · policy SHA-256 "
        + _short(result["policy_sha256"])
        + " (full values in archive)"
    )
    legacy = any(c["stage"] in ("quote", "measurements") for c in result["checks"])
    if legacy:
        emit(
            "Legacy result: combined stages; replay inputs to obtain the current detailed checks"
        )
    modules_shown = False
    evidence = report.get("evidence", {})
    entries = evidence.get("ima_measurements", []) if isinstance(evidence, dict) else []
    verdicts = (
        _module_verdicts(result, reference, entries) if isinstance(entries, list) else None
    )
    for check in result["checks"]:
        stage = check["stage"]
        if stage in ("ima_reference", "measurements"):
            describe_modules(report, emit, verdicts=verdicts)
            modules_shown = True
        label = _LABELS.get(stage, stage)
        emit(
            f"  {check['status'].upper():6}  {label}: {check['detail']}"
            + (f" [{check['reason']}]" if check["status"] != "passed" else "")
        )
        try:
            _context(stage, check, result, report, emit)
        except (KeyError, TypeError, ValueError, AttributeError, OverflowError):
            emit(
                "          Received context cannot be displayed; verifier result is shown above"
            )
    if not modules_shown:
        describe_modules(report, emit)
