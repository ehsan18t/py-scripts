@ECHO OFF
TITLE Auto App Updater
SETLOCAL ENABLEDELAYEDEXPANSION

@REM Configs
CALL %~dp0Configs.bat

rem CD "%pyDlScriptLocation%"


@REM 
@REM Clean Up before Downloading
@REM
rem DEL /S /Q "%dl_location%\*.exe" >NUL 2>&1
rem DEL /S /Q "%dl_location%\*.msi" >NUL 2>&1

python "%pyDlScript%" "%dl_location%"
PAUSE