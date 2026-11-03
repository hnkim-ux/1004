@echo off
chcp 65001 > nul
rem 코스피200 시세판(GUI) 실행파일(exe) 빌드 스크립트
rem 결과물: dist\코스피200시세판.exe

pip install pyinstaller requests openpyxl PyQt6

pyinstaller --noconfirm --onefile --windowed ^
  --name "코스피200시세판" ^
  --icon kospi200.ico ^
  --add-data "kospi200.ico;." ^
  --exclude-module PySide6 --exclude-module shiboken6 ^
  --exclude-module pandas --exclude-module numpy --exclude-module matplotlib ^
  --exclude-module scipy --exclude-module PIL --exclude-module IPython ^
  --exclude-module selenium --exclude-module pygame --exclude-module tkinter ^
  --exclude-module bs4 ^
  kospi200_gui.py

echo.
echo 빌드 완료! dist 폴더를 확인하세요.
pause
