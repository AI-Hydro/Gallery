"""
Certification step for AI-Hydro marketplace manifests (Phase 3.3).

Reads raw item manifests, checks each against the certification criteria,
and returns a certification record per item. Intended to be called from
build-api.yml CI and to inject certification data into the generated API JSON.

Certification criteria (all must pass for certified=true):
  1. citation — non-empty string
  2. trustLevel — one of {"official", "community", "experimental"}
  3. badges — non-empty list
  4. license — non-empty string

A certified item gets:
  "certification": {
      "certified": true,
      "certified_at": "<ISO date>",
      "checks_passed": [...],
      "checks_failed": []
  }

An uncertified item gets certified=false with checks_failed populated.

Usage (standalone):
    python3 scripts/certify_manifests.py  --manifest-glob "items/*/manifest.json"

Usage (from build_gallery_api.py / inline in CI):
    from scripts.certify_manifests import certify_manifest
    cert = certify_manifest(manifest_dict)
    manifest_dict["certification"] = cert
"""
from __future__ import annotations

import argparse
import glob
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

VALID_TRUST_LEVELS = {"official", "community", "experimental"}


def certify_manifest(manifest: dict, certified_at: str | None = None) -> dict:
    """Return a certification record for one manifest dict.

    Does NOT mutate the manifest.  The caller is responsible for injecting the
    returned dict under ``manifest["certification"]`` in the API output.
    """
    if certified_at is None:
        certified_at = datetime.now(timezone.utc).date().isoformat()

    checks_passed: list[str] = []
    checks_failed: list[str] = []

    # 1. Citation
    citation = manifest.get("citation") or ""
    if isinstance(citation, str) and citation.strip():
        checks_passed.append("citation")
    else:
        checks_failed.append("citation: missing or empty")

    # 2. Trust level
    trust_level = manifest.get("trustLevel") or ""
    if trust_level in VALID_TRUST_LEVELS:
        checks_passed.append("trustLevel")
    else:
        checks_failed.append(
            f"trustLevel: must be one of {sorted(VALID_TRUST_LEVELS)!r}, got {trust_level!r}"
        )

    # 3. Badges
    badges = manifest.get("badges") or []
    if isinstance(badges, list) and len(badges) > 0:
        checks_passed.append("badges")
    else:
        checks_failed.append("badges: missing or empty list")

    # 4. License
    license_val = manifest.get("license") or ""
    if isinstance(license_val, str) and license_val.strip():
        checks_passed.append("license")
    else:
        checks_failed.append("license: missing or empty")

    certified = len(checks_failed) == 0

    return {
        "certified": certified,
        "certified_at": certified_at if certified else None,
        "checks_passed": checks_passed,
        "checks_failed": checks_failed,
    }


def certify_skills_manifest(manifest: dict, certified_at: str | None = None) -> dict:
    """Certification for Skills manifests (SKILL.md frontmatter).

    Skills have a different schema: name, when_to_use, tools_used, tags.
    Certification criteria:
      1. description — non-empty
      2. when_to_use — non-empty
      3. tools_used — non-empty list
      4. tags — non-empty list
    """
    if certified_at is None:
        certified_at = datetime.now(timezone.utc).date().isoformat()

    checks_passed: list[str] = []
    checks_failed: list[str] = []

    desc = manifest.get("description") or ""
    if isinstance(desc, str) and desc.strip():
        checks_passed.append("description")
    else:
        checks_failed.append("description: missing or empty")

    when = manifest.get("when_to_use") or ""
    if isinstance(when, str) and when.strip():
        checks_passed.append("when_to_use")
    else:
        checks_failed.append("when_to_use: missing or empty")

    tools = manifest.get("tools_used") or []
    if isinstance(tools, list) and len(tools) > 0:
        checks_passed.append("tools_used")
    else:
        checks_failed.append("tools_used: missing or empty list")

    tags = manifest.get("tags") or []
    if isinstance(tags, list) and len(tags) > 0:
        checks_passed.append("tags")
    else:
        checks_failed.append("tags: missing or empty list")

    certified = len(checks_failed) == 0
    return {
        "certified": certified,
        "certified_at": certified_at if certified else None,
        "checks_passed": checks_passed,
        "checks_failed": checks_failed,
    }


def certify_module_manifest(manifest: dict, certified_at: str | None = None) -> dict:
    """Certification for Modules manifests.

    Modules criteria:
      1. citation — non-empty dict or string
      2. description — non-empty
      3. tags — non-empty list
      4. estimatedMinutes — positive int
    """
    if certified_at is None:
        certified_at = datetime.now(timezone.utc).date().isoformat()

    checks_passed: list[str] = []
    checks_failed: list[str] = []

    citation = manifest.get("citation") or {}
    if (isinstance(citation, dict) and citation.get("text", "").strip()) or \
       (isinstance(citation, str) and citation.strip()):
        checks_passed.append("citation")
    else:
        checks_failed.append("citation: missing or has no text")

    desc = manifest.get("description") or ""
    if isinstance(desc, str) and desc.strip():
        checks_passed.append("description")
    else:
        checks_failed.append("description: missing or empty")

    tags = manifest.get("tags") or []
    if isinstance(tags, list) and len(tags) > 0:
        checks_passed.append("tags")
    else:
        checks_failed.append("tags: missing or empty list")

    minutes = manifest.get("estimatedMinutes") or 0
    if isinstance(minutes, int) and minutes > 0:
        checks_passed.append("estimatedMinutes")
    else:
        checks_failed.append("estimatedMinutes: missing or not a positive integer")

    certified = len(checks_failed) == 0
    return {
        "certified": certified,
        "certified_at": certified_at if certified else None,
        "checks_passed": checks_passed,
        "checks_failed": checks_failed,
    }


# ---------------------------------------------------------------------------
# CLI entry point (standalone check)
# ---------------------------------------------------------------------------

def _cli() -> None:
    parser = argparse.ArgumentParser(description="Certify AI-Hydro marketplace manifests")
    parser.add_argument(
        "--manifest-glob", default="items/*/manifest.json",
        help="Glob pattern for manifest files"
    )
    parser.add_argument(
        "--surface", choices=["gallery", "skills", "modules"], default="gallery",
        help="Which surface schema to certify against"
    )
    parser.add_argument("--fail-on-uncertified", action="store_true",
                        help="Exit 1 if any manifests are uncertified")
    args = parser.parse_args()

    fn = {"gallery": certify_manifest, "skills": certify_skills_manifest,
          "modules": certify_module_manifest}[args.surface]

    n_pass = n_fail = 0
    for path in sorted(glob.glob(args.manifest_glob)):
        with open(path) as f:
            manifest = json.load(f)
        cert = fn(manifest)
        item_id = manifest.get("id") or manifest.get("name") or manifest.get("moduleId") or path
        if cert["certified"]:
            n_pass += 1
            print(f"  PASS  {item_id}  ({len(cert['checks_passed'])} checks)")
        else:
            n_fail += 1
            print(f"  FAIL  {item_id}")
            for reason in cert["checks_failed"]:
                print(f"         - {reason}")

    print(f"\n{n_pass} certified, {n_fail} failed")
    if args.fail_on_uncertified and n_fail > 0:
        sys.exit(1)


if __name__ == "__main__":
    _cli()
