from __future__ import annotations

import json
from pathlib import Path

import pytest


@pytest.fixture
def workspace(tmp_path: Path) -> Path:
    """Create a fake workspace with several project types."""
    py = tmp_path / "mylib"
    py.mkdir()
    (py / "pyproject.toml").write_text("[project]\nname = 'mylib'\n")
    (py / "tests").mkdir()
    (py / "tests" / "test_main.py").write_text("def test_ok(): pass\n")
    (py / "src").mkdir()
    (py / "src" / "main.py").write_text("print('hello')\n")

    node = tmp_path / "webapp"
    node.mkdir()
    (node / "package.json").write_text(json.dumps({"name": "webapp", "scripts": {"test": "jest", "lint": "eslint .", "build": "tsc"}}))
    (node / "src").mkdir()
    (node / "src" / "index.ts").write_text("console.log('hi');\n")

    php = tmp_path / "api-server"
    php.mkdir()
    (php / "composer.json").write_text(json.dumps({"name": "vendor/api-server", "scripts": {"test": "phpunit"}}))
    (php / "index.php").write_text("<?php echo 'ok'; ?>\n")

    mk = tmp_path / "infra"
    mk.mkdir()
    (mk / "Makefile").write_text("test:\n\techo ok\nlint:\n\techo lint\n")
    (mk / "deploy.sh").write_text("#!/bin/bash\n")

    existing = tmp_path / "existing"
    existing.mkdir()
    (existing / "pyqual.yaml").write_text("pipeline:\n  name: existing\n  stages: []\n")
    (existing / "pyproject.toml").write_text("[project]\nname = 'existing'\n")

    data = tmp_path / "recordings"
    data.mkdir()
    (data / "file.wav").write_text("")

    hidden = tmp_path / ".cache"
    hidden.mkdir()
    (hidden / "stuff").write_text("")

    return tmp_path
