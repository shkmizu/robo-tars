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
echo === Instalando as bibliotecas do TARS ===
%PY% -m pip install -r requirements.txt
if errorlevel 1 (
  echo.
  echo ERRO na instalacao das bibliotecas: veja a mensagem acima.
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
