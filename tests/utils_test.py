import tempfile
from pathlib import Path
def test_temp_dir_creation() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        p = Path(tmpdir)
        assert p.exists()
        assert p.is_dir()