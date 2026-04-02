"""Tests for profiles.py — built-in pipeline profiles."""

from __future__ import annotations

import pytest

from pyqual.profiles import (
    PipelineProfile,
    get_profile,
    list_profiles,
    PROFILES,
)


class TestPipelineProfile:
    """Tests for PipelineProfile dataclass."""

    def test_profile_creation(self) -> None:
        profile = PipelineProfile(
            description="Test profile",
            stages=[{"name": "test", "tool": "pytest"}],
            metrics={"coverage_min": 80.0},
        )
        assert profile.description == "Test profile"
        assert len(profile.stages) == 1
        assert profile.metrics["coverage_min"] == 80.0

    def test_profile_defaults(self) -> None:
        profile = PipelineProfile(
            description="Minimal profile",
            stages=[],
        )
        assert profile.metrics == {}
        assert profile.loop == {}
        assert profile.env == {}


class TestGetProfile:
    """Tests for get_profile function."""

    def test_get_existing_profile(self) -> None:
        prof = get_profile("python")
        assert prof is not None
        assert "python" in prof.description.lower()

    def test_get_nonexistent_profile(self) -> None:
        assert get_profile("nonexistent") is None


class TestListProfiles:
    """Tests for list_profiles function."""

    def test_returns_sorted_list(self) -> None:
        names = list_profiles()
        assert names == sorted(names)
        assert "python" in names
        assert "ci" in names

    def test_matches_profiles_dict(self) -> None:
        names = list_profiles()
        assert set(names) == set(PROFILES.keys())


class TestBuiltInProfiles:
    """Tests for built-in profile definitions."""

    def test_python_profile_has_stages(self) -> None:
        prof = PROFILES["python"]
        stage_names = [s["name"] for s in prof.stages]
        assert "analyze" in stage_names
        assert "test" in stage_names
        assert "fix" in stage_names

    def test_python_profile_has_metrics(self) -> None:
        prof = PROFILES["python"]
        assert "cc_max" in prof.metrics
        assert "coverage_min" in prof.metrics

    def test_ci_profile_single_iteration(self) -> None:
        prof = PROFILES["ci"]
        assert prof.loop.get("max_iterations") == 1
        assert prof.loop.get("on_fail") == "report"

    def test_lint_only_profile_no_fix(self) -> None:
        prof = PROFILES["lint-only"]
        stage_names = [s["name"] for s in prof.stages]
        assert "fix" not in stage_names
        assert "prefact" not in stage_names

    def test_security_profile_has_security_stages(self) -> None:
        prof = PROFILES["security"]
        stage_names = [s["name"] for s in prof.stages]
        assert "audit" in stage_names
        assert "bandit" in stage_names
        assert "secrets" in stage_names

    def test_python_full_has_push_publish(self) -> None:
        prof = PROFILES["python-full"]
        stage_names = [s["name"] for s in prof.stages]
        assert "push" in stage_names
        assert "publish" in stage_names

    def test_all_profiles_have_description(self) -> None:
        for name, prof in PROFILES.items():
            assert prof.description, f"Profile {name} missing description"

    def test_all_stages_have_name(self) -> None:
        for name, prof in PROFILES.items():
            for stage in prof.stages:
                assert "name" in stage, f"Profile {name} has stage without name"
