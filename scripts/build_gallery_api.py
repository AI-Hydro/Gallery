#!/usr/bin/env python3
"""Build AI-Hydro Research Gallery static catalogs.

This script intentionally uses only GitHub-native/public signals:
- item manifest contributor metadata
- repository stars/forks
- optional release asset download_count
- optional issue/PR reaction totals

It writes:
- api/gallery.json
- api/contributors.json
- api/reputation.json
"""

from __future__ import annotations

import glob
import json
import os
import re
import sys
import urllib.error
import urllib.request
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ALLOWED_TYPES = {
    "map_scene",
    "style_preset",
    "dataset_connector",
    "case_study",
    "map_plate_template",
}
ALLOWED_TRUST = {"official", "reviewed", "community", "local"}
REQUIRED = [
    "id",
    "type",
    "title",
    "description",
    "version",
    "author",
    "license",
    "trustLevel",
    "tags",
    "citation",
]
ROOT = Path(__file__).resolve().parents[1]
API = ROOT / "api"
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")
GITHUB_API = "https://api.github.com"


def github_get(path_or_url: str) -> Any | None:
    url = path_or_url if path_or_url.startswith("http") else f"{GITHUB_API}{path_or_url}"
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "AI-Hydro-Gallery-Catalog-Builder",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    if GITHUB_TOKEN:
        headers["Authorization"] = f"Bearer {GITHUB_TOKEN}"
    request = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            return json.loads(response.read().decode("utf-8"))
    except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError) as exc:
        print(f"warning: GitHub metric fetch failed for {url}: {exc}", file=sys.stderr)
        return None


def parse_github_repo(url: str | None) -> tuple[str, str] | None:
    if not url:
        return None
    match = re.search(r"github\.com/([^/\s]+)/([^/\s#?]+)", url)
    if not match:
        return None
    owner, repo = match.group(1), match.group(2).removesuffix(".git")
    return owner, repo


def parse_issue_url(url: str | None) -> tuple[str, str, int] | None:
    if not url:
        return None
    match = re.search(r"github\.com/([^/\s]+)/([^/\s]+)/issues/(\d+)", url)
    if not match:
        match = re.search(r"github\.com/([^/\s]+)/([^/\s]+)/pull/(\d+)", url)
    if not match:
        return None
    return match.group(1), match.group(2), int(match.group(3))


def repo_metrics(repo_ref: tuple[str, str] | None) -> dict[str, int]:
    if not repo_ref:
        return {"githubStars": 0, "githubForks": 0}
    owner, repo = repo_ref
    data = github_get(f"/repos/{owner}/{repo}") or {}
    return {
        "githubStars": int(data.get("stargazers_count") or 0),
        "githubForks": int(data.get("forks_count") or 0),
    }


def release_asset_downloads(url: str | None) -> int:
    if not url:
        return 0
    repo_ref = parse_github_repo(url)
    if not repo_ref:
        return 0
    owner, repo = repo_ref
    releases = github_get(f"/repos/{owner}/{repo}/releases?per_page=100") or []
    if not isinstance(releases, list):
        return 0
    for release in releases:
        for asset in release.get("assets", []):
            if url in {asset.get("browser_download_url"), asset.get("url"), asset.get("html_url")}:
                return int(asset.get("download_count") or 0)
    return 0


def issue_reactions(url: str | None) -> int:
    parsed = parse_issue_url(url)
    if not parsed:
        return 0
    owner, repo, number = parsed
    data = github_get(f"/repos/{owner}/{repo}/issues/{number}") or {}
    reactions = data.get("reactions") or {}
    if isinstance(reactions, dict):
        return int(reactions.get("total_count") or 0)
    return 0


def normalize_contributors(item: dict[str, Any]) -> list[dict[str, Any]]:
    contributors = item.get("contributors")
    if not contributors:
        github = item.get("authorGithub") or ""
        contributors = [
            {
                "github": github,
                "name": item.get("author", ""),
                "profileUrl": item.get("authorUrl", ""),
                "orcid": item.get("orcid", ""),
                "affiliation": item.get("affiliation", ""),
                "roles": ["author"],
            }
        ]

    normalized = []
    for contributor in contributors:
        roles = contributor.get("roles") or ["author"]
        if not isinstance(roles, list):
            roles = [str(roles)]
        normalized.append(
            {
                "github": str(contributor.get("github") or "").strip(),
                "name": str(contributor.get("name") or contributor.get("github") or "Unknown contributor").strip(),
                "orcid": str(contributor.get("orcid") or "").strip(),
                "affiliation": str(contributor.get("affiliation") or "").strip(),
                "profileUrl": str(
                    contributor.get("profileUrl")
                    or contributor.get("profile_url")
                    or contributor.get("url")
                    or contributor.get("website")
                    or ""
                ).strip(),
                "website": str(contributor.get("website") or "").strip(),
                "linkedin": str(contributor.get("linkedin") or contributor.get("linkedinUrl") or "").strip(),
                "googleScholar": str(
                    contributor.get("googleScholar") or contributor.get("google_scholar") or contributor.get("scholar") or ""
                ).strip(),
                "citationUrl": str(contributor.get("citationUrl") or contributor.get("citation_url") or "").strip(),
                "roles": roles,
            }
        )
    return normalized


def derive_badges(item: dict[str, Any], metrics: dict[str, int]) -> list[str]:
    badges = list(item.get("badges") or [])
    if item.get("trustLevel") == "official" and "Official" not in badges:
        badges.append("Official")
    if item.get("citation") and item.get("license") and "Citation-ready" not in badges:
        badges.append("Citation-ready")
    if metrics.get("downloads", 0) >= 100 and "Highly used" not in badges:
        badges.append("Highly used")
    if metrics.get("reactions", 0) >= 10 and "Community favorite" not in badges:
        badges.append("Community favorite")
    return badges


def build() -> None:
    now = datetime.now(timezone.utc).date().isoformat()
    items: list[dict[str, Any]] = []
    errors: list[str] = []
    repo_metric_cache: dict[tuple[str, str], dict[str, int]] = {}

    for manifest_path in sorted(glob.glob(str(ROOT / "items/**/manifest.json"), recursive=True)):
        with open(manifest_path, encoding="utf-8") as f:
            item = json.load(f)

        item_id = item.get("id") or Path(manifest_path).parent.name
        item["id"] = item_id
        missing = [field for field in REQUIRED if not item.get(field)]
        if missing:
            errors.append(f"{manifest_path}: missing {', '.join(missing)}")
        if item.get("type") not in ALLOWED_TYPES:
            errors.append(f"{manifest_path}: invalid type {item.get('type')}")
        if item.get("trustLevel") not in ALLOWED_TRUST:
            errors.append(f"{manifest_path}: invalid trustLevel {item.get('trustLevel')}")
        if not isinstance(item.get("tags"), list):
            errors.append(f"{manifest_path}: tags must be a list")

        item.setdefault("thumbnailUrl", "")
        item.setdefault("artifactUrl", "")
        item.setdefault("githubUrl", f"https://github.com/AI-Hydro/Gallery/tree/main/items/{item_id}")
        item.setdefault("authorUrl", "")
        item.setdefault("citationUrl", "")
        item.setdefault("createdAt", now)
        item["updatedAt"] = now
        item.setdefault("isFeatured", False)
        item.setdefault("isInstalled", False)
        item.setdefault("discussionUrl", "")
        item.setdefault("releaseAssetUrl", "")
        item.setdefault("importWarnings", [])
        item["contributors"] = normalize_contributors(item)

        repo_ref = parse_github_repo(item.get("githubUrl")) or ("AI-Hydro", "Gallery")
        if repo_ref not in repo_metric_cache:
            repo_metric_cache[repo_ref] = repo_metrics(repo_ref)
        repo_stats = repo_metric_cache[repo_ref]
        metrics = {
            "installs": int(item.get("downloadCount") or item.get("download_count") or 0),
            "downloads": release_asset_downloads(item.get("releaseAssetUrl")),
            "githubStars": repo_stats["githubStars"],
            "githubForks": repo_stats["githubForks"],
            "reactions": issue_reactions(item.get("discussionUrl")),
        }
        item["metrics"] = metrics
        item["downloadCount"] = metrics["installs"]
        item["githubReactions"] = metrics["reactions"]
        item["githubStars"] = metrics["githubStars"]
        item["badges"] = derive_badges(item, metrics)
        items.append(item)

    if errors:
        print("\n".join(errors), file=sys.stderr)
        raise SystemExit(1)

    contributors: dict[str, dict[str, Any]] = {}
    anonymous_count = 0
    for item in items:
        for contributor in item["contributors"]:
            key = contributor.get("github") or f"anonymous-{anonymous_count}"
            if not contributor.get("github"):
                anonymous_count += 1
            record = contributors.setdefault(
                key,
                {
                    "github": contributor.get("github", ""),
                    "name": contributor.get("name", ""),
                    "orcid": contributor.get("orcid", ""),
                    "affiliation": contributor.get("affiliation", ""),
                    "profileUrl": contributor.get("profileUrl", ""),
                    "website": contributor.get("website", ""),
                    "linkedin": contributor.get("linkedin", ""),
                    "googleScholar": contributor.get("googleScholar", ""),
                    "citationUrl": contributor.get("citationUrl", ""),
                    "contributions": [],
                    "totals": {
                        "items": 0,
                        "official": 0,
                        "reviewed": 0,
                        "community": 0,
                        "local": 0,
                        "installs": 0,
                        "downloads": 0,
                        "reactions": 0,
                        "githubStars": 0,
                    },
                    "badges": [],
                },
            )
            record["contributions"].append(
                {
                    "marketplace": "gallery",
                    "itemId": item["id"],
                    "title": item["title"],
                    "type": item["type"],
                    "role": ", ".join(contributor.get("roles") or ["author"]),
                    "trustLevel": item["trustLevel"],
                    "githubUrl": item.get("githubUrl", ""),
                }
            )
            totals = record["totals"]
            totals["items"] += 1
            totals[item["trustLevel"]] += 1
            totals["installs"] += int(item["metrics"]["installs"])
            totals["downloads"] += int(item["metrics"]["downloads"])
            totals["reactions"] += int(item["metrics"]["reactions"])
            totals["githubStars"] = max(totals["githubStars"], int(item["metrics"]["githubStars"]))

    for record in contributors.values():
        badges = []
        if record["totals"]["items"] >= 1:
            badges.append("AI-Hydro contributor")
        if record["totals"]["official"] >= 1:
            badges.append("Official contributor")
        if record["totals"]["items"] >= 3:
            badges.append("Gallery builder")
        record["badges"] = badges

    reputation = {
        "schemaVersion": "1.0",
        "generatedAtUtc": datetime.now(timezone.utc).isoformat(),
        "marketplace": "gallery",
        "metricsSource": "github-native",
        "items": [
            {
                "id": item["id"],
                "title": item["title"],
                "type": item["type"],
                "trustLevel": item["trustLevel"],
                "contributors": item["contributors"],
                "badges": item["badges"],
                "metrics": item["metrics"],
            }
            for item in items
        ],
        "contributors": sorted(contributors.values(), key=lambda x: (-x["totals"]["items"], x["name"].lower())),
    }

    API.mkdir(exist_ok=True)
    outputs = {
        "gallery.json": items,
        "contributors.json": sorted(contributors.values(), key=lambda x: (-x["totals"]["items"], x["name"].lower())),
        "reputation.json": reputation,
    }
    for name, payload in outputs.items():
        with open(API / name, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2)
            f.write("\n")
    print(f"Wrote {len(items)} gallery item(s) and {len(contributors)} contributor profile(s)")


if __name__ == "__main__":
    build()
