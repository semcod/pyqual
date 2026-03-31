#!/usr/bin/env python3
"""Flexible performance benchmark framework.

Can benchmark any Python library or CLI tool for:
- Startup / import time
- CLI command latency
- Unit test suite execution time
- Throughput (operations/second)
- Prefact-specific scan performance

Usage:
    python benchmark.py                   # run all suites
    python benchmark.py --suite startup   # only startup probes
    python benchmark.py --suite tests     # only test-time probes
    python benchmark.py --suite scan      # only scan probes
    python benchmark.py --json            # JSON output
    python benchmark.py --threshold 2.0   # fail if any probe > 2.0s
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
import textwrap
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

# ---------------------------------------------------------------------------
# Bootstrap – make sure src/ is importable
# ---------------------------------------------------------------------------
_ROOT = Path(__file__).parent
sys.path.insert(0, str(_ROOT / "src"))

try:
    from rich.console import Console
    from rich.table import Table
    from rich.panel import Panel
    from rich import box
    _RICH = True
except ImportError:
    _RICH = False


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------

@dataclass
class BenchmarkResult:
    name: str
    suite: str
    elapsed: float           # seconds
    unit: str = "s"
    extra: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None
    threshold: Optional[float] = None  # if set, result is marked FAIL when elapsed > threshold

    @property
    def passed(self) -> bool:
        if self.error:
            return False
        if self.threshold is not None:
            return self.elapsed <= self.threshold
        return True

    @property
    def status(self) -> str:
        if self.error:
            return "ERROR"
        if self.threshold is not None:
            return "PASS" if self.elapsed <= self.threshold else "FAIL"
        return "OK"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "suite": self.suite,
            "elapsed": round(self.elapsed, 4),
            "unit": self.unit,
            "status": self.status,
            "threshold": self.threshold,
            "extra": self.extra,
            "error": self.error,
        }


# ---------------------------------------------------------------------------
# Probe base
# ---------------------------------------------------------------------------

class BenchmarkProbe(ABC):
    """Abstract benchmark probe.  Override run() to implement custom probes."""

    suite: str = "custom"

    @abstractmethod
    def run(self) -> BenchmarkResult:
        ...


# ---------------------------------------------------------------------------
# Probe implementations
# ---------------------------------------------------------------------------

class ImportProbe(BenchmarkProbe):
    """Measures how long it takes to import a Python module in a fresh process.

    Works with *any* installed library, e.g.:
        ImportProbe("prefact")
        ImportProbe("requests")
        ImportProbe("django")
    """

    suite = "startup"

    def __init__(
        self,
        module: str,
        label: Optional[str] = None,
        threshold: Optional[float] = None,
        repeat: int = 3,
    ):
        self.module = module
        self.label = label or f"import {module}"
        self.threshold = threshold
        self.repeat = repeat

    def run(self) -> BenchmarkResult:
        times: List[float] = []
        error: Optional[str] = None

        for _ in range(self.repeat):
            cmd = [sys.executable, "-c", f"import {self.module}"]
            t0 = time.perf_counter()
            try:
                proc = subprocess.run(
                    cmd,
                    capture_output=True,
                    timeout=30,
                )
                elapsed = time.perf_counter() - t0
                if proc.returncode != 0:
                    error = proc.stderr.decode(errors="replace").strip()
                    break
                times.append(elapsed)
            except subprocess.TimeoutExpired:
                error = "timeout after 30s"
                break
            except Exception as e:
                error = str(e)
                break

        if error or not times:
            return BenchmarkResult(
                name=self.label, suite=self.suite,
                elapsed=0.0, error=error or "no measurements",
                threshold=self.threshold,
            )

        best = min(times)
        return BenchmarkResult(
            name=self.label,
            suite=self.suite,
            elapsed=best,
            threshold=self.threshold,
            extra={"repeat": self.repeat, "all_times": [round(t, 4) for t in times]},
        )


class CLIProbe(BenchmarkProbe):
    """Measures execution time of any shell command.

    Examples:
        CLIProbe(["prefact", "--help"])
        CLIProbe(["python", "-m", "pytest", "--collect-only"])
        CLIProbe(["ruff", "check", "."])
    """

    suite = "startup"

    def __init__(
        self,
        command: List[str],
        label: Optional[str] = None,
        cwd: Optional[Path] = None,
        threshold: Optional[float] = None,
        repeat: int = 3,
        env: Optional[Dict[str, str]] = None,
    ):
        self.command = command
        self.label = label or " ".join(command)
        self.cwd = cwd or _ROOT
        self.threshold = threshold
        self.repeat = repeat
        self.env = env

    def run(self) -> BenchmarkResult:
        times: List[float] = []
        error: Optional[str] = None
        env = {**os.environ, **(self.env or {})}

        for _ in range(self.repeat):
            t0 = time.perf_counter()
            try:
                proc = subprocess.run(
                    self.command,
                    capture_output=True,
                    cwd=self.cwd,
                    timeout=60,
                    env=env,
                )
                elapsed = time.perf_counter() - t0
                if proc.returncode not in (0, 1):
                    error = proc.stderr.decode(errors="replace").strip()[:200]
                    break
                times.append(elapsed)
            except FileNotFoundError:
                error = f"command not found: {self.command[0]}"
                break
            except subprocess.TimeoutExpired:
                error = "timeout after 60s"
                break
            except Exception as e:
                error = str(e)
                break

        if error or not times:
            return BenchmarkResult(
                name=self.label, suite=self.suite,
                elapsed=0.0, error=error or "no measurements",
                threshold=self.threshold,
            )

        best = min(times)
        return BenchmarkResult(
            name=self.label,
            suite=self.suite,
            elapsed=best,
            threshold=self.threshold,
            extra={"repeat": self.repeat, "all_times": [round(t, 4) for t in times]},
        )


class UnitTestProbe(BenchmarkProbe):
    """Runs a pytest test suite and measures total + per-file timing.

    Works with any project that has pytest tests.
    """

    suite = "tests"

    def __init__(
        self,
        test_path: Path,
        label: Optional[str] = None,
        pytest_args: Optional[List[str]] = None,
        threshold: Optional[float] = None,
        cwd: Optional[Path] = None,
    ):
        self.test_path = test_path
        self.label = label or f"pytest {test_path}"
        self.pytest_args = pytest_args or ["-q", "--tb=no", "--no-header"]
        self.threshold = threshold
        self.cwd = cwd or _ROOT

    def run(self) -> BenchmarkResult:
        cmd = [
            sys.executable, "-m", "pytest",
            str(self.test_path),
            "--tb=no",
            "--no-header",
            "-q",
            *self.pytest_args,
        ]

        t0 = time.perf_counter()
        try:
            proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                cwd=self.cwd,
                timeout=300,
            )
            elapsed = time.perf_counter() - t0
        except subprocess.TimeoutExpired:
            return BenchmarkResult(
                name=self.label, suite=self.suite,
                elapsed=0.0, error="timeout after 300s",
                threshold=self.threshold,
            )
        except Exception as e:
            return BenchmarkResult(
                name=self.label, suite=self.suite,
                elapsed=0.0, error=str(e),
                threshold=self.threshold,
            )

        # Parse output for test counts
        extra: Dict[str, Any] = {"returncode": proc.returncode}
        output = proc.stdout + proc.stderr
        for line in output.splitlines():
            if " passed" in line or " failed" in line or " error" in line:
                extra["summary"] = line.strip()
                break

        error = None
        if proc.returncode not in (0, 1, 5):  # 5 = no tests collected
            error = (proc.stderr or proc.stdout)[:300].strip()

        return BenchmarkResult(
            name=self.label,
            suite=self.suite,
            elapsed=elapsed,
            threshold=self.threshold,
            extra=extra,
            error=error,
        )


class ThroughputProbe(BenchmarkProbe):
    """Measures throughput of a callable (operations/second).

    Works with any function, e.g.:
        ThroughputProbe("parse JSON", lambda: json.loads(big_str), n=1000)
        ThroughputProbe("scan file",  lambda: scanner.scan_file(p, src), n=50)
    """

    suite = "throughput"

    def __init__(
        self,
        label: str,
        fn: Callable[[], Any],
        n: int = 100,
        setup: Optional[Callable[[], None]] = None,
        threshold_ops: Optional[float] = None,  # minimum ops/s to PASS
    ):
        self.label = label
        self.fn = fn
        self.n = n
        self.setup = setup
        self.threshold_ops = threshold_ops

    def run(self) -> BenchmarkResult:
        if self.setup:
            self.setup()

        error: Optional[str] = None
        try:
            t0 = time.perf_counter()
            for _ in range(self.n):
                self.fn()
            elapsed = time.perf_counter() - t0
        except Exception as e:
            return BenchmarkResult(
                name=self.label, suite=self.suite,
                elapsed=0.0, error=str(e),
            )

        ops_per_sec = self.n / elapsed if elapsed > 0 else float("inf")
        threshold = (self.n / self.threshold_ops) if self.threshold_ops else None

        return BenchmarkResult(
            name=self.label,
            suite=self.suite,
            elapsed=elapsed,
            threshold=threshold,
            extra={
                "n": self.n,
                "ops_per_sec": round(ops_per_sec, 1),
                "avg_ms": round(elapsed / self.n * 1000, 3),
            },
            error=error,
        )


class ScanProbe(BenchmarkProbe):
    """Prefact-specific: creates N temp Python files and measures scan throughput."""

    suite = "scan"

    def __init__(
        self,
        num_files: int = 100,
        file_size_kb: int = 1,
        label: Optional[str] = None,
        threshold: Optional[float] = None,
    ):
        self.num_files = num_files
        self.file_size_kb = file_size_kb
        self.label = label or f"scan {num_files}×{file_size_kb}KB"
        self.threshold = threshold

    def run(self) -> BenchmarkResult:
        try:
            from prefact.config import Config
            from prefact.engine import RefactoringEngine
        except ImportError as e:
            return BenchmarkResult(
                name=self.label, suite=self.suite,
                elapsed=0.0, error=f"prefact not importable: {e}",
                threshold=self.threshold,
            )

        template = textwrap.dedent("""\
            \"\"\"Module {i}.\"\"\"
            from ....module{mod} import func{fn}
            from os import path
            from os import path
            import sys

            def run():
                return "ok"
        """)

        with tempfile.TemporaryDirectory() as tmpdir:
            base = Path(tmpdir)

            for i in range(self.num_files):
                content = template.format(i=i, mod=i % 10, fn=i % 5)
                if self.file_size_kb > 1:
                    pad = "x" * (self.file_size_kb * 1024 - len(content))
                    content += f"\n# {pad}\n"
                (base / f"m{i:04d}.py").write_text(content, encoding="utf-8")

            config = Config(
                project_root=base,
                package_name="bench",
                dry_run=True,
                verbose=False,
            )
            engine = RefactoringEngine(config)

            t0 = time.perf_counter()
            result = engine.run(dry_run=True)
            elapsed = time.perf_counter() - t0

        files_per_sec = self.num_files / elapsed if elapsed > 0 else 0.0
        return BenchmarkResult(
            name=self.label,
            suite=self.suite,
            elapsed=elapsed,
            threshold=self.threshold,
            extra={
                "files": self.num_files,
                "issues_found": len(result.issues_found),
                "fixes_applied": len(result.fixes_applied),
                "files_per_sec": round(files_per_sec, 1),
            },
        )


# ---------------------------------------------------------------------------
# Suite builder
# ---------------------------------------------------------------------------

class BenchmarkSuite:
    """Collects probes and runs them, returning aggregated results."""

    def __init__(self, name: str = "benchmark"):
        self.name = name
        self._probes: List[BenchmarkProbe] = []

    def add(self, probe: BenchmarkProbe) -> "BenchmarkSuite":
        self._probes.append(probe)
        return self

    def run(self, suite_filter: Optional[str] = None) -> List[BenchmarkResult]:
        probes = self._probes
        if suite_filter:
            probes = [p for p in probes if p.suite == suite_filter]

        results: List[BenchmarkResult] = []
        for probe in probes:
            result = probe.run()
            results.append(result)
        return results


# ---------------------------------------------------------------------------
# Reporter
# ---------------------------------------------------------------------------

def _fmt_time(s: float) -> str:
    if s < 0.001:
        return f"{s*1000:.2f} ms"
    if s < 1.0:
        return f"{s*1000:.1f} ms"
    return f"{s:.3f}  s"


class BenchmarkReporter:
    """Prints results as a rich table or plain text."""

    def __init__(self, results: List[BenchmarkResult]):
        self.results = results

    def print_rich(self) -> None:
        console = Console()
        console.print()
        console.print(Panel.fit("[bold cyan]Performance Benchmark Report[/bold cyan]"))

        # Group by suite
        suites: Dict[str, List[BenchmarkResult]] = {}
        for r in self.results:
            suites.setdefault(r.suite, []).append(r)

        for suite_name, suite_results in suites.items():
            table = Table(
                title=f"[bold]{suite_name.upper()}[/bold]",
                box=box.SIMPLE_HEAVY,
                show_header=True,
                header_style="bold magenta",
            )
            table.add_column("Probe", style="cyan", min_width=30)
            table.add_column("Time", justify="right", min_width=12)
            table.add_column("Threshold", justify="right", min_width=12)
            table.add_column("Status", justify="center", min_width=8)
            table.add_column("Details", style="dim")

            for r in suite_results:
                status_color = {
                    "OK": "green", "PASS": "green",
                    "FAIL": "red", "ERROR": "bold red",
                }.get(r.status, "white")

                details = ""
                if r.extra:
                    parts = []
                    if "ops_per_sec" in r.extra:
                        parts.append(f"{r.extra['ops_per_sec']} ops/s")
                    if "files_per_sec" in r.extra:
                        parts.append(f"{r.extra['files_per_sec']} files/s")
                    if "summary" in r.extra:
                        parts.append(r.extra["summary"])
                    if r.error:
                        parts.append(f"[red]{r.error[:60]}[/red]")
                    details = "  ".join(parts)
                elif r.error:
                    details = f"[red]{r.error[:80]}[/red]"

                table.add_row(
                    r.name,
                    _fmt_time(r.elapsed) if not r.error else "—",
                    _fmt_time(r.threshold) if r.threshold else "—",
                    f"[{status_color}]{r.status}[/{status_color}]",
                    details,
                )

            console.print(table)

        # Summary
        total = len(self.results)
        passed = sum(1 for r in self.results if r.status in ("OK", "PASS"))
        failed = sum(1 for r in self.results if r.status == "FAIL")
        errors = sum(1 for r in self.results if r.status == "ERROR")
        console.print(
            f"[bold]Total:[/bold] {total}  "
            f"[green]OK/PASS: {passed}[/green]  "
            f"[red]FAIL: {failed}[/red]  "
            f"[bold red]ERROR: {errors}[/bold red]"
        )
        console.print()

    def print_plain(self) -> None:
        suites: Dict[str, List[BenchmarkResult]] = {}
        for r in self.results:
            suites.setdefault(r.suite, []).append(r)

        for suite_name, suite_results in suites.items():
            print(f"\n{'='*60}")
            print(f"  {suite_name.upper()}")
            print(f"{'='*60}")
            print(f"  {'Probe':<35} {'Time':>10}  {'Status':>8}")
            print(f"  {'-'*57}")
            for r in suite_results:
                t = _fmt_time(r.elapsed) if not r.error else "—"
                print(f"  {r.name:<35} {t:>10}  {r.status:>8}")
                if r.extra.get("summary"):
                    print(f"    → {r.extra['summary']}")
                if r.error:
                    print(f"    ! {r.error[:80]}")

    def print_json(self) -> None:
        print(json.dumps([r.to_dict() for r in self.results], indent=2))

    def print(self, fmt: str = "auto") -> None:
        if fmt == "json":
            self.print_json()
        elif fmt == "plain" or not _RICH:
            self.print_plain()
        else:
            self.print_rich()

    def any_failed(self) -> bool:
        return any(r.status in ("FAIL", "ERROR") for r in self.results)


# ---------------------------------------------------------------------------
# Default prefact benchmark suite
# ---------------------------------------------------------------------------

def build_prefact_suite() -> BenchmarkSuite:
    suite = BenchmarkSuite("prefact")

    # ── Startup / import ────────────────────────────────────────────────────
    suite.add(ImportProbe("prefact", threshold=2.0))
    suite.add(ImportProbe("prefact.engine", threshold=2.0))
    suite.add(ImportProbe("prefact.rules", threshold=2.0))

    suite.add(CLIProbe(
        [sys.executable, "-m", "prefact", "--help"],
        label="prefact --help",
        threshold=3.0,
    ))
    suite.add(CLIProbe(
        [sys.executable, "-m", "prefact", "scan", "--help"],
        label="prefact scan --help",
        threshold=3.0,
    ))

    # ── Unit tests ───────────────────────────────────────────────────────────
    tests_dir = _ROOT / "tests"
    if tests_dir.exists():
        suite.add(UnitTestProbe(
            tests_dir,
            label="full test suite",
            threshold=30.0,
        ))
        for test_file in sorted(tests_dir.glob("test_*.py")):
            suite.add(UnitTestProbe(
                test_file,
                label=f"pytest {test_file.name}",
                threshold=15.0,
            ))

    # ── Scan throughput ──────────────────────────────────────────────────────
    suite.add(ScanProbe(num_files=50,   file_size_kb=1,  threshold=10.0))
    suite.add(ScanProbe(num_files=100,  file_size_kb=1,  threshold=20.0))
    suite.add(ScanProbe(num_files=200,  file_size_kb=5,  threshold=40.0))

    # ── In-process throughput ────────────────────────────────────────────────
    suite.add(_make_inprocess_probe())

    return suite


def _make_inprocess_probe() -> ThroughputProbe:
    """Benchmark scanner in-process with pre-built files."""
    import tempfile, textwrap as tw

    _state: Dict[str, Any] = {}

    def setup() -> None:
        from prefact.config import Config
        from prefact.scanner import Scanner

        tmpdir = tempfile.mkdtemp()
        base = Path(tmpdir)
        src = tw.dedent("""\
            from ..utils import helper
            from os import path
            from os import path
            import sys
            def run(): return 1
        """)
        files = []
        for i in range(20):
            p = base / f"m{i}.py"
            p.write_text(src, encoding="utf-8")
            files.append(p)

        config = Config(project_root=base, package_name="bench", dry_run=True, verbose=False)
        scanner = Scanner(config)
        _state["scanner"] = scanner
        _state["files"] = files
        _state["base"] = base

    def fn() -> None:
        scanner = _state["scanner"]
        files = _state["files"]
        scanner.scan(files)

    return ThroughputProbe(
        label="scanner.scan (20 files, in-process)",
        fn=fn,
        n=10,
        setup=setup,
        threshold_ops=0.5,  # at least 0.5 full scans per second
    )


# ---------------------------------------------------------------------------
# Generic helper: benchmark any library
# ---------------------------------------------------------------------------

def benchmark_library(
    module: str,
    cli_commands: Optional[List[List[str]]] = None,
    test_path: Optional[Path] = None,
    threshold_import: float = 3.0,
    threshold_cli: float = 5.0,
    threshold_tests: float = 60.0,
) -> BenchmarkSuite:
    """Generic helper to benchmark *any* installed Python library.

    Example:
        results = benchmark_library(
            module="requests",
            cli_commands=[["python", "-c", "import requests; print(requests.__version__)"]],
        ).run()
    """
    suite = BenchmarkSuite(f"library:{module}")
    suite.add(ImportProbe(module, threshold=threshold_import))

    for cmd in (cli_commands or []):
        suite.add(CLIProbe(cmd, threshold=threshold_cli))

    if test_path and test_path.exists():
        suite.add(UnitTestProbe(test_path, threshold=threshold_tests))

    return suite


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(
        description="Flexible performance benchmark for prefact (and any Python library)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=textwrap.dedent("""\
            Examples:
              python benchmark.py                    # all suites
              python benchmark.py --suite startup    # import + CLI probes only
              python benchmark.py --suite tests      # unit test probes only
              python benchmark.py --suite scan       # scan throughput probes
              python benchmark.py --suite throughput # in-process throughput
              python benchmark.py --json             # JSON output
        """),
    )
    parser.add_argument(
        "--suite",
        choices=["startup", "tests", "scan", "throughput"],
        default=None,
        help="Run only probes from this suite (default: all)",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output results as JSON",
    )
    parser.add_argument(
        "--plain",
        action="store_true",
        help="Plain text output (no colours)",
    )
    parser.add_argument(
        "--threshold",
        type=float,
        default=None,
        metavar="SEC",
        help="Override all time thresholds with this value (seconds)",
    )
    args = parser.parse_args()

    suite = build_prefact_suite()

    results = suite.run(suite_filter=args.suite)

    # Global threshold override
    if args.threshold is not None:
        for r in results:
            if r.unit == "s":
                r.threshold = args.threshold

    fmt = "json" if args.json else ("plain" if args.plain else "auto")
    reporter = BenchmarkReporter(results)
    reporter.print(fmt=fmt)

    return 1 if reporter.any_failed() else 0


if __name__ == "__main__":
    sys.exit(main())
