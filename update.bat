@echo off
setlocal
rem ================================================================
rem  NetzwerkCosmetics - Update-Skript
rem  Holt die neueste Version per "git pull" und kopiert die Plugins
rem  in deine Server. Vorher die Server STOPPEN (Windows sperrt
rem  JAR-Dateien, die gerade benutzt werden).
rem ================================================================

rem ---- HIER ANPASSEN: Ordner deiner Paper-Server (mit Leerzeichen trennen) ----
set PAPER_SERVERS="C:\Server\Lobby" "C:\Server\Spielmodus1"
rem ---- HIER ANPASSEN: Ordner deines BungeeCord-Proxys ----
set PROXY=C:\Server\BungeeCord
rem ------------------------------------------------------------------------------

cd /d "%~dp0"
echo Hole neueste Version von GitHub ...
git pull --ff-only
if errorlevel 1 (
    echo.
    echo FEHLER: git pull hat nicht geklappt. Siehe Meldung oben.
    pause
    exit /b 1
)
echo.

for %%S in (%PAPER_SERVERS%) do (
    if exist "%%~S\plugins\" (
        del /Q "%%~S\plugins\NetzwerkCosmetics-Paper-*.jar" 2>nul
        copy /Y "dist\NetzwerkCosmetics-Paper.jar" "%%~S\plugins\" >nul
        if errorlevel 1 (
            echo FEHLER: Konnte nicht nach %%~S kopieren. Laeuft der Server noch?
        ) else (
            echo OK   Paper-Plugin nach %%~S\plugins
        )
    ) else (
        echo WARNUNG: %%~S\plugins gibt es nicht - Pfad in update.bat pruefen
    )
)

if exist "%PROXY%\plugins\" (
    del /Q "%PROXY%\plugins\NetzwerkCosmetics-Bungee-*.jar" 2>nul
    copy /Y "dist\NetzwerkCosmetics-Bungee.jar" "%PROXY%\plugins\" >nul
    if errorlevel 1 (
        echo FEHLER: Konnte nicht nach %PROXY% kopieren. Laeuft der Proxy noch?
    ) else (
        echo OK   Bungee-Plugin nach %PROXY%\plugins
    )
) else (
    echo WARNUNG: %PROXY%\plugins gibt es nicht - Pfad in update.bat pruefen
)

echo.
echo Fertig. Neue resourcepack.zip liegt in: %~dp0dist
echo Hat sich das Pack geaendert, neu hochladen und die URL in der config.yml anpassen.
echo Jetzt die Server wieder starten.
pause
