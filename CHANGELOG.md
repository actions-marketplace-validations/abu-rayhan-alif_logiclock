# Changelog

All notable changes to this project are documented in this file.

## Unreleased

### Added

- `scan` command with incremental cache, excludes, and worker support.
- `scan --format text|json|sarif` for CI and code-scanning workflows.
- `validate` command with rule-vs-decorator checks and actionable findings.
- `validate --format text|json|sarif` output options.
- `conflicts --advanced` for overlapping predicate conflict detection.
- `graph` export improvements for Mermaid and DOT output.
- `autotest` command for generated scenario execution (PASS/FAIL summary).
- `autotest --format json` for machine-readable CI output.
- `--trusted-code` gate for `validate` and `autotest` module execution safety.
- Open-source project policy docs:
  - `SECURITY.md`
  - `CONTRIBUTING.md`
  - `CODE_OF_CONDUCT.md`
- CI and release guidance docs under `docs/`.

### Changed

- README reorganized with quickstart, architecture, command matrix, and usage recipes.
- CI workflow upgraded with Python test matrix and quality gate improvements.
- Rule usage tracking extended with declared conditions for advanced conflict checks.

### Fixed

- Graph node-id collision for duplicate function names in visual exports.
- Label escaping issues for Mermaid/DOT outputs.
- Scan config fallback bug (`scan_format` from `.logiclock.toml` now respected).
- Cache file write path hardened (atomic replace).
- Repository cache artifact leakage mitigated (`.logiclock_scan_cache.json` ignored).
