@echo off
REM Ruff linter script with OneDrive compatibility
set UV_LINK_MODE=copy
uv run ruff check .
