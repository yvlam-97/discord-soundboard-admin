@echo off
REM Activate the virtual environment

call "%~dp0bot-env\Scripts\activate.bat"
python -m pip install -r requirements.txt

REM Start the bot in a new window
title audio-ambush-bot

start cmd /k python main.py

REM Start the web server in a new window
title audio-ambush-web

start cmd /k python -m uvicorn soundboard_web:app --host 127.0.0.1 --port 8080

echo Both bot and web server started in separate windows.
pause
