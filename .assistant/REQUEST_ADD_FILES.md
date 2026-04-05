I need the files you want me to edit so I can produce exact SEARCH/REPLACE edits.

What I need from you
- Add (paste) the exact contents of each file you want changed into this chat, and include the full file path for each (for example: src/utils/calcs.py).
- You mentioned 5 issues to fix. Please provide the five file paths (and their contents) that contain those issues.
- If you want me to prefer certain constant names for magic numbers, say so (otherwise I'll choose clear names).

Planned changes (short)
1. Remove unused imports.
2. Replace magic numbers with module-level named constants (placed near the top of the file).
3. Remove duplicate imports and consolidate imports where appropriate.
4. Make minimal, well-documented changes and do NOT modify TODO.md.

After you add the files
- I will:
  - Explain each change in 1–2 sentences.
  - Provide one SEARCH/REPLACE block per edit (or per small group of edits) that exactly matches the current file contents and the replacement.
  - Keep edits small and focused so each SEARCH uniquely matches.

Examples of what to paste
- For each file, paste a header line with the full path, e.g.:
  /path/to/file.py
  <then the file contents>

Helpful shell commands (run from repo root)
```bash
git status --porcelain
pytest -q
```

Once you paste the five files (with paths), I'll prepare the SEARCH/REPLACE edits.
