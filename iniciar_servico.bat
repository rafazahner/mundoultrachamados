@echo off
title Monitor Ultra - Servico
cd /d "%~dp0"

:loop
echo [%date% %time%] Iniciando servidor_monitor.py...
py servidor_monitor.py
echo [%date% %time%] Processo encerrado. Reiniciando em 5 segundos...
timeout /t 5 /nobreak >nul
goto loop
