@echo off
chcp 65001 >nul
cd /d "%~dp0"
rem O PyAudio (microfone) so tem instalador pronto ate o Python 3.13: usa o 3.12 se existir.
set PY=
py -3.12 -c "" >nul 2>nul && set "PY=py -3.12"
if not defined PY (py -3.11 -c "" >nul 2>nul && set "PY=py -3.11")
if not defined PY (py -3.13 -c "" >nul 2>nul && set "PY=py -3.13")
if not defined PY (
  echo ERRO: instale o Python 3.12 em python.org/downloads/release/python-31210/
  echo        "Windows installer (64-bit)". Pode manter o Python mais novo instalado junto.
  pause
  exit /b 1
)
%PY% tars.py --porta auto --baud 115200 --diagnostico
pause
