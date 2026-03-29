"""Plugin system for pyqual - extensible metric collectors."""

from __future__ import annotations

import json
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Any, ClassVar, Type


@dataclass
class PluginMetadata:
    """Metadata for a pyqual plugin."""
    name: str
    description: str
    version: str
    author: str = ""
    tags: list[str] = None
    config_example: str = ""

    def __post_init__(self):
        if self.tags is None:
            self.tags = []


class MetricCollector(ABC):
    """Base class for metric collector plugins.
    
    Subclasses should implement collect() to extract metrics from JSON artifacts
    in the .pyqual/ directory.
    
    Example:
        class HumanEvalCollector(MetricCollector):
            name = "llm-bench"
            
            def collect(self, workdir: Path) -> dict[str, float]:
                result = {}
                path = workdir / ".pyqual" / "humaneval.json"
                if path.exists():
                    data = json.loads(path.read_text())
                    if "pass_at_1" in data:
                        result["pass_at_1"] = float(data["pass_at_1"])
                return result
    """
    
    name: ClassVar[str] = ""
    metadata: ClassVar[PluginMetadata] = PluginMetadata(
        name="",
        description="",
        version="0.1.0"
    )
    
    @abstractmethod
    def collect(self, workdir: Path) -> dict[str, float]:
        """Collect metrics from workdir/.pyqual/ artifacts.
        
        Args:
            workdir: Project working directory containing .pyqual/ folder
            
        Returns:
            Dictionary of metric_name -> value
        """
        ...
    
    def get_config_example(self) -> str:
        """Return example YAML configuration for this plugin."""
        return f"""\
# {self.metadata.name} plugin configuration
pipeline:
  metrics:
    {self.name}_min: 0.8
  stages:
    - name: {self.name}_check
      run: echo "Run your tool here > .pyqual/output.json"
"""


class PluginRegistry:
    """Registry for metric collector plugins."""
    
    _plugins: dict[str, Type[MetricCollector]] = {}
    
    @classmethod
    def register(cls, plugin_class: Type[MetricCollector]) -> Type[MetricCollector]:
        """Register a plugin class. Can be used as a decorator.
        
        Example:
            @PluginRegistry.register
            class MyCollector(MetricCollector):
                name = "my-collector"
        """
        cls._plugins[plugin_class.name] = plugin_class
        return plugin_class
    
    @classmethod
    def get(cls, name: str) -> Type[MetricCollector] | None:
        """Get a plugin class by name."""
        return cls._plugins.get(name)
    
    @classmethod
    def list_plugins(cls, tag: str | None = None) -> list[Type[MetricCollector]]:
        """List all registered plugins, optionally filtered by tag."""
        plugins = list(cls._plugins.values())
        if tag:
            plugins = [p for p in plugins if tag in (p.metadata.tags or [])]
        return plugins
    
    @classmethod
    def create_instance(cls, name: str) -> MetricCollector | None:
        """Create an instance of a registered plugin."""
        plugin_class = cls._plugins.get(name)
        if plugin_class:
            return plugin_class()
        return None


# Predefined built-in plugins

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
"""
    )
    
    def collect(self, workdir: Path) -> dict[str, float]:
        result: dict[str, float] = {}
        # Parse humaneval.json
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
        # Parse codebleu.json
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
"""
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
"""
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
"""
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
"""
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
"""
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


@PluginRegistry.register
class SecurityCollector(MetricCollector):
    """Security scanning metrics from trufflehog, gitleaks, safety."""
    
    name = "security"
    metadata = PluginMetadata(
        name="security",
        description="Secrets scanning, vulnerability detection, license compliance",
        version="1.0.0",
        tags=["security", "secrets", "vulnerabilities", "compliance"],
        config_example="""
metrics:
  secrets_found_max: 0
  vuln_critical_max: 0
  license_blacklist_max: 0

stages:
  - name: security_scan
    run: |
      trufflehog filesystem . --json > .pyqual/trufflehog.json
      safety check --json > .pyqual/safety.json
"""
    )
    
    def collect(self, workdir: Path) -> dict[str, float]:
        result: dict[str, float] = {}
        # Parse secrets scans
        for fname in ["trufflehog.json", "gitleaks.json", "secrets.json"]:
            path = workdir / ".pyqual" / fname
            if path.exists():
                try:
                    data = json.loads(path.read_text())
                    if isinstance(data, list):
                        result["secrets_found"] = float(len(data))
                    elif isinstance(data, dict):
                        count = len(data.get("findings", data.get("results", [])))
                        result["secrets_found"] = float(count)
                except (json.JSONDecodeError, TypeError):
                    pass
        # Parse vulnerability scans
        for fname in ["safety.json", "pip_audit.json"]:
            path = workdir / ".pyqual" / fname
            if path.exists():
                try:
                    data = json.loads(path.read_text())
                    if isinstance(data, dict) and "vulnerabilities" in data:
                        vulns = data["vulnerabilities"]
                    elif isinstance(data, list):
                        vulns = data
                    else:
                        continue
                    critical = sum(1 for v in vulns if "critical" in str(v.get("severity", "")).lower())
                    result["vuln_critical"] = float(critical)
                    result["vuln_total"] = float(len(vulns))
                except (json.JSONDecodeError, TypeError, KeyError):
                    pass
        return result


def get_available_plugins() -> dict[str, PluginMetadata]:
    """Get metadata for all available built-in plugins."""
    return {
        name: plugin.metadata 
        for name, plugin in PluginRegistry._plugins.items()
    }


def install_plugin_config(name: str, workdir: Path = Path(".")) -> str:
    """Generate configuration snippet for a plugin.
    
    Returns:
        YAML configuration string for the plugin
    """
    plugin_class = PluginRegistry.get(name)
    if not plugin_class:
        raise ValueError(f"Unknown plugin: {name}")
    
    instance = plugin_class()
    return instance.get_config_example()
