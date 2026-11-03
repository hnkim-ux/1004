@echo off
chcp 65001 > nul
rem S&P 500 데이터 분석기(GUI) 실행파일(exe) 빌드 스크립트
rem 결과물: dist\SP500분석기.exe

pip install pyinstaller pandas matplotlib PyQt6

pyinstaller --noconfirm --onefile --windowed ^
  --name "SP500분석기" ^
  --icon sp500.ico ^
  --add-data "sp500.ico;." ^
  --exclude-module PySide6 --exclude-module shiboken6 ^
  --exclude-module scipy --exclude-module IPython --exclude-module seaborn ^
  --exclude-module selenium --exclude-module pygame --exclude-module tkinter ^
  --exclude-module bs4 --exclude-module openpyxl ^
  sp500_gui.py

echo.
echo 빌드 완료! dist 폴더를 확인하세요.
pause
