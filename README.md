<div align="center">

### logic-lock

<table align="center"><tr><td>

<pre>
==================================================
            L O G I C - L O C K
       pip install    logic-lock
       import         logiclock
==================================================
</pre>

</td></tr></table>

[![Python](https://img.shields.io/badge/python-3.11%2B-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-MIT-F5BD02?style=for-the-badge)](LICENSE)
[![PyPI](https://img.shields.io/badge/install-logic--lock-006DAD?style=for-the-badge&logo=pypi&logoColor=white)](https://pypi.org/project/logic-lock/)
[![GitHub](https://img.shields.io/badge/GitHub-repo-24292F?style=for-the-badge&logo=github)](https://github.com/abu-rayhan-alif/logiclock)

### Rules, decorator metadata, and code — stay consistent

**`pip install logic-lock`** — **import `logiclock`**

<br>

</div>

---

## What it does

**logic-lock** ties **authoritative rule definitions** (e.g. JSON: conditions + result) to
what you declare on Python functions with **`@logic_lock`** (rule id, optional `result` /
`conditions`). It can **report mismatches** (wrong result string, missing conditions) and
includes helpers for **matching**, **reports**, and **scenario hints** — so teams don’t
silently drift between “what the rule says” and “what the code claims.”

## Why use it

- One place for **rule IDs** and expected outcomes; metadata on callables documents intent.
- **Catch inconsistencies early** (tests or CI) instead of only in code review.
- **Small CLI** today (`report-sample`, version); **`scan` / `validate` will grow** — the
  **Python API** is the main integration point right now.

## TL;DR

```bash
pip install logic-lock
logiclock --version
logiclock --no-color report-sample
```

---

## In your code

```python
from logiclock.decorators import logic_lock

@logic_lock(
    "my_rule",
    result="ok",
    conditions=["user.is_active"],
)
def handle_request(user):
    ...
```

More examples: [`tests/test_rule_validator.py`](tests/test_rule_validator.py).

---

## Install

| How | Command |
|-----|---------|
| PyPI | `pip install logic-lock` |
| This repo | `pip install .` |

CLI: `logiclock --help`

---

## Troubleshooting

| Issue | Try |
|-------|-----|
| `No module named logiclock` | `pip install logic-lock` or `pip install -e .` |
| CLI not found | Same venv; `python -m pip show logic-lock` |
| `scan` is a stub | Use the **Python API** for now |
| Colors in CI | `logiclock --no-color ...` |

[Issues](https://github.com/abu-rayhan-alif/logiclock/issues)

---

<details>
<summary><b>Development</b></summary>

Python **3.11+**.

```bash
pip install -r requirements-lock.txt
pip install -e . --no-deps
flake8 src tests
pytest tests
```

Or `pip install -e ".[dev]"`. Refresh lock:

```bash
pip-compile --strip-extras --extra dev -o requirements-lock.txt pyproject.toml
```

</details>

<details>
<summary><b>CI in this repo</b></summary>

- **lint-and-test**: `flake8` + `pytest`
- **logiclock-scan**: composite action, `continue-on-error: true` for now

</details>

<details>
<summary><b>GitHub Actions (yours)</b></summary>

```yaml
jobs:
  logiclock:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
          cache: pip
          cache-dependency-path: |
            pyproject.toml
            requirements-lock.txt
      - run: |
          pip install -r requirements-lock.txt
          pip install . --no-deps
      - run: logiclock --strict --no-color scan
```

**This repo** (`uses: ./`):

```yaml
- uses: ./
  with:
    python-version: "3.12"
    install-command: pip install -r requirements-lock.txt && pip install . --no-deps
    scan-command: logiclock --strict --no-color scan
```

**Other repos**:

```yaml
install-command: pip install "logic-lock @ git+https://github.com/YOUR_ORG/logiclock.git@vX.Y.Z"
```

On PyPI: use `pip install logic-lock` in `install-command`.

</details>
