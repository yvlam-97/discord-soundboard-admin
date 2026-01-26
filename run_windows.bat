@echo off
REM Change to script directory
cd /d "%~dp0"

REM Activate the virtual environment
call bot-env\Scripts\activate.bat

REM Install/update dependencies
python -m pip install -r requirements.txt

REM Run the bot (web server is integrated)
title Audio Ambush
python main.py

pause
