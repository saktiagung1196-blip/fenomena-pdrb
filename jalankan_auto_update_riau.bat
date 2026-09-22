@echo off
cd /d "%~dp0"
echo ==========================================================
echo AUTO UPDATE BERITA RIAU
echo ==========================================================
py app_berita_riau_final.py --collect
echo.
if errorlevel 1 (
    echo UPDATE GAGAL.
    exit /b 1
)
echo UPDATE BERHASIL.
