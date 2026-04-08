# Contributing Guide

Thanks for contributing to `logiclock`.

## Development Setup

```bash
git clone https://github.com/abu-rayhan-alif/logiclock.git
cd logiclock
pip install -e ".[dev]"
```

## Local Quality Checks

```bash
flake8 src tests
pytest tests -q
```

## Branch and PR Workflow

- create a feature branch from `develop`
- keep commits focused and descriptive
- open a PR with:
  - summary
  - risk level
  - test plan

## Commit Message Style

Use clear intent-first messages, for example:
- `feat: add scan sarif output`
- `fix: guard module import behind trusted-code flag`
- `docs: improve quickstart by persona`

## Documentation

If behavior changes, update:
- `README.md`
- relevant docs in `docs/`
- tests/snapshots when needed

## Security

For vulnerabilities, follow `SECURITY.md` instead of opening a public issue.
