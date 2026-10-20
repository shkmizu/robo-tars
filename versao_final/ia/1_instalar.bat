@echo off
chcp 65001 >nul
cd /d "%~dp0"
set PY=python
where py >nul 2>nul && set PY=py -3
echo === Instalando as bibliotecas do TARS ===
%PY% -m pip install -r requirements.txt
if errorlevel 1 (
  echo.
  echo ERRO: confira se o Python 3.11 ou 3.12 esta instalado e marcado "Add python.exe to PATH".
  pause
  exit /b 1
)
echo.
echo === Baixando o modelo de IA (uns 2 GB, so na primeira vez) ===
ollama pull llama3.2:3b
if errorlevel 1 echo AVISO: instale o Ollama em ollama.com e rode este arquivo de novo.
echo.
%PY% tars.py --teste
pause
