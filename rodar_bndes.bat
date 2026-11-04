@echo off
chcp 65001 > nul
cd /d "%~dp0"
set PYTHONIOENCODING=utf-8
set CONDA=%USERPROFILE%\miniconda3
set PATH=%CONDA%;%CONDA%\Library\mingw-w64\bin;%CONDA%\Library\usr\bin;%CONDA%\Library\bin;%CONDA%\Scripts;%PATH%
set PY=%CONDA%\python.exe
echo Rodando baixar_bndes.py. A janela fecha sozinha ao terminar.
(
  "%PY%" -m pip install --quiet requests
  "%PY%" baixar_bndes.py
) > log_bndes.txt 2>&1
echo Pronto. Resultado salvo em log_bndes.txt
timeout /t 5 > nul
