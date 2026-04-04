"""Example: Integrating pyqual into prollama.

This file demonstrates how to use pyqual's public API from external projects.
Save this as prollama/quality.py or similar.
"""

# Option 1: Simple high-level API usage
from pyqual import run_pipeline

def run_quality_check(config_path: str = "pyqual.yaml", workdir: str = ".") -> bool:
    """Run pyqual quality pipeline and return True if all gates pass."""
    result = run_pipeline(config_path, workdir=workdir)
    return result.final_passed


# Option 2: Using the api module for more control
from pyqual import api

def run_with_callbacks(workdir: str = ".") -> bool:
    """Run pipeline with progress callbacks."""
    config = api.load_config("pyqual.yaml", workdir)
    
    def on_stage_start(name: str):
        print(f"[STAGE START] {name}")
    
    def on_stage_done(result):
        status = "✓" if result.passed else "✗"
        print(f"[STAGE DONE] {status} {result.name} ({result.duration:.1f}s)")
    
    result = api.run(
        config,
        workdir=workdir,
        on_stage_start=on_stage_start,
        on_stage_done=on_stage_done,
    )
    
    # Export results for CI/CD
    api.export_results_json(result, f"{workdir}/.pyqual/results.json")
    return result.final_passed


# Option 3: Shell helpers for quick checks
from pyqual import shell, shell_check

def check_prerequisites() -> dict[str, bool]:
    """Check if required tools are available."""
    checks = {
        "python": shell_check("which python3"),
        "git": shell_check("which git"),
        "docker": shell_check("which docker"),
    }
    return checks


def run_shell_command_example() -> None:
    """Run a shell command through pyqual's shell helper."""
    # Run and capture output
    result = shell.run("git status --short", cwd=".")
    if result.returncode == 0:
        print("Git status:", result.stdout)
    
    # Quick check
    if shell_check("git diff --quiet"):
        print("No uncommitted changes")
    else:
        print("There are uncommitted changes")
    
    # Get output directly
    branch = shell.output("git branch --show-current", cwd=".")
    print(f"Current branch: {branch.strip()}")


# Option 4: Run individual stages
# Timeout and output limits
STAGE_TIMEOUT_SECONDS = 300
MAX_ERROR_OUTPUT_CHARS = 500


def run_single_stage(stage_name: str, tool: str, workdir: str = ".") -> bool:
    """Run a single stage without full pipeline."""
    result = api.run_stage(
        stage_name=stage_name,
        tool=tool,
        workdir=workdir,
        timeout=STAGE_TIMEOUT_SECONDS,
    )
    
    print(f"Stage: {result['name']}")
    print(f"Passed: {result['passed']}")
    print(f"Duration: {result['duration']}s")
    
    if not result['passed']:
        print(f"Error: {result['stderr'][:MAX_ERROR_OUTPUT_CHARS]}")
    
    return result['passed']


# Option 5: Dry-run to preview what would happen
def preview_pipeline(config_path: str = "pyqual.yaml"):
    """Preview pipeline execution without running anything."""
    result = api.dry_run(config_path)
    
    print(api.format_result_summary(result))
    
    for iteration in result.iterations:
        for stage in iteration.stages:
            print(f"  Would run: {stage.name}")
            if stage.command:
                print(f"    Command: {stage.command}")


# Option 6: Check gates without running pipeline
def quick_gate_check(workdir: str = "."):
    """Check if current code passes quality gates."""
    config = api.load_config("pyqual.yaml", workdir)
    gates = api.check_gates(config, workdir)
    
    all_passed = True
    for gate in gates:
        status = "✓" if gate.passed else "✗"
        print(f"{status} {gate.metric}: {gate.value} {gate.operator} {gate.threshold}")
        if not gate.passed:
            all_passed = False
    
    return all_passed


if __name__ == "__main__":
    # Example usage
    print("=== Checking prerequisites ===")
    prereqs = check_prerequisites()
    for tool, available in prereqs.items():
        print(f"  {tool}: {'✓' if available else '✗'}")
    
    print("\n=== Quick gate check ===")
    gates_ok = quick_gate_check(".")
    
    if gates_ok:
        print("\n✓ All quality gates passed!")
    else:
        print("\n✗ Some quality gates failed - running full pipeline...")
        # success = run_quality_check()
