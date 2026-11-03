@echo off
chcp 65001 > nul
rem 대한민국 출생아수 분석기(GUI) 실행파일(exe) 빌드 스크립트
rem 결과물: dist\출생아수분석기.exe

cd /d "%~dp0"
pip install pyinstaller pandas matplotlib PyQt6 openpyxl

pyinstaller --noconfirm --onefile --windowed ^
  --name "출생아수분석기" ^
  --add-data "data\births.xlsx;data" ^
  --exclude-module PySide6 --exclude-module shiboken6 ^
  --exclude-module scipy --exclude-module IPython --exclude-module seaborn ^
  --exclude-module selenium --exclude-module pygame --exclude-module tkinter ^
  --exclude-module bs4 ^
  birth_gui.py

echo.
echo 빌드 완료! dist 폴더를 확인하세요.
pause
