@echo off
chcp 65001 >nul
cd /d "%~dp0"
set PY=python
where py >nul 2>nul && set PY=py -3
echo Fale perto do microfone. Diga "desligar" para sair.
%PY% tars.py --porta auto --baud 115200
pause
