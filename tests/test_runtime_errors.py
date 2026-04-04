"""Tests for runtime error detection in pipelines."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from pyqual._gate_collectors import _from_runtime_errors
from pyqual.config import PyqualConfig, StageConfig
from pyqual.constants import RUNTIME_ERRORS_FILE
from pyqual.pipeline import Pipeline
from pyqual.pipeline_results import StageResult


class TestRuntimeErrorCollection:
    """Test runtime error capture and metrics collection."""

    def test_capture_runtime_error_creates_file(self) -> None:
        """Test that failed stages create runtime_errors.json."""
        with tempfile.TemporaryDirectory() as tmpdir:
            workdir = Path(tmpdir)
            
            # Create a minimal config
            config = PyqualConfig(
                name="test",
                stages=[],
                gates=[],
                loop=Mock(max_iterations=1),
            )
            
            pipeline = Pipeline(config, workdir=workdir)
            
            # Create a failed stage result
            stage = StageConfig(name="test_stage", run="false")
            result = StageResult(
                name="test_stage",
                returncode=1,
                original_returncode=1,
                stdout="",
                stderr="Test failed",
                duration=0.5,
                command="false",
            )
            
            # Capture the error
            pipeline._capture_runtime_error(stage, result)
            
            # Verify file was created
            errors_file = workdir / RUNTIME_ERRORS_FILE
            assert errors_file.exists()
            
            # Verify content
            errors = json.loads(errors_file.read_text())
            assert isinstance(errors, list)
            assert len(errors) == 1
            assert errors[0]["stage"] == "test_stage"
            assert errors[0]["command"] == "false"
            assert errors[0]["returncode"] == 1
            # Check that error_type is one of the expected values
            assert errors[0]["error_type"] in ["test_failed", "unknown"]

    def test_capture_multiple_errors(self) -> None:
        """Test that multiple errors are captured and limited to 100."""
        with tempfile.TemporaryDirectory() as tmpdir:
            workdir = Path(tmpdir)
            config = PyqualConfig(
                name="test",
                stages=[],
                gates=[],
                loop=Mock(max_iterations=1),
            )
            pipeline = Pipeline(config, workdir=workdir)
            
            # Create 105 errors
            for i in range(105):
                stage = StageConfig(name=f"stage_{i}", run="false")
                result = StageResult(
                    name=f"stage_{i}",
                    returncode=1,
                    original_returncode=1,
                    stdout="",
                    stderr=f"Error {i}",
                    duration=0.1,
                    command="false",
                )
                pipeline._capture_runtime_error(stage, result)
            
            # Verify only last 100 errors are kept
            errors_file = workdir / RUNTIME_ERRORS_FILE
            errors = json.loads(errors_file.read_text())
            assert len(errors) == 100
            assert errors[0]["stage"] == "stage_5"  # First 5 were dropped
            assert errors[-1]["stage"] == "stage_104"

    def test_error_classification(self) -> None:
        """Test error type classification."""
        with tempfile.TemporaryDirectory() as tmpdir:
            workdir = Path(tmpdir)
            config = PyqualConfig(
                name="test",
                stages=[],
                gates=[],
                loop=Mock(max_iterations=1),
            )
            pipeline = Pipeline(config, workdir=workdir)
            
            test_cases = [
                (124, "timeout", "timeout"),
                (127, "command not found", "command_not_found"),
                (126, "permission denied", "permission_denied"),
                (1, "ModuleNotFoundError: No module named 'x'", "import_error"),
                (1, "SyntaxError: invalid syntax", "syntax_error"),
                (1, "KeyError: 'missing_key'", "runtime_exception"),
                (1, "AssertionError: Test failed", "assertion_failed"),
                (1, "Unknown error occurred", "unknown"),
            ]
            
            for rc, stderr, expected_type in test_cases:
                stage = StageConfig(name="test", run="false")
                result = StageResult(
                    name="test",
                    returncode=rc,
                    original_returncode=rc,
                    stdout="",
                    stderr=stderr,
                    duration=0.1,
                    command="false",
                )
                
                error_type = pipeline._classify_error(result)
                assert error_type == expected_type, f"RC={rc}, stderr={stderr!r}"

    def test_extract_error_message(self) -> None:
        """Test error message extraction from stderr/stdout."""
        with tempfile.TemporaryDirectory() as tmpdir:
            workdir = Path(tmpdir)
            config = PyqualConfig(
                name="test",
                stages=[],
                gates=[],
                loop=Mock(max_iterations=1),
            )
            pipeline = Pipeline(config, workdir=workdir)
            
            # Test with traceback
            result = StageResult(
                name="test",
                returncode=1,
                original_returncode=1,
                stdout="",
                stderr="Traceback (most recent call last):\n  File test.py, line 10\nValueError: invalid value",
                duration=0.1,
                command="false",
            )
            
            message = pipeline._extract_error_message(result)
            # Should extract either the traceback line or the ValueError line
            assert "Traceback" in message or "ValueError" in message
            
            # Test with simple error
            result.stderr = "ERROR: Something went wrong"
            message = pipeline._extract_error_message(result)
            assert message == "ERROR: Something went wrong"
            
            # Test with empty stderr
            result.stderr = ""
            result.stdout = "Command output\nFinal line: error occurred"
            message = pipeline._extract_error_message(result)
            assert message == "Final line: error occurred"

    def test_runtime_errors_metric_collector(self) -> None:
        """Test the runtime errors metric collector."""
        with tempfile.TemporaryDirectory() as tmpdir:
            workdir = Path(tmpdir)
            pyqual_dir = workdir / ".pyqual"
            pyqual_dir.mkdir()
            
            # Create test runtime errors
            errors = [
                {
                    "timestamp": "2024-01-01T10:00:00+00:00",
                    "stage": "test",
                    "command": "pytest",
                    "tool": None,
                    "returncode": 1,
                    "duration_s": 1.0,
                    "error_type": "test_failed",
                    "message": "Test failed",
                    "stdout_tail": "",
                    "stderr_tail": "",
                },
                {
                    "timestamp": "2024-01-01T10:01:00+00:00",
                    "stage": "lint",
                    "command": "ruff",
                    "tool": "ruff",
                    "returncode": 1,
                    "duration_s": 0.5,
                    "error_type": "syntax_error",
                    "message": "Syntax error",
                    "stdout_tail": "",
                    "stderr_tail": "",
                },
                {
                    "timestamp": "2024-01-01T08:00:00+00:00",
                    "stage": "old",
                    "command": "old_cmd",
                    "tool": None,
                    "returncode": 1,
                    "duration_s": 1.0,
                    "error_type": "test_failed",
                    "message": "Old error",
                    "stdout_tail": "",
                    "stderr_tail": "",
                },
            ]
            
            (pyqual_dir / "runtime_errors.json").write_text(json.dumps(errors))
            
            # Test without mocking datetime - just check basic metrics work
            metrics = _from_runtime_errors(workdir)
            
            assert metrics["runtime_errors"] == 3.0
            assert metrics["runtime_test_failed"] == 2.0
            assert metrics["runtime_syntax_error"] == 1.0
            # runtime_errors_recent depends on current time, so just check it exists
            assert "runtime_errors_recent" in metrics

    def test_runtime_errors_integration_with_pipeline(self) -> None:
        """Test that runtime errors are captured during actual pipeline execution."""
        with tempfile.TemporaryDirectory() as tmpdir:
            workdir = Path(tmpdir)
            
            # Create a config with a failing stage
            config = PyqualConfig(
                name="test",
                stages=[
                    StageConfig(name="failing_stage", run="false")
                ],
                gates=[],
                loop=Mock(max_iterations=1),
            )
            
            pipeline = Pipeline(config, workdir=workdir)
            result = pipeline.run(dry_run=False)
            
            # Verify error was captured
            errors_file = workdir / RUNTIME_ERRORS_FILE
            assert errors_file.exists()
            
            errors = json.loads(errors_file.read_text())
            assert len(errors) == 1
            assert errors[0]["stage"] == "failing_stage"
            assert errors[0]["returncode"] == 1

    def test_no_error_capture_on_success(self) -> None:
        """Test that successful stages don't create runtime errors."""
        with tempfile.TemporaryDirectory() as tmpdir:
            workdir = Path(tmpdir)
            
            config = PyqualConfig(
                name="test",
                stages=[
                    StageConfig(name="success_stage", run="true")
                ],
                gates=[],
                loop=Mock(max_iterations=1),
            )
            
            pipeline = Pipeline(config, workdir=workdir)
            pipeline.run(dry_run=False)
            
            # Verify no errors file was created
            errors_file = workdir / RUNTIME_ERRORS_FILE
            assert not errors_file.exists()

    def test_optional_run_stage_failure_is_captured(self) -> None:
        """Optional run stages should not hide real command failures."""
        with tempfile.TemporaryDirectory() as tmpdir:
            workdir = Path(tmpdir)

            config = PyqualConfig(
                name="test",
                stages=[
                    StageConfig(name="publish", run="false", optional=True),
                ],
                gates=[],
                loop=Mock(max_iterations=1),
            )

            pipeline = Pipeline(config, workdir=workdir)
            result = pipeline.run(dry_run=False)

            stage_result = result.iterations[0].stages[0]
            assert stage_result.passed is False
            assert stage_result.original_returncode == 1

            errors_file = workdir / RUNTIME_ERRORS_FILE
            assert errors_file.exists()
            errors = json.loads(errors_file.read_text())
            assert len(errors) == 1
            assert errors[0]["stage"] == "publish"
            assert errors[0]["returncode"] == 1

    def test_no_error_capture_on_skipped(self) -> None:
        """Test that skipped stages don't create runtime errors."""
        with tempfile.TemporaryDirectory() as tmpdir:
            workdir = Path(tmpdir)
            
            config = PyqualConfig(
                name="test",
                stages=[
                    StageConfig(name="skipped_stage", run="nonexistent_cmd", optional=True)
                ],
                gates=[],
                loop=Mock(max_iterations=1),
            )
            
            pipeline = Pipeline(config, workdir=workdir)
            pipeline.run(dry_run=False)
            
            # Verify no errors file was created
            errors_file = workdir / RUNTIME_ERRORS_FILE
            assert not errors_file.exists()
