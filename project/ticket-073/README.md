# ticket-073: Fix PERF-AUDIT findings and adopt Wellmanifest baseline standards

- **Status**: IN_PROGRESS
- **Workflow state**: VERIFIED

SESSION_EXECUTION_AUTHORIZATION: continue analysis, repairs, and standard alignment across projects using `wellmanifest/wellman`.

## Acceptance Criteria
- [x] AC-01: Bound log and audit file reads in `.github/workflows/pyqual-ci.yml` and `pyqual/plugins/security/main.py` (`PERF-AUDIT-IO-001`).
- [x] AC-02: Extract subprocess wrapper `_run_planfile_cli` in `pyqual/tickets.py` (`PERF-AUDIT-SUBPROC-001`).
- [x] AC-03: Wire unused optional kwargs in `pyqual/bulk/runner.py`, `pyqual/cli/main.py`, `pyqual/plugins/__init__.py`, `pyqual/plugins/git/main.py`, and `pyqual/yaml_fixer.py` (`PERF-AUDIT-KWARG-001`).
- [x] AC-04: Adopt Wellmanifest `baseline` standards in `.governance/` and pass all tests.
