@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0"

echo ============================================
echo   TextClean 打包脚本（PyInstaller 单文件 exe）
echo ============================================
echo.

python -m PyInstaller --noconfirm --clean ^
  --name TextClean ^
  --onefile ^
  --windowed ^
  --icon "textclean.ico" ^
  --version-file "version_info.txt" ^
  --add-data "textclean.ico;." ^
  --collect-all tkinterdnd2 ^
  --exclude-module matplotlib ^
  --exclude-module numpy ^
  --exclude-module pandas ^
  --exclude-module openpyxl ^
  --exclude-module docx ^
  --exclude-module pptx ^
  --exclude-module xlrd ^
  "main.py"

if errorlevel 1 (
  echo.
  echo [失败] 打包出错，请查看上面的信息。
  pause
  exit /b 1
)

echo.
echo [成功] 产物：dist\TextClean.exe
echo.
endlocal