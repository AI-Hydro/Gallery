"""
Tests for certify_manifests.py — Phase 3.3 certification logic.

Run from Gallery/:  python3 -m pytest scripts/test_certify.py -v
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from certify_manifests import (
    certify_manifest,
    certify_skills_manifest,
    certify_module_manifest,
)


GOOD_GALLERY = {
    "id": "test-scene",
    "citation": "U.S. Geological Survey. NLDI basin service.",
    "trustLevel": "official",
    "badges": ["Official", "Citation-ready"],
    "license": "Apache-2.0",
}

GOOD_SKILL = {
    "id": "baseflow-separation",
    "description": "Separate baseflow from streamflow.",
    "when_to_use": "When the user asks about BFI or groundwater.",
    "tools_used": ["extract_hydrological_signatures"],
    "tags": ["baseflow", "BFI"],
}

GOOD_MODULE = {
    "moduleId": "baseflow-separation",
    "description": "Interactive baseflow separation module.",
    "citation": {"text": "Lyne & Hollick (1979). Stochastic time-variable rainfall-runoff modelling."},
    "tags": ["baseflow", "Lyne-Hollick"],
    "estimatedMinutes": 40,
}


class TestGalleryCertification(unittest.TestCase):
    def test_fully_valid_item_passes(self):
        cert = certify_manifest(GOOD_GALLERY)
        self.assertTrue(cert["certified"])
        self.assertFalse(cert["checks_failed"])
        self.assertEqual(set(cert["checks_passed"]), {"citation", "trustLevel", "badges", "license"})

    def test_missing_citation_fails(self):
        m = {**GOOD_GALLERY, "citation": ""}
        cert = certify_manifest(m)
        self.assertFalse(cert["certified"])
        self.assertTrue(any("citation" in f for f in cert["checks_failed"]))

    def test_none_citation_fails(self):
        m = {**GOOD_GALLERY, "citation": None}
        cert = certify_manifest(m)
        self.assertFalse(cert["certified"])

    def test_invalid_trust_level_fails(self):
        m = {**GOOD_GALLERY, "trustLevel": "unverified"}
        cert = certify_manifest(m)
        self.assertFalse(cert["certified"])
        self.assertTrue(any("trustLevel" in f for f in cert["checks_failed"]))

    def test_valid_trust_levels(self):
        for level in ("official", "community", "experimental"):
            m = {**GOOD_GALLERY, "trustLevel": level}
            self.assertTrue(certify_manifest(m)["certified"], f"trustLevel={level} should pass")

    def test_empty_badges_fails(self):
        m = {**GOOD_GALLERY, "badges": []}
        cert = certify_manifest(m)
        self.assertFalse(cert["certified"])

    def test_missing_license_fails(self):
        m = {**GOOD_GALLERY, "license": ""}
        cert = certify_manifest(m)
        self.assertFalse(cert["certified"])

    def test_certified_at_set_on_pass(self):
        cert = certify_manifest(GOOD_GALLERY)
        self.assertIsNotNone(cert["certified_at"])

    def test_certified_at_none_on_fail(self):
        m = {**GOOD_GALLERY, "citation": ""}
        cert = certify_manifest(m)
        self.assertIsNone(cert["certified_at"])

    def test_custom_certified_at(self):
        cert = certify_manifest(GOOD_GALLERY, certified_at="2026-06-13")
        self.assertEqual(cert["certified_at"], "2026-06-13")

    def test_real_gallery_manifest_passes(self):
        """The actual conus-reference-basins-scene manifest must pass."""
        import json
        manifest_path = Path(__file__).parent.parent / "items" / "conus-reference-basins-scene" / "manifest.json"
        if not manifest_path.exists():
            self.skipTest("Gallery manifest not found")
        with open(manifest_path) as f:
            m = json.load(f)
        cert = certify_manifest(m)
        self.assertTrue(cert["certified"], f"Real manifest failed: {cert['checks_failed']}")


class TestSkillsCertification(unittest.TestCase):
    def test_fully_valid_skill_passes(self):
        cert = certify_skills_manifest(GOOD_SKILL)
        self.assertTrue(cert["certified"])
        self.assertFalse(cert["checks_failed"])

    def test_missing_description_fails(self):
        s = {**GOOD_SKILL, "description": ""}
        self.assertFalse(certify_skills_manifest(s)["certified"])

    def test_missing_when_to_use_fails(self):
        s = {**GOOD_SKILL, "when_to_use": ""}
        self.assertFalse(certify_skills_manifest(s)["certified"])

    def test_empty_tools_used_fails(self):
        s = {**GOOD_SKILL, "tools_used": []}
        self.assertFalse(certify_skills_manifest(s)["certified"])

    def test_empty_tags_fails(self):
        s = {**GOOD_SKILL, "tags": []}
        self.assertFalse(certify_skills_manifest(s)["certified"])


class TestModuleCertification(unittest.TestCase):
    def test_fully_valid_module_passes(self):
        cert = certify_module_manifest(GOOD_MODULE)
        self.assertTrue(cert["certified"])
        self.assertFalse(cert["checks_failed"])

    def test_missing_citation_text_fails(self):
        m = {**GOOD_MODULE, "citation": {"text": ""}}
        self.assertFalse(certify_module_manifest(m)["certified"])

    def test_string_citation_passes(self):
        m = {**GOOD_MODULE, "citation": "Lyne & Hollick (1979)."}
        self.assertTrue(certify_module_manifest(m)["certified"])

    def test_empty_description_fails(self):
        m = {**GOOD_MODULE, "description": ""}
        self.assertFalse(certify_module_manifest(m)["certified"])

    def test_zero_minutes_fails(self):
        m = {**GOOD_MODULE, "estimatedMinutes": 0}
        self.assertFalse(certify_module_manifest(m)["certified"])

    def test_negative_minutes_fails(self):
        m = {**GOOD_MODULE, "estimatedMinutes": -5}
        self.assertFalse(certify_module_manifest(m)["certified"])

    def test_empty_tags_fails(self):
        m = {**GOOD_MODULE, "tags": []}
        self.assertFalse(certify_module_manifest(m)["certified"])
