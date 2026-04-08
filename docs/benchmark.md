# Benchmark Notes

Measure scan performance in your repository:

```bash
logiclock scan . --no-cache
logiclock scan .
```

Expected behavior:
- first run parses all discovered Python files
- second run parses fewer files (or zero) due to cache hits

Recommended benchmark fields to capture:
- total files
- parsed vs cached files
- elapsed seconds
- worker count
