#!/usr/bin/env bash
git status
python -m pip install ruff
ruff check .
