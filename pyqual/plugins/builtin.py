"""Built-in metric collector plugins for pyqual."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from pyqual.constants import (
    DEFAULT_MCP_PORT,
    PYQUAL_DIR,
)
from pyqual.plugins._base import MetricCollector, PluginMetadata, PluginRegistry


# =============================================================================
# LLM & AI Benchmarking Collectors
# =============================================================================

@PluginRegistry.register
class LLMBenchCollector(MetricCollector):
    """LLM code generation quality metrics from human-eval and CodeBLEU."""

    name = "llm-bench"
    metadata = PluginMetadata(
        name="llm-bench",
        description="LLM code generation quality (pass@1, CodeBLEU, AI-generated %)",
        version="1.0.0",
        tags=["llm", "benchmark", "code-quality"],
        config_example="""
metrics:
  pass_at_1_min: 80        # % test cases passed (human-eval)
  code_bleu_min: 0.7      # BLEU score vs reference
  ai_generated_pct_max: 20 # % kodu AI-generated

stages:
  - name: llm_bench
    run: human-eval --code-dir . --json > .pyqual/humaneval.json
""",
    )

    def collect(self, workdir: Path) -> dict[str, float]:
        result: dict[str, float] = {}
        humaneval_path = workdir / ".pyqual" / "humaneval.json"
        if humaneval_path.exists():
            try:
                data = json.loads(humaneval_path.read_text())
                pass_at_1 = data.get("pass_at_1") or data.get("pass@1")
                if pass_at_1:
                    result["pass_at_1"] = float(pass_at_1)
                pass_at_k = data.get("pass_at_k") or data.get("pass@k")
                if pass_at_k:
                    result["pass_at_k"] = float(pass_at_k)
            except (json.JSONDecodeError, TypeError):
                pass
        codebleu_path = workdir / ".pyqual" / "codebleu.json"
        if codebleu_path.exists():
            try:
                data = json.loads(codebleu_path.read_text())
                codebleu = data.get("codebleu") or data.get("score")
                if codebleu:
                    result["code_bleu"] = float(codebleu)
                ai_pct = data.get("ai_generated_pct") or data.get("ai_percentage")
                if ai_pct:
                    result["ai_generated_pct"] = float(ai_pct)
            except (json.JSONDecodeError, TypeError):
                pass
        return result


@PluginRegistry.register
class HallucinationCollector(MetricCollector):
    """Hallucination detection and prompt quality metrics."""

    name = "hallucination"
    metadata = PluginMetadata(
        name="hallucination",
        description="Detect hallucinations in LLM outputs, measure prompt efficiency",
        version="1.0.0",
        tags=["llm", "rag", "hallucination", "quality"],
        config_example="""
metrics:
  hallucination_rate_max: 1     # % hallucinated comments
  prompt_token_efficiency_max: 80 # token usage vs baseline
  faithfulness_score_min: 0.9   # cosine similarity context-response

stages:
  - name: hallucination_check
    run: |
      python -c "from sentence_transformers import SentenceTransformer; 
      model = SentenceTransformer('all-MiniLM-L6-v2'); 
      sim = model.encode(['context', 'response']); 
      print(float(sim[0].dot(sim[1])))" > .pyqual/hall.json
""",
    )

    def collect(self, workdir: Path) -> dict[str, float]:
        result: dict[str, float] = {}
        hall_path = workdir / ".pyqual" / "hall.json"
        if hall_path.exists():
            try:
                data = json.loads(hall_path.read_text())
                faith = data.get("faithfulness") or data.get("faithfulness_score")
                if faith:
                    result["faithfulness_score"] = float(faith)
                hall_rate = data.get("hallucination_rate") or data.get("hallucination_pct")
                if hall_rate:
                    result["hallucination_rate"] = float(hall_rate)
                token_eff = data.get("token_efficiency") or data.get("prompt_token_efficiency")
                if token_eff:
                    result["prompt_token_efficiency"] = float(token_eff)
                cos_sim = data.get("cosine_similarity") or data.get("similarity")
                if cos_sim:
                    result["context_response_sim"] = float(cos_sim)
            except (json.JSONDecodeError, TypeError):
                pass
        return result


# =============================================================================
# Compliance & Supply Chain Collectors
# =============================================================================

@PluginRegistry.register
class SBOMCollector(MetricCollector):
    """SBOM compliance and supply chain security metrics."""

    name = "sbom"
    metadata = PluginMetadata(
        name="sbom",
        description="SBOM completeness, license compliance, supply chain vulnerabilities",
        version="1.0.0",
        tags=["security", "compliance", "supply-chain"],
        config_example="""
metrics:
  sbom_coverage_min: 100    # % deps in SBOM
  vuln_supply_chain_max: 0  # supply chain vulns

stages:
  - name: sbom_validate
    run: sbom4python --requirements-file requirements.txt --json > .pyqual/sbom.json
""",
    )

    def collect(self, workdir: Path) -> dict[str, float]:
        result: dict[str, float] = {}
        sbom_path = workdir / ".pyqual" / "sbom.json"
        if sbom_path.exists():
            try:
                data = json.loads(sbom_path.read_text())
                comps = data.get("components", [])
                total = len(comps)
                licensed = sum(1 for c in comps if c.get("licenses"))
                if total > 0:
                    result["sbom_coverage"] = (licensed / total) * 100
                vuln_supply = data.get("vulnerabilities", [])
                result["vuln_supply_chain"] = float(len(vuln_supply))
            except (json.JSONDecodeError, TypeError):
                pass
        return result


# =============================================================================
# Internationalization & Accessibility Collectors
# =============================================================================

@PluginRegistry.register
class I18nCollector(MetricCollector):
    """Internationalization coverage metrics."""

    name = "i18n"
    metadata = PluginMetadata(
        name="i18n",
        description="i18n coverage, missing translations for gettext/flask-babel",
        version="1.0.0",
        tags=["i18n", "l10n", "accessibility"],
        config_example="""
metrics:
  i18n_coverage_min: 95  # % strings internationalized

stages:
  - name: i18n_check
    run: i18n-check . --json > .pyqual/i18n.json
""",
    )

    def collect(self, workdir: Path) -> dict[str, float]:
        result: dict[str, float] = {}
        i18n_path = workdir / ".pyqual" / "i18n.json"
        if i18n_path.exists():
            try:
                data = json.loads(i18n_path.read_text())
                coverage = data.get("coverage") or data.get("i18n_coverage")
                if coverage:
                    result["i18n_coverage"] = float(coverage)
                missing = data.get("missing_keys") or data.get("untranslated")
                if missing:
                    result["i18n_missing"] = float(missing)
            except (json.JSONDecodeError, TypeError):
                pass
        return result


@PluginRegistry.register
class A11yCollector(MetricCollector):
    """Accessibility (a11y) compliance metrics."""

    name = "a11y"
    metadata = PluginMetadata(
        name="a11y",
        description="Accessibility violations for web/UI Python frameworks",
        version="1.0.0",
        tags=["accessibility", "a11y", "web", "ui"],
        config_example="""
metrics:
  a11y_issues_max: 0  # accessibility violations

stages:
  - name: a11y_check
    run: axe-core . --json > .pyqual/a11y.json  # or pa11y
""",
    )

    def collect(self, workdir: Path) -> dict[str, float]:
        result: dict[str, float] = {}
        a11y_path = workdir / ".pyqual" / "a11y.json"
        if a11y_path.exists():
            try:
                data = json.loads(a11y_path.read_text())
                violations = data.get("violations", [])
                result["a11y_issues"] = float(len(violations))
                critical = sum(1 for v in violations if v.get("impact") == "critical")
                result["a11y_critical"] = float(critical)
            except (json.JSONDecodeError, TypeError):
                pass
        return result


# =============================================================================
# Repository Health Collectors
# =============================================================================

@PluginRegistry.register
class RepoMetricsCollector(MetricCollector):
    """Advanced repository health metrics (bus factor, diversity)."""

    name = "repo-metrics"
    metadata = PluginMetadata(
        name="repo-metrics",
        description="Bus factor, commit frequency, contributor diversity via grimoirelab",
        version="1.0.0",
        tags=["repository", "git", "health", "analytics"],
        config_example="""
metrics:
  bus_factor_min: 3              # min committerów core
  commit_frequency_min: 5        # commits/tydzień
  contributor_diversity_min: 0.7 # Gini index

stages:
  - name: repo_health
    run: git log --shortstat | python analyze_commits.py > .pyqual/repo_health.json
""",
    )

    def collect(self, workdir: Path) -> dict[str, float]:
        result: dict[str, float] = {}
        for fname in ["repo_health.json", "grimoirelab.json", "git_stats.json"]:
            path = workdir / ".pyqual" / fname
            if path.exists():
                try:
                    data = json.loads(path.read_text())
                    bus = data.get("bus_factor") or data.get("core_developers")
                    if bus:
                        result["bus_factor"] = float(bus)
                    freq = data.get("commit_frequency") or data.get("commits_per_week")
                    if freq:
                        result["commit_frequency"] = float(freq)
                    diversity = data.get("contributor_diversity") or data.get("diversity_index")
                    if diversity:
                        result["contributor_diversity"] = float(diversity)
                except (json.JSONDecodeError, TypeError):
                    pass
        return result


# =============================================================================
# MCP/LLM Fix Workflow Collectors
# =============================================================================

@PluginRegistry.register
class LlxMcpFixCollector(MetricCollector):
    """Dockerized llx MCP fix/refactor workflow results."""

    name = "llx-mcp-fixer"
    metadata = PluginMetadata(
        name="llx-mcp-fixer",
        description="MCP-backed auto-fix/refactor workflow powered by llx and Aider in Docker",
        version="1.0.0",
        tags=["mcp", "docker", "llx", "llm", "fix", "refactor"],
        config_example=f"""
metrics:
  llx_fix_success_min: 1
  llx_fix_returncode_eq: 0
  llx_tool_calls_min: 2

stages:
  - name: llx_mcp_fix
    run: pyqual mcp-fix --workdir . --project-path /workspace/project --issues .pyqual/errors.json --output .pyqual/llx_mcp.json
    when: metrics_fail
    timeout: 900

env:
  PYQUAL_LLX_MCP_URL: http://localhost:{DEFAULT_MCP_PORT}/sse
  PYQUAL_LLX_PROJECT_PATH: /workspace/project
  PYQUAL_LLX_USE_DOCKER: "false"
""".strip(),
    )

    @staticmethod
    def _tier_rank(tier: str | None) -> float | None:
        if not tier:
            return None
        ranks = {"free": 1.0, "cheap": 2.0, "balanced": 3.0, "premium": 4.0}
        return ranks.get(tier.lower())

    @staticmethod
    def _load_report(path: Path) -> dict[str, Any] | None:
        try:
            data = json.loads(path.read_text())
        except (json.JSONDecodeError, OSError):
            return None
        return data if isinstance(data, dict) else None

    @staticmethod
    def _assign_float(result: dict[str, float], key: str, value: Any) -> None:
        if value is None:
            return
        try:
            result[key] = float(value)
        except (TypeError, ValueError):
            pass

    @staticmethod
    def _count_lines(value: Any) -> float | None:
        if not isinstance(value, str):
            return None
        return float(sum(1 for line in value.splitlines() if line.strip()))

    def _collect_analysis_metrics(self, result: dict[str, float], analysis: Any) -> None:
        if not isinstance(analysis, dict):
            return
        metrics = analysis.get("metrics")
        if isinstance(metrics, dict):
            self._assign_float(result, "llx_project_files", metrics.get("total_files"))
            self._assign_float(result, "llx_avg_cc", metrics.get("avg_cc"))
        selection = analysis.get("selection")
        if isinstance(selection, dict):
            tier_rank = self._tier_rank(selection.get("tier"))
            if tier_rank is not None:
                result["llx_fix_tier_rank"] = tier_rank

    def _collect_aider_metrics(self, result: dict[str, float], aider: Any) -> None:
        if not isinstance(aider, dict):
            return
        returncode = aider.get("returncode")
        if returncode is None and aider.get("success") is not None:
            returncode = 0 if bool(aider.get("success")) else 1
        self._assign_float(result, "llx_fix_returncode", returncode)
        method = aider.get("method")
        if method == "docker":
            result["llx_fix_uses_docker"] = 1.0
        elif method == "local":
            result["llx_fix_uses_docker"] = 0.0
        stdout_lines = self._count_lines(aider.get("stdout"))
        if stdout_lines is not None:
            result["llx_stdout_lines"] = stdout_lines
        stderr_lines = self._count_lines(aider.get("stderr"))
        if stderr_lines is not None:
            result["llx_stderr_lines"] = stderr_lines

    def get_config_example(self) -> str:
        """Return a ready-to-use YAML snippet for the llx MCP fixer pipeline."""
        return self.metadata.config_example

    def collect(self, workdir: Path) -> dict[str, float]:
        result: dict[str, float] = {}
        fix_path = workdir / ".pyqual" / "llx_mcp.json"
        if not fix_path.exists():
            return result
        data = self._load_report(fix_path)
        if data is None:
            return result
        success = data.get("success")
        if success is not None:
            result["llx_fix_success"] = 1.0 if bool(success) else 0.0
        self._assign_float(result, "llx_tool_calls", data.get("tool_calls"))
        self._collect_analysis_metrics(result, data.get("analysis"))
        self._collect_aider_metrics(result, data.get("aider"))
        return result
