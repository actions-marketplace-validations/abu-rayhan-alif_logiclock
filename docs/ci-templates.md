# CI Templates

## Pre-commit (local)

Use `.pre-commit-config.yaml` from repository root:

```bash
pip install pre-commit
pre-commit install
```

## GitHub PR check

```yaml
name: logiclock-pr-check
on: [pull_request]
jobs:
  logiclock:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - run: |
          pip install pylogiclock
          logiclock scan . --format json
          logiclock conflicts --advanced

## Release pipeline snippet

```yaml
name: release
on:
  workflow_dispatch:
jobs:
  release:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - run: |
          python -m pip install --upgrade pip
          pip install build twine
          python -m build
          python -m twine check dist/*
```
```
