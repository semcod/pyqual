"""Tests for pyqual gates and collectors."""

import json
from pathlib import Path
import tempfile

import pytest

from pyqual.gates import GateSet, GateResult, Gate
from pyqual.config import GateConfig


class TestSecurityCollectors:
    """Test security metric collectors (safety, bandit, secrets)."""

    def test_from_safety_pip_audit(self):
        """Test parsing pip-audit/safety JSON output."""
        with tempfile.TemporaryDirectory() as tmpdir:
            workdir = Path(tmpdir)
            pyqual_dir = workdir / ".pyqual"
            pyqual_dir.mkdir()

            # Create pip_audit.json with vulnerabilities
            audit_data = {
                "vulnerabilities": [
                    {"severity": "HIGH", "package": "requests"},
                    {"severity": "MEDIUM", "package": "urllib3"},
                    {"severity": "LOW", "package": "certifi"},
                ]
            }
            (pyqual_dir / "pip_audit.json").write_text(json.dumps(audit_data))

            gate_set = GateSet([])
            metrics = gate_set._from_safety(workdir)

            assert metrics["vuln_high"] == 1.0
            assert metrics["vuln_medium"] == 1.0
            assert metrics["vuln_low"] == 1.0
            assert metrics["vuln_total"] == 3.0

    def test_from_bandit(self):
        """Test parsing bandit JSON output."""
        with tempfile.TemporaryDirectory() as tmpdir:
            workdir = Path(tmpdir)
            pyqual_dir = workdir / ".pyqual"
            pyqual_dir.mkdir()

            bandit_data = {
                "results": [
                    {"issue_severity": "HIGH", "test_id": "B101"},
                    {"issue_severity": "HIGH", "test_id": "B102"},
                    {"issue_severity": "MEDIUM", "test_id": "B301"},
                    {"issue_severity": "LOW", "test_id": "B501"},
                ]
            }
            (pyqual_dir / "bandit.json").write_text(json.dumps(bandit_data))

            gate_set = GateSet([])
            metrics = gate_set._from_bandit(workdir)

            assert metrics["bandit_high"] == 2.0
            assert metrics["bandit_medium"] == 1.0
            assert metrics["bandit_low"] == 1.0

    def test_from_secrets_trufflehog(self):
        """Test parsing trufflehog/gitleaks JSON output."""
        with tempfile.TemporaryDirectory() as tmpdir:
            workdir = Path(tmpdir)
            pyqual_dir = workdir / ".pyqual"
            pyqual_dir.mkdir()

            # Test list format
            secrets = [{"SourceMetadata": {}}, {"SourceMetadata": {}}]
            (pyqual_dir / "trufflehog.json").write_text(json.dumps(secrets))

            gate_set = GateSet([])
            metrics = gate_set._from_secrets(workdir)

            assert metrics["secrets_found"] == 2.0

    def test_from_secrets_gitleaks(self):
        """Test parsing gitleaks dict format."""
        with tempfile.TemporaryDirectory() as tmpdir:
            workdir = Path(tmpdir)
            pyqual_dir = workdir / ".pyqual"
            pyqual_dir.mkdir()

            gitleaks_data = {"findings": [{"rule": "aws-key"}, {"rule": "slack-token"}]}
            (pyqual_dir / "gitleaks.json").write_text(json.dumps(gitleaks_data))

            gate_set = GateSet([])
            metrics = gate_set._from_secrets(workdir)

            assert metrics["secrets_found"] == 2.0


class TestQualityCollectors:
    """Test quality metric collectors (mypy, radon, pip_outdated)."""

    def test_from_mypy(self):
        """Test parsing mypy JSON output."""
        with tempfile.TemporaryDirectory() as tmpdir:
            workdir = Path(tmpdir)
            pyqual_dir = workdir / ".pyqual"
            pyqual_dir.mkdir()

            mypy_errors = [
                {"file": "app.py", "line": 10, "message": "Missing return statement"},
                {"file": "utils.py", "line": 5, "message": "Incompatible types"},
            ]
            (pyqual_dir / "mypy.json").write_text(json.dumps(mypy_errors))

            gate_set = GateSet([])
            metrics = gate_set._from_mypy(workdir)

            assert metrics["mypy_errors"] == 2.0

    def test_from_radon_mi(self):
        """Test parsing radon maintainability index JSON."""
        with tempfile.TemporaryDirectory() as tmpdir:
            workdir = Path(tmpdir)
            pyqual_dir = workdir / ".pyqual"
            pyqual_dir.mkdir()

            radon_data = {
                "app.py": {"mi": 75.5},
                "utils.py": {"mi": 82.3},
                "test.py": {"mi": 68.0},
            }
            (pyqual_dir / "radon_mi.json").write_text(json.dumps(radon_data))

            gate_set = GateSet([])
            metrics = gate_set._from_radon(workdir)

            assert pytest.approx(metrics["mi_avg"], 0.01) == 75.27  # (75.5 + 82.3 + 68.0) / 3
            assert metrics["mi_min"] == 68.0

    def test_from_pip_outdated(self):
        """Test parsing pip list --outdated JSON."""
        with tempfile.TemporaryDirectory() as tmpdir:
            workdir = Path(tmpdir)
            pyqual_dir = workdir / ".pyqual"
            pyqual_dir.mkdir()

            outdated = [
                {"name": "requests", "version": "2.28.0", "latest": "2.31.0"},
                {"name": "numpy", "version": "1.23.0", "latest": "1.26.0"},
            ]
            (pyqual_dir / "outdated.json").write_text(json.dumps(outdated))

            gate_set = GateSet([])
            metrics = gate_set._from_pip_outdated(workdir)

            assert metrics["outdated_deps"] == 2.0

    def test_from_pytest_durations(self):
        """Test parsing pytest duration JSON."""
        with tempfile.TemporaryDirectory() as tmpdir:
            workdir = Path(tmpdir)
            pyqual_dir = workdir / ".pyqual"
            pyqual_dir.mkdir()

            pytest_data = {
                "duration": 45.5,
                "tests": [
                    {"name": "test_fast", "duration": 0.1},
                    {"name": "test_slow", "duration": 2.5},
                    {"name": "test_medium", "duration": 0.8},
                ]
            }
            (pyqual_dir / "pytest_durations.json").write_text(json.dumps(pytest_data))

            gate_set = GateSet([])
            metrics = gate_set._from_pytest_durations(workdir)

            assert metrics["test_time"] == 45.5
            assert metrics["slow_tests"] == 1.0  # Only test_slow > 1.0s


class TestLinterCollectors:
    """Test linter metric collectors (ruff, pylint, flake8)."""

    def test_from_ruff(self):
        """Test parsing ruff JSON output."""
        with tempfile.TemporaryDirectory() as tmpdir:
            workdir = Path(tmpdir)
            pyqual_dir = workdir / ".pyqual"
            pyqual_dir.mkdir()

            ruff_data = [
                {"code": "E501", "message": "Line too long", "severity": "error"},
                {"code": "E401", "message": "Multiple imports", "severity": "error"},
                {"code": "W291", "message": "Trailing whitespace", "severity": "warning"},
            ]
            (pyqual_dir / "ruff.json").write_text(json.dumps(ruff_data))

            gate_set = GateSet([])
            metrics = gate_set._from_ruff(workdir)

            assert metrics["ruff_errors"] == 3.0
            assert metrics["ruff_fatal"] == 2.0  # E codes
            assert metrics["ruff_warnings"] == 1.0  # W codes

    def test_from_pylint(self):
        """Test parsing pylint JSON output."""
        with tempfile.TemporaryDirectory() as tmpdir:
            workdir = Path(tmpdir)
            pyqual_dir = workdir / ".pyqual"
            pyqual_dir.mkdir()

            pylint_data = [
                {"type": "error", "symbol": "E0401", "message": "Import error"},
                {"type": "error", "symbol": "E1101", "message": "No member"},
                {"type": "warning", "symbol": "W0611", "message": "Unused import"},
            ]
            (pyqual_dir / "pylint.json").write_text(json.dumps(pylint_data))

            gate_set = GateSet([])
            metrics = gate_set._from_pylint(workdir)

            assert metrics["pylint_errors"] == 3.0
            assert metrics["pylint_error"] == 2.0
            assert metrics["pylint_warnings"] == 1.0

    def test_from_pylint_score(self):
        """Test parsing pylint score output."""
        with tempfile.TemporaryDirectory() as tmpdir:
            workdir = Path(tmpdir)
            pyqual_dir = workdir / ".pyqual"
            pyqual_dir.mkdir()

            pylint_data = {"score": 8.5, "messages": [{}, {}, {}]}
            (pyqual_dir / "pylint.json").write_text(json.dumps(pylint_data))

            gate_set = GateSet([])
            metrics = gate_set._from_pylint(workdir)

            assert metrics["pylint_score"] == 8.5
            assert metrics["pylint_errors"] == 3.0

    def test_from_flake8(self):
        """Test parsing flake8 JSON output."""
        with tempfile.TemporaryDirectory() as tmpdir:
            workdir = Path(tmpdir)
            pyqual_dir = workdir / ".pyqual"
            pyqual_dir.mkdir()

            flake8_data = [
                {"code": "E501", "message": "Line too long"},
                {"code": "E401", "message": "Multiple imports"},
                {"code": "W291", "message": "Trailing whitespace"},
                {"code": "F401", "message": "Unused import"},
                {"code": "C901", "message": "Complex function"},
            ]
            (pyqual_dir / "flake8.json").write_text(json.dumps(flake8_data))

            gate_set = GateSet([])
            metrics = gate_set._from_flake8(workdir)

            assert metrics["flake8_violations"] == 5.0
            assert metrics["flake8_errors"] == 3.0  # E + F codes
            assert metrics["flake8_warnings"] == 1.0  # W codes
            assert metrics["flake8_conventions"] == 1.0  # C codes


    def test_from_interrogate(self):
        """Test parsing interrogate docstring coverage JSON."""
        with tempfile.TemporaryDirectory() as tmpdir:
            workdir = Path(tmpdir)
            pyqual_dir = workdir / ".pyqual"
            pyqual_dir.mkdir()

            interrogate_data = {
                "coverage": 85.5,
                "total": 100,
                "documented": 85,
                "percent_covered": 85.5
            }
            (pyqual_dir / "interrogate.json").write_text(json.dumps(interrogate_data))

            gate_set = GateSet([])
            metrics = gate_set._from_interrogate(workdir)

            assert metrics["docstring_coverage"] == 85.5
            assert metrics["docstring_total"] == 100.0
            assert metrics["docstring_missing"] == 15.0

    def test_from_import_linter(self):
        """Test parsing import-linter JSON output."""
        with tempfile.TemporaryDirectory() as tmpdir:
            workdir = Path(tmpdir)
            pyqual_dir = workdir / ".pyqual"
            pyqual_dir.mkdir()

            import_linter_data = {
                "contracts": [
                    {"name": "layers", "kept": True, "violations": []},
                    {"name": "forbidden", "kept": False, "violations": [
                        {"file": "app.py", "line": 10},
                        {"file": "utils.py", "line": 20}
                    ]}
                ]
            }
            (pyqual_dir / "import_linter.json").write_text(json.dumps(import_linter_data))

            gate_set = GateSet([])
            metrics = gate_set._from_import_linter(workdir)

            assert metrics["import_violations"] == 2.0
            assert metrics["broken_import_contracts"] == 1.0

    def test_from_pydocstyle(self):
        """Test parsing pydocstyle JSON output."""
        with tempfile.TemporaryDirectory() as tmpdir:
            workdir = Path(tmpdir)
            pyqual_dir = workdir / ".pyqual"
            pyqual_dir.mkdir()

            pydocstyle_data = [
                {"code": "D100", "message": "Missing docstring in public module", "file": "app.py"},
                {"code": "D101", "message": "Missing docstring in public class", "file": "app.py"},
                {"code": "D100", "message": "Missing docstring", "file": "utils.py"},
            ]
            (pyqual_dir / "pydocstyle.json").write_text(json.dumps(pydocstyle_data))

            gate_set = GateSet([])
            metrics = gate_set._from_pydocstyle(workdir)

            assert metrics["pydocstyle_violations"] == 3.0
            assert metrics["pydocstyle_d100"] == 2.0
            assert metrics["pydocstyle_d101"] == 1.0

    def test_from_black(self):
        """Test parsing black check JSON output."""
        with tempfile.TemporaryDirectory() as tmpdir:
            workdir = Path(tmpdir)
            pyqual_dir = workdir / ".pyqual"
            pyqual_dir.mkdir()

            black_data = [
                {"path": "app.py", "unchanged": False},
                {"path": "utils.py", "unchanged": False},
                {"path": "test.py", "unchanged": True},
            ]
            (pyqual_dir / "black.json").write_text(json.dumps(black_data))

            gate_set = GateSet([])
            metrics = gate_set._from_black(workdir)

            assert metrics["black_unformatted"] == 3.0

    def test_from_isort(self):
        """Test parsing isort check JSON output."""
        with tempfile.TemporaryDirectory() as tmpdir:
            workdir = Path(tmpdir)
            pyqual_dir = workdir / ".pyqual"
            pyqual_dir.mkdir()

            isort_data = [
                {"path": "app.py", "import_changes": 5},
                {"path": "utils.py", "import_changes": 3},
            ]
            (pyqual_dir / "isort.json").write_text(json.dumps(isort_data))

            gate_set = GateSet([])
            metrics = gate_set._from_isort(workdir)

            assert metrics["isort_unsorted"] == 2.0
            assert metrics["isort_import_changes"] == 8.0

    def test_from_sarif(self):
        """Test parsing SARIF format security output."""
        with tempfile.TemporaryDirectory() as tmpdir:
            workdir = Path(tmpdir)
            pyqual_dir = workdir / ".pyqual"
            pyqual_dir.mkdir()

            sarif_data = {
                "version": "2.1.0",
                "runs": [{
                    "tool": {
                        "driver": {
                            "name": "bandit",
                            "rules": [
                                {"id": "B105", "defaultConfiguration": {"level": "error"}},
                                {"id": "B301", "defaultConfiguration": {"level": "warning"}},
                            ]
                        }
                    },
                    "results": [
                        {"ruleId": "B105", "level": "error", "message": {"text": "Hardcoded password"}},
                        {"ruleId": "B301", "level": "warning", "message": {"text": "Pickle usage"}},
                        {"ruleId": "B301", "level": "warning", "message": {"text": "Another pickle"}},
                    ]
                }]
            }
            (pyqual_dir / "bandit.sarif").write_text(json.dumps(sarif_data))

            gate_set = GateSet([])
            metrics = gate_set._from_sarif(workdir)

            assert metrics["sarif_total"] == 3.0
            assert metrics["sarif_high"] == 1.0  # error
            assert metrics["sarif_medium"] == 2.0  # warning
            assert metrics["sarif_B105"] == 1.0
            assert metrics["sarif_B301"] == 2.0


class TestGateOperations:
    """Test gate checking logic."""

    def test_gate_check_passes(self):
        """Test gate passes when condition met."""
        config = GateConfig(metric="vuln_high", operator="le", threshold=0.0)
        gate = Gate(config)
        metrics = {"vuln_high": 0.0}
        result = gate.check(metrics)

        assert result.passed is True
        assert result.metric == "vuln_high"

    def test_gate_check_fails(self):
        """Test gate fails when condition not met."""
        config = GateConfig(metric="bandit_high", operator="le", threshold=0.0)
        gate = Gate(config)
        metrics = {"bandit_high": 2.0}
        result = gate.check(metrics)

        assert result.passed is False
        assert result.value == 2.0

    def test_gate_check_missing_metric(self):
        """Test gate fails when metric not found."""
        config = GateConfig(metric="secrets_found", operator="le", threshold=0.0)
        gate = Gate(config)
        metrics = {}  # No secrets_found metric
        result = gate.check(metrics)

        assert result.passed is False
        assert result.value is None

    def test_gate_all_operators(self):
        """Test all supported gate operators."""
        test_cases = [
            ("le", 5, 5, True),   # <=
            ("le", 6, 5, False),  # <=
            ("ge", 5, 5, True),   # >=
            ("ge", 4, 5, False),  # >=
            ("lt", 4, 5, True),   # <
            ("lt", 5, 5, False),  # <
            ("gt", 6, 5, True),   # >
            ("gt", 5, 5, False),  # >
            ("eq", 5, 5, True),   # =
            ("eq", 4, 5, False),  # =
        ]

        for op, value, threshold, expected in test_cases:
            config = GateConfig(metric="test", operator=op, threshold=float(threshold))
            gate = Gate(config)
            result = gate.check({"test": float(value)})
            assert result.passed == expected, f"Failed for operator {op} with {value} vs {threshold}"


class TestGateSet:
    """Test GateSet collection and checking."""

    def test_gateset_empty(self):
        """Test GateSet with no gates passes."""
        gate_set = GateSet([])
        with tempfile.TemporaryDirectory() as tmpdir:
            assert gate_set.all_passed(Path(tmpdir)) is True

    def test_gateset_all_pass(self):
        """Test GateSet when all gates pass."""
        configs = [
            GateConfig.from_dict("vuln_high_max", "0"),
            GateConfig.from_dict("bandit_high_max", "0"),
        ]
        gate_set = GateSet(configs)

        with tempfile.TemporaryDirectory() as tmpdir:
            workdir = Path(tmpdir)
            pyqual_dir = workdir / ".pyqual"
            pyqual_dir.mkdir()

            # Create empty security reports
            (pyqual_dir / "pip_audit.json").write_text(json.dumps({"vulnerabilities": []}))
            (pyqual_dir / "bandit.json").write_text(json.dumps({"results": []}))

            results = gate_set.check_all(workdir)
            assert all(r.passed for r in results)
