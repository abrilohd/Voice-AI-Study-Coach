@echo off
cd /d "%~dp0"
uv run mypy app\core\security.py --strict
