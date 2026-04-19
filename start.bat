@echo off
:: RustCleaner v3 Launcher
:: Forces interactive mode by default, handles working directory
cd /d "%~dp0"
python "%~dp0rust_clean.py"
pause
