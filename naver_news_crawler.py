"""
네이버 통합검색 결과의 '뉴스' 영역에서 기사 목록을 수집하고,
각 기사의 본문까지 크롤링하는 GUI 앱 (requests + BeautifulSoup4 + PyQt6)

사용법:
    pip install requests beautifulsoup4 PyQt6
    python naver_news_crawler.py
"""

import csv
import html
import json
import os
import sys
import time
from collections import OrderedDict
from urllib.parse import quote

import requests
from bs4 import BeautifulSoup
from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from PyQt6.QtCore import Qt, QThread, QUrl, pyqtSignal
from PyQt6.QtGui import QDesktopServices, QIcon
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QFileDialog,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
)

SEARCH_URL = (
    "https://search.naver.com/search.naver"
    "?where=nexearch&sm=top_hty&fbm=0&ie=utf8&query={query}"
)
DEFAULT_KEYWORD = "반도체"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/130.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "ko-KR,ko;q=0.9",
}

REQUEST_DELAY = 0.5  # 기사 요청 사이 대기 시간(초) - 서버 부담 줄이기


def resource_path(name):
    """PyInstaller로 묶인 exe에서는 임시 폴더(sys._MEIPASS)에서 리소스를 찾는다."""
    base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, name)


# 파스텔 핑크 & 라벤더 테마
STYLE_SHEET = """
QWidget {
    font-family: "Malgun Gothic";
    font-size: 10.5pt;
    color: #6B4E71;
}
QMainWindow, QWidget#central {
    background-color: #FFF4F8;
}
QLabel#title {
    font-size: 20pt;
    font-weight: bold;
    color: #FF7EB3;
    padding: 4px 0 0 4px;
}
QLabel#subtitle {
    color: #B49BC8;
    padding-left: 6px;
}
QLineEdit {
    background: #FFFFFF;
    border: 2px solid #FFC4DD;
    border-radius: 18px;
    padding: 7px 16px;
    selection-background-color: #FFB3D1;
}
QLineEdit:focus {
    border: 2px solid #FF8FC0;
}
QPushButton {
    border: none;
    border-radius: 18px;
    padding: 9px 18px;
    font-weight: bold;
    color: #FFFFFF;
    background-color: #FF8FC0;
}
QPushButton:hover   { background-color: #FF75B0; }
QPushButton:pressed { background-color: #F25C9C; }
QPushButton:disabled {
    background-color: #F1DDE8;
    color: #FFFFFF;
}
QPushButton#csvBtn          { background-color: #B9A3F0; }
QPushButton#csvBtn:hover    { background-color: #A68CEB; }
QPushButton#excelBtn        { background-color: #7FD8BE; }
QPushButton#excelBtn:hover  { background-color: #63CCAD; }
QPushButton#csvBtn:disabled, QPushButton#excelBtn:disabled {
    background-color: #EDE6F2;
}
QTableWidget, QTextBrowser {
    background: #FFFFFF;
    border: 2px solid #FFD6E7;
    border-radius: 16px;
    padding: 6px;
}
QTableWidget {
    gridline-color: transparent;
    alternate-background-color: #FFF8FB;
    selection-background-color: #FFE0EE;
    selection-color: #6B4E71;
    outline: 0;
}
QTableWidget::item {
    padding: 6px;
    border-bottom: 1px dashed #FBE3EE;
}
QHeaderView::section {
    background-color: #FFE4F0;
    color: #E0679C;
    font-weight: bold;
    border: none;
    padding: 8px;
}
QSplitter::handle {
    background: transparent;
    width: 10px;
}
QProgressBar {
    background: #FFFFFF;
    border: 2px solid #FFD6E7;
    border-radius: 9px;
    height: 14px;
    text-align: center;
    color: #E0679C;
    font-size: 8pt;
}
QProgressBar::chunk {
    border-radius: 7px;
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                                stop:0 #FFB3D1, stop:1 #C7B3FF);
}
QScrollBar:vertical {
    background: transparent;
    width: 10px;
    margin: 4px;
}
QScrollBar::handle:vertical {
    background: #FFC4DD;
    border-radius: 5px;
    min-height: 30px;
}
QScrollBar::add-line, QScrollBar::sub-line { height: 0; }
QScrollBar::add-page, QScrollBar::sub-page { background: none; }
QMessageBox { background-color: #FFF4F8; }
QMessageBox QPushButton { min-width: 70px; }
"""


# ─────────────────────────────────────────────
# 크롤링 함수
# ─────────────────────────────────────────────
def get_soup(url):
    res = requests.get(url, headers=HEADERS, timeout=10)
    res.raise_for_status()
    if not res.encoding or res.encoding.lower() == "iso-8859-1":
        res.encoding = res.apparent_encoding  # 일부 언론사의 인코딩 보정
    return BeautifulSoup(res.text, "html.parser")


def clean_text(text):
    return text.replace("새 창 열림", "").strip()


def parse_search_results(soup):
    """
    검색 결과의 뉴스 영역에서 기사 목록 추출.
    네이버는 CSS 클래스명이 자주 바뀌므로(난독화), 비교적 안정적인
    data-nlog-area 속성(nws_all.j.tit / body / prof / nav)을 기준으로 파싱한다.
    """
    articles = OrderedDict()

    for a in soup.select('a[data-nlog-area^="nws_all"]'):
        try:
            gdid = json.loads(a.get("data-nlog-params", "{}")).get("gdid")
        except json.JSONDecodeError:
            gdid = None
        if not gdid:
            continue

        item = articles.setdefault(
            gdid,
            {"title": "", "summary": "", "press": "", "link": "", "naver_link": ""},
        )
        area = a["data-nlog-area"].rsplit(".", 1)[-1]
        text = clean_text(a.get_text(" ", strip=True))

        if area == "tit" and not item["title"]:
            item["title"] = text
            item["link"] = a["href"]
        elif area == "body" and not item["summary"]:
            item["summary"] = text
        elif area == "prof" and text and not item["press"]:
            item["press"] = text
        elif area == "nav":
            item["naver_link"] = a["href"]

    return [item for item in articles.values() if item["title"]]


def parse_naver_article(url):
    """네이버뉴스(n.news.naver.com) 기사 본문 파싱"""
    soup = get_soup(url)

    title = soup.select_one("#title_area") or soup.select_one("h2.media_end_head_headline")
    date = soup.select_one("span.media_end_head_info_datestamp_time")
    body = soup.select_one("#dic_area") or soup.select_one("#articeBody")

    if body:
        # 사진 설명, 스크립트 등 본문이 아닌 요소 제거
        for tag in body.select("script, style, em.img_desc, span.end_photo_org"):
            tag.decompose()
        for br in body.find_all("br"):
            br.replace_with("\n")

    return {
        "title": title.get_text(strip=True) if title else "",
        "date": (date.get("data-date-time") or date.get_text(strip=True)) if date else "",
        "content": "\n".join(
            line.strip() for line in body.get_text().splitlines() if line.strip()
        ) if body else "",
    }


def parse_press_article(url):
    """
    언론사 원문 기사 파싱 (네이버뉴스 링크가 없는 경우의 대체 방법).
    언론사마다 구조가 달라 <article> 또는 가장 텍스트가 많은 영역의 <p> 를 사용한다.
    """
    soup = get_soup(url)
    for tag in soup.select("script, style, header, footer, nav, aside"):
        tag.decompose()

    container = soup.find("article") or soup.body
    paragraphs = [p.get_text(strip=True) for p in container.find_all("p")]
    content = "\n".join(p for p in paragraphs if len(p) > 20)

    if not content:
        og = soup.find("meta", property="og:description")
        content = og["content"] if og else ""

    date = soup.find("meta", property="article:published_time")
    return {"date": date["content"] if date else "", "content": content}


def fetch_detail(item):
    """기사 1건의 본문/날짜를 채워 넣는다."""
    try:
        if item["naver_link"]:
            detail = parse_naver_article(item["naver_link"])
            item["title"] = detail["title"] or item["title"]
        else:
            detail = parse_press_article(item["link"])
        item["date"] = detail["date"]
        item["content"] = detail["content"] or item["summary"]
    except requests.RequestException as e:
        item["date"] = ""
        item["content"] = f"[본문 수집 실패: {e}]\n\n{item['summary']}"
    return item


def save_csv(results, filename):
    fields = ["title", "press", "date", "link", "naver_link", "summary", "content"]
    # utf-8-sig: 엑셀에서 열어도 한글이 깨지지 않도록 BOM 추가
    with open(filename, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(results)


def save_excel(results, filename):
    columns = [
        ("title", "제목", 50),
        ("press", "언론사", 12),
        ("date", "날짜", 20),
        ("naver_link", "네이버뉴스 링크", 30),
        ("link", "원문 링크", 30),
        ("summary", "요약", 50),
        ("content", "본문", 80),
    ]

    wb = Workbook()
    ws = wb.active
    ws.title = "뉴스"

    # 헤더
    ws.append([label for _, label, _ in columns])
    for col, (_, _, width) in enumerate(columns, 1):
        cell = ws.cell(row=1, column=col)
        cell.font = Font(bold=True, color="FFFFFF")
        cell.fill = PatternFill("solid", fgColor="03C75A")
        cell.alignment = Alignment(horizontal="center", vertical="center")
        ws.column_dimensions[cell.column_letter].width = width

    # 데이터 (엑셀 셀 1개는 최대 32,767자까지만 저장 가능)
    for item in results:
        ws.append([item.get(key, "")[:32767] for key, _, _ in columns])

    for row in ws.iter_rows(min_row=2):
        for cell in row:
            cell.alignment = Alignment(vertical="top", wrap_text=True)
        for cell in (row[3], row[4]):  # 링크 칼럼은 클릭 가능한 하이퍼링크로
            if cell.value:
                cell.hyperlink = cell.value
                cell.font = Font(color="0563C1", underline="single")

    ws.freeze_panes = "A2"  # 스크롤해도 헤더 고정
    wb.save(filename)


# ─────────────────────────────────────────────
# 백그라운드 크롤링 스레드 (GUI 멈춤 방지)
# ─────────────────────────────────────────────
class CrawlWorker(QThread):
    found = pyqtSignal(int)                # 검색 결과에서 찾은 기사 수
    article_done = pyqtSignal(int, dict)   # (순번, 기사 데이터)
    failed = pyqtSignal(str)

    def __init__(self, keyword):
        super().__init__()
        self.keyword = keyword

    def run(self):
        try:
            soup = get_soup(SEARCH_URL.format(query=quote(self.keyword)))
        except requests.RequestException as e:
            self.failed.emit(f"검색 페이지 요청 실패: {e}")
            return

        articles = parse_search_results(soup)
        self.found.emit(len(articles))

        for i, item in enumerate(articles):
            if self.isInterruptionRequested():
                break
            self.article_done.emit(i, fetch_detail(item))
            time.sleep(REQUEST_DELAY)


# ─────────────────────────────────────────────
# 메인 윈도우
# ─────────────────────────────────────────────
class MainWindow(QMainWindow):
    COLUMNS = ["제목", "언론사", "날짜"]

    def __init__(self):
        super().__init__()
        self.setWindowTitle("🐰 말랑말랑 뉴스 수집기")
        self.resize(1100, 720)
        self.results = []
        self.worker = None

        # 타이틀
        title = QLabel("🐰 말랑말랑 뉴스 수집기 🌸")
        title.setObjectName("title")
        subtitle = QLabel("궁금한 키워드를 입력하면 뉴스를 쏙쏙 모아올게요 ✨")
        subtitle.setObjectName("subtitle")

        # 상단: 검색어 입력 + 버튼
        self.keyword_edit = QLineEdit(DEFAULT_KEYWORD)
        self.keyword_edit.setPlaceholderText("🔍 어떤 뉴스가 궁금하세요?")
        self.keyword_edit.returnPressed.connect(self.start_crawl)

        self.search_btn = QPushButton("🔍 찾아보기")
        self.search_btn.clicked.connect(self.start_crawl)
        self.save_btn = QPushButton("📝 CSV 저장")
        self.save_btn.setObjectName("csvBtn")
        self.save_btn.setEnabled(False)
        self.save_btn.clicked.connect(self.save_results)
        self.excel_btn = QPushButton("📊 엑셀 저장")
        self.excel_btn.setObjectName("excelBtn")
        self.excel_btn.setEnabled(False)
        self.excel_btn.clicked.connect(self.save_results_excel)
        for btn in (self.search_btn, self.save_btn, self.excel_btn):
            btn.setCursor(Qt.CursorShape.PointingHandCursor)

        top = QHBoxLayout()
        top.setSpacing(8)
        top.addWidget(self.keyword_edit, 1)
        top.addWidget(self.search_btn)
        top.addWidget(self.save_btn)
        top.addWidget(self.excel_btn)

        # 좌측: 기사 목록 테이블
        self.table = QTableWidget(0, len(self.COLUMNS))
        self.table.setHorizontalHeaderLabels(self.COLUMNS)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.verticalHeader().setVisible(False)
        self.table.setAlternatingRowColors(True)
        self.table.setShowGrid(False)
        self.table.setFocusPolicy(Qt.FocusPolicy.NoFocus)  # 선택 셀의 파란 테두리 제거
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.table.itemSelectionChanged.connect(self.show_article)
        self.table.cellDoubleClicked.connect(self.open_in_browser)

        # 우측: 기사 본문 보기
        self.viewer = QTextBrowser()
        self.viewer.setOpenExternalLinks(True)
        self.show_placeholder()

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.addWidget(self.table)
        splitter.addWidget(self.viewer)
        splitter.setSizes([550, 550])

        # 하단: 진행 상태
        self.progress = QProgressBar()
        self.progress.setVisible(False)
        self.progress.setFixedWidth(220)
        self.status_label = QLabel("💡 기사를 더블클릭하면 브라우저에서 열려요!")

        bottom = QHBoxLayout()
        bottom.addWidget(self.status_label, 1)
        bottom.addWidget(self.progress)

        layout = QVBoxLayout()
        layout.setContentsMargins(18, 14, 18, 12)
        layout.setSpacing(10)
        layout.addWidget(title)
        layout.addWidget(subtitle)
        layout.addLayout(top)
        layout.addWidget(splitter, 1)
        layout.addLayout(bottom)
        container = QWidget()
        container.setObjectName("central")
        container.setLayout(layout)
        self.setCentralWidget(container)

    # ── 크롤링 ──
    def start_crawl(self):
        keyword = self.keyword_edit.text().strip()
        if not keyword:
            QMessageBox.warning(self, "앗!", "검색어를 먼저 입력해 주세요 🥺")
            return
        if self.worker and self.worker.isRunning():
            return

        self.results = []
        self.table.setRowCount(0)
        self.show_placeholder("🐾 뉴스를 찾으러 가는 중이에요...")
        self.search_btn.setEnabled(False)
        self.save_btn.setEnabled(False)
        self.excel_btn.setEnabled(False)
        self.status_label.setText(f"🐇 '{keyword}' 뉴스를 찾는 중이에요...")

        self.worker = CrawlWorker(keyword)
        self.worker.found.connect(self.on_found)
        self.worker.article_done.connect(self.on_article_done)
        self.worker.failed.connect(self.on_failed)
        self.worker.finished.connect(self.on_finished)
        self.worker.start()

    def on_found(self, count):
        if count == 0:
            self.status_label.setText("😢 뉴스 기사를 찾지 못했어요. 다른 키워드로 해볼까요?")
            self.show_placeholder("😢 뉴스 기사를 찾지 못했어요")
            return
        self.progress.setRange(0, count)
        self.progress.setValue(0)
        self.progress.setVisible(True)
        self.status_label.setText(f"🍓 기사 {count}건 발견! 본문을 열심히 읽어오는 중...")

    def on_article_done(self, index, item):
        self.results.append(item)
        row = self.table.rowCount()
        self.table.insertRow(row)
        for col, key in enumerate(["title", "press", "date"]):
            self.table.setItem(row, col, QTableWidgetItem(item.get(key, "")))
        self.progress.setValue(index + 1)
        if row == 0:
            self.table.selectRow(0)

    def on_failed(self, message):
        QMessageBox.critical(self, "앗, 문제가 생겼어요 😵", message)
        self.status_label.setText(f"😵 {message}")

    def on_finished(self):
        self.search_btn.setEnabled(True)
        self.progress.setVisible(False)
        if self.results:
            self.save_btn.setEnabled(True)
            self.excel_btn.setEnabled(True)
            self.status_label.setText(f"🎉 짜잔! 뉴스 {len(self.results)}건을 모아왔어요")

    # ── 기사 보기 ──
    def show_placeholder(self, message="🌷 왼쪽에서 기사를 고르면 여기에 본문이 보여요"):
        self.viewer.setHtml(
            "<div style='text-align:center; margin-top:120px;'>"
            "<p style='font-size:48pt;'>🐰</p>"
            f"<p style='font-size:12pt; color:#C7A3D9;'>{message}</p></div>"
        )

    def show_article(self):
        rows = self.table.selectionModel().selectedRows()
        if not rows:
            return
        item = self.results[rows[0].row()]
        link = item["naver_link"] or item["link"]
        content = html.escape(item["content"]).replace("\n", "<br><br>")
        self.viewer.setHtml(
            f"<h2 style='color:#E0679C;'>🌸 {html.escape(item['title'])}</h2>"
            f"<p style='color:#B49BC8;'>📰 {html.escape(item['press'])} &nbsp;·&nbsp; 🕐 {item['date']}<br>"
            f"🔗 <a href='{link}' style='color:#9C7FE0;'>{link}</a></p>"
            "<p style='text-align:center; color:#FFC4DD;'>♡ · ♡ · ♡ · ♡ · ♡</p>"
            f"<div style='line-height:160%; color:#5C4663;'>{content}</div>"
        )

    def open_in_browser(self, row, _col):
        item = self.results[row]
        QDesktopServices.openUrl(QUrl(item["naver_link"] or item["link"]))

    # ── 저장 ──
    def save_results(self):
        filename, _ = QFileDialog.getSaveFileName(
            self, "CSV 저장", "naver_news.csv", "CSV 파일 (*.csv)"
        )
        if not filename:
            return
        try:
            save_csv(self.results, filename)
            QMessageBox.information(self, "저장 완료 💾", f"뉴스 {len(self.results)}건을 저장했어요! 🎀\n{filename}")
        except OSError as e:
            QMessageBox.critical(self, "저장 실패", str(e))

    def save_results_excel(self):
        keyword = self.keyword_edit.text().strip() or "news"
        filename, _ = QFileDialog.getSaveFileName(
            self, "엑셀 저장", f"naver_news_{keyword}.xlsx", "엑셀 파일 (*.xlsx)"
        )
        if not filename:
            return
        try:
            save_excel(self.results, filename)
            QMessageBox.information(self, "저장 완료 💾", f"뉴스 {len(self.results)}건을 엑셀로 저장했어요! 🎀\n{filename}")
        except OSError as e:  # 같은 파일이 엑셀에서 열려 있으면 PermissionError 발생
            QMessageBox.critical(self, "저장 실패 😢", f"{e}\n\n파일이 엑셀에서 열려 있다면 닫고 다시 시도해 주세요.")

    def closeEvent(self, event):
        if self.worker and self.worker.isRunning():
            self.worker.requestInterruption()
            self.worker.wait()
        event.accept()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")  # 스타일시트가 OS 테마와 섞이지 않도록
    app.setStyleSheet(STYLE_SHEET)
    app.setWindowIcon(QIcon(resource_path("news_bunny.ico")))
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
