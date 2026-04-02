I need the Python source files you want me to edit.

What I need from you
- Add (paste) the exact contents of each Python file that should be changed, and include the full file path for each file (as shown in your repo).
- If you prefer, add a small repo tree (git ls-files or find output) so I can point to files to edit.
- Do NOT modify TODO.md as requested.

Planned fixes (I will implement once you provide the files)
1. Remove unused imports (delete the import lines or move needed names into local scope).
2. Replace magic numbers with named constants (add meaningful CONSTANT_NAME = <value> at module top and use that name).
3. Remove duplicate imports (keep a single canonical import; use from X import Y where appropriate).
4. Add short inline comments explaining newly introduced constants where necessary.
5. Keep import ordering consistent (stdlib, third-party, local) and avoid wildcard imports.

How I'll deliver edits
- For every file you add, I'll produce SEARCH/REPLACE blocks that match the file's existing content exactly and replace only the necessary lines.
- I will keep each SEARCH block small and uniquely matching to make edits safe.
- After you apply the edits, you can tell me and I can make follow-ups.

Helpful commands you can run locally to gather candidate files
```bash
git ls-files '*.py' || find . -name '*.py'
```
```bash
grep -RIn --include='*.py' -E "\b(import|from)\b" .
```

Please add the Python files (with full paths) that contain the issues and I'll produce the precise SEARCH/REPLACE edits.
