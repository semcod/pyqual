import yaml
from pyqual.config import PyqualConfig, GateConfig

def test_default_yaml_parses() -> None:
    """Default pyqual.yaml should parse without errors."""
    raw = yaml.safe_load(PyqualConfig.default_yaml())
    config = PyqualConfig._parse(raw)
    assert config.name == "quality-loop"
    assert len(config.stages) == 6
    assert len(config.gates) == 3
    assert config.loop.max_iterations == 3

def test_gate_config_from_dict() -> None:
    """Gate config parses suffixes correctly."""
    g1 = GateConfig.from_dict("cc_max", "15")
    assert g1.metric == "cc"
    assert g1.operator == "le"
    assert g1.threshold == 15.0

    g2 = GateConfig.from_dict("coverage_min", "80")
    assert g2.metric == "coverage"
    assert g2.operator == "ge"
    assert g2.threshold == 80.0