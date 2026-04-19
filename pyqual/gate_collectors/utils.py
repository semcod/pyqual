from pathlib import Path

def _read_artifact_text(workdir: Path, filenames: list[str]) -> str | None:
    for base in (workdir, workdir / "project"):
        for name in filenames:
            p = base / name
            if p.exists():
                try:
                    return p.read_text()
                except OSError:
                    continue
    return None