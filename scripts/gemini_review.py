#!/usr/bin/env python3
"""Strict independent CV reviewer via AGY (Gemini), per GOAL section 6.

Hermes must not self-approve visual quality. This adapter renders review
prompts that force Gemini to open and inspect the actual image files, returns
the structured verdict, and never includes Hermes's preferred choice before
the first independent ranking (blind mode).

Usage:
  gemini_review.py rank   --reference R.png... --candidate C1=label --candidate C2=label ...
  gemini_review.py gate   --stage face --reference R.png... --render current.png --log evidence.json
Exit: 0 PASS, 1 REVISE, 2 FAIL/ERROR. Machine-readable verdict on stdout last line.
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

VERDICT_SCHEMA = {
    "type": "object",
    "properties": {
        "verdict": {"type": "string", "enum": ["PASS", "REVISE", "FAIL"]},
        "rank": {"type": "array", "items": {"type": "string"}},
        "top_mismatches": {"type": "array", "items": {"type": "string"}},
        "severity": {"type": "string", "enum": ["none", "minor", "major", "critical"]},
        "correction_targets": {"type": "array", "items": {"type": "string"}},
        "evidence_only": {"type": "boolean"},
    },
    "required": ["verdict", "top_mismatches", "severity", "correction_targets"],
}

STRICT_RULES = """STRICT CV REVIEWER RULES:
- You MUST open and look at every image file path given. Judge ONLY visible pixels.
- Do not praise. Do not infer intended quality. If you cannot see it, say UNKNOWN.
- Same colors / same ribbon / same flowers are NOT sufficient for identity.
- Identity = face geometry + eye design + hair silhouette + outfit + proportions.
- Verdict PASS only if a fan of the reference character would recognize this avatar
  from the reviewed views alone."""


def run_agy(paths: list[Path], prompt: str, schema: dict) -> dict:
    agy = shutil.which("agy")
    if agy is None:
        raise SystemExit("agy CLI not found")
    dirs = sorted({str(p.parent) for p in paths})
    cmd = [agy, "--output-format", "json", "--dangerously-skip-permissions"]
    schema_file = None
    if schema is not None:
        schema_file = tempfile.NamedTemporaryFile(  # noqa: SIM115
            "w", suffix=".json", delete=False
        )
        schema_file.write(json.dumps(schema))
        schema_file.close()
        cmd += ["--json-schema", schema_file.name]
    for d in dirs:
        cmd += ["--add-dir", d]
    file_list = "\n".join(f"- {p}" for p in paths)
    full = f"{prompt}\n\nIMAGE FILES (open and inspect each):\n{file_list}\n"
    cmd += ["--print", full]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=420)  # noqa: S603
    out = result.stdout.strip()
    if not out:
        raise SystemExit(f"agy produced no output: {result.stderr[:400]}")
    payload = json.loads(out)
    body = payload.get("response", "")
    # response may itself be the schema JSON
    try:
        verdict = json.loads(body)
    except json.JSONDecodeError:
        start = body.find("{")
        end = body.rfind("}")
        if start == -1 or end <= start:
            verdict = {"verdict": "FAIL", "top_mismatches": ["reviewer output unparsable"],
                       "severity": "critical", "correction_targets": ["rerun review"],
                       "evidence_only": False, "_raw": body[:800]}
        else:
            verdict = json.loads(body[start : end + 1])
    return verdict


def cmd_rank(args: argparse.Namespace) -> int:
    refs = [Path(p) for p in args.reference]
    cands = []
    for entry in args.candidate:
        label, _, path = entry.partition("=")
        cands.append((label, Path(path)))
    paths = refs + [p for _, p in cands]
    missing = [str(p) for p in paths if not p.exists()]
    if missing:
        print(json.dumps({"verdict": "FAIL", "missing_files": missing}))
        return 2
    lines = [
        "Independent blind ranking task for candidate source assets toward a 3D",
        "avatar of the reference character (first image(s) are canonical reference).",
        STRICT_RULES,
        "Rank ALL candidates on: face structure compatibility, head proportions,",
        "eye layout/style, body proportions, hair potential, anime-style fit,",
        "modification effort, and RISK the final result still reads as the source",
        "avatar rather than the reference character. Best first.",
        "Return verdict=PASS if a clear legal base exists in the set (else REVISE),",
        "rank=[labels best..worst], top_mismatches=main risks, severity of overall gap,",
        "correction_targets=what the chosen base must change. Set evidence_only=true.",
        "Candidates: " + ", ".join(f"{label}={p.name}" for label, p in cands),
    ]
    verdict = run_agy(paths, "\n".join(lines), VERDICT_SCHEMA)
    print(json.dumps(verdict, ensure_ascii=False))
    return {"PASS": 0, "REVISE": 1}.get(verdict.get("verdict", "FAIL"), 2)


def cmd_gate(args: argparse.Namespace) -> int:
    paths = [Path(p) for p in args.reference] + [Path(args.render)]
    missing = [str(p) for p in paths if not p.exists()]
    if missing:
        print(json.dumps({"verdict": "FAIL", "missing_files": missing}))
        return 2
    lines = [
        f"Production review gate: stage={args.stage}. The LAST image is the current",
        "avatar render; earlier images are canonical references for the SAME view.",
        STRICT_RULES,
        "Compare only matched views. For each visible mismatch give the specific",
        "correction target and severity. PASS = materially resembles at this stage.",
        "If render views do not match reference views, verdict=REVISE with target",
        "'capture matched views' rather than guessing.",
    ]
    if args.log:
        lines.append(f"Evidence log for context only (do not grade from it): {args.log}")
    verdict = run_agy(paths, "\n".join(lines), VERDICT_SCHEMA)
    print(json.dumps(verdict, ensure_ascii=False))
    return {"PASS": 0, "REVISE": 1}.get(verdict.get("verdict", "FAIL"), 2)


def main() -> int:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="mode", required=True)
    r = sub.add_parser("rank")
    r.add_argument("--reference", action="append", required=True)
    r.add_argument("--candidate", action="append", required=True)
    r.set_defaults(func=cmd_rank)
    g = sub.add_parser("gate")
    g.add_argument("--stage", required=True)
    g.add_argument("--reference", action="append", required=True)
    g.add_argument("--render", required=True)
    g.add_argument("--log")
    g.set_defaults(func=cmd_gate)
    args = ap.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
