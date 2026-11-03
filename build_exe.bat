@echo off
chcp 65001 > nul
rem 말랑말랑 뉴스 수집기 실행파일(exe) 빌드 스크립트
rem 결과물: dist\말랑말랑뉴스수집기.exe

pip install pyinstaller requests beautifulsoup4 openpyxl PyQt6

pyinstaller --noconfirm --onefile --windowed ^
  --name "말랑말랑뉴스수집기" ^
  --icon news_bunny.ico ^
  --add-data "news_bunny.ico;." ^
  --exclude-module PySide6 --exclude-module shiboken6 ^
  --exclude-module pandas --exclude-module numpy --exclude-module matplotlib ^
  --exclude-module scipy --exclude-module PIL --exclude-module IPython ^
  --exclude-module selenium --exclude-module pygame --exclude-module tkinter ^
  naver_news_crawler.py

echo.
echo 빌드 완료! dist 폴더를 확인하세요.
pause
