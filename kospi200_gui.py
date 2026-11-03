"""
코스피200 지수와 구성종목 시세를 보여주는 GUI 앱 (PyQt6)
데이터 수집은 kospi200_crawler.py 의 함수를 그대로 사용한다.

사용법:
    pip install requests openpyxl PyQt6
    python kospi200_gui.py
"""

import os
import sys
from datetime import datetime

import requests
from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from PyQt6.QtCore import Qt, QThread, QTimer, QUrl, pyqtSignal
from PyQt6.QtGui import QColor, QDesktopServices, QIcon
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QCheckBox,
    QFileDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from kospi200_crawler import (
    HEADERS,
    INDEX_FIELDS,
    STOCK_FIELDS,
    fetch_constituents,
    fetch_expected_count,
    fetch_index,
    save_csv,
)

AUTO_REFRESH_MS = 60_000  # 자동 새로고침 간격 (1분)
STOCK_PAGE_URL = "https://m.stock.naver.com/domestic/stock/{code}/total"

# 한국 증시 관례: 상승 빨강, 하락 파랑
UP_COLOR = "#E5484D"
DOWN_COLOR = "#3B82F6"
FLAT_COLOR = "#8A8FA3"

# 표에 보여줄 칼럼 (STOCK_FIELDS 중 기준시각 제외)
TABLE_FIELDS = ["순위", "종목코드", "종목명", "현재가", "전일비", "등락률(%)",
                "거래량", "거래대금(백만)", "시가총액(억)"]
NUMERIC_FIELDS = {"순위", "현재가", "전일비", "등락률(%)", "거래량", "거래대금(백만)", "시가총액(억)"}

STYLE_SHEET = """
QWidget {
    font-family: "Malgun Gothic";
    font-size: 10.5pt;
    color: #3E4A61;
}
QMainWindow, QWidget#central { background-color: #F3F8FF; }
QLabel#title {
    font-size: 19pt;
    font-weight: bold;
    color: #4C7BF4;
}
QLabel#subtitle { color: #9AA8C7; }
QFrame#card {
    background: #FFFFFF;
    border: 2px solid #DCE8FF;
    border-radius: 18px;
}
QLabel#indexName  { font-size: 11pt; font-weight: bold; color: #6B7A99; }
QLabel#indexValue { font-size: 28pt; font-weight: bold; }
QLabel#indexChange { font-size: 13pt; font-weight: bold; }
QLabel#statKey   { color: #9AA8C7; font-size: 9.5pt; }
QLabel#statValue { font-weight: bold; }
QLineEdit {
    background: #FFFFFF;
    border: 2px solid #CFE0FF;
    border-radius: 16px;
    padding: 6px 14px;
}
QLineEdit:focus { border: 2px solid #7FA6FF; }
QPushButton {
    border: none;
    border-radius: 16px;
    padding: 8px 16px;
    font-weight: bold;
    color: #FFFFFF;
    background-color: #6A95FF;
}
QPushButton:hover   { background-color: #557FF0; }
QPushButton:pressed { background-color: #4169DB; }
QPushButton:disabled { background-color: #E3EAF7; }
QPushButton#csvBtn          { background-color: #B9A3F0; }
QPushButton#csvBtn:hover    { background-color: #A68CEB; }
QPushButton#excelBtn        { background-color: #5FCFA8; }
QPushButton#excelBtn:hover  { background-color: #47BF95; }
QPushButton#csvBtn:disabled, QPushButton#excelBtn:disabled { background-color: #E8E6F2; }
QCheckBox { color: #6B7A99; spacing: 6px; }
QTableWidget {
    background: #FFFFFF;
    border: 2px solid #DCE8FF;
    border-radius: 16px;
    padding: 4px;
    gridline-color: transparent;
    alternate-background-color: #F8FBFF;
    selection-background-color: #E4EDFF;
    selection-color: #3E4A61;
    outline: 0;
}
QTableWidget::item { padding: 4px 6px; }
QHeaderView::section {
    background-color: #E8F0FF;
    color: #4C7BF4;
    font-weight: bold;
    border: none;
    padding: 7px;
}
QProgressBar {
    background: #FFFFFF;
    border: 2px solid #DCE8FF;
    border-radius: 8px;
    height: 12px;
}
QProgressBar::chunk {
    border-radius: 6px;
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #9DBBFF, stop:1 #7FE0C0);
}
QScrollBar:vertical { background: transparent; width: 10px; margin: 4px; }
QScrollBar::handle:vertical { background: #CFE0FF; border-radius: 5px; min-height: 30px; }
QScrollBar::add-line, QScrollBar::sub-line { height: 0; }
QScrollBar::add-page, QScrollBar::sub-page { background: none; }
"""


def resource_path(name):
    """PyInstaller로 묶인 exe에서는 임시 폴더(sys._MEIPASS)에서 리소스를 찾는다."""
    base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, name)


def to_number(text):
    """'1,234.5' / '-37.08' 같은 문자열을 정렬용 숫자로 변환 (실패 시 0)"""
    try:
        return float(str(text).replace(",", "").replace("+", ""))
    except ValueError:
        return 0.0


def change_color(value):
    number = to_number(value)
    return UP_COLOR if number > 0 else DOWN_COLOR if number < 0 else FLAT_COLOR


def signed(value):
    """양수에 + 를 붙이고, 상승/하락 화살표를 앞에 붙인다."""
    number = to_number(value)
    text = str(value)
    if number > 0 and not text.startswith("+"):
        text = "+" + text
    arrow = "▲" if number > 0 else "▼" if number < 0 else "−"
    return f"{arrow} {text}"


def save_excel(rows, filename):
    widths = {"순위": 6, "종목코드": 10, "종목명": 22, "기준시각": 20}
    wb = Workbook()
    ws = wb.active
    ws.title = "코스피200"
    ws.append(STOCK_FIELDS)
    for col, field in enumerate(STOCK_FIELDS, 1):
        cell = ws.cell(row=1, column=col)
        cell.font = Font(bold=True, color="FFFFFF")
        cell.fill = PatternFill("solid", fgColor="6A95FF")
        cell.alignment = Alignment(horizontal="center")
        ws.column_dimensions[cell.column_letter].width = widths.get(field, 14)

    for r in rows:
        values = []
        for field in STOCK_FIELDS:
            value = r.get(field, "")
            # 숫자 칼럼은 엑셀에서 계산/정렬이 되도록 숫자로 저장
            values.append(to_number(value) if field in NUMERIC_FIELDS and value != "" else value)
        ws.append(values)
        color = change_color(r.get("전일비")).lstrip("#")
        for col in (STOCK_FIELDS.index("전일비") + 1, STOCK_FIELDS.index("등락률(%)") + 1):
            ws.cell(row=ws.max_row, column=col).font = Font(color=color)

    for field in ("현재가", "전일비", "거래량", "거래대금(백만)", "시가총액(억)"):
        letter = ws.cell(row=1, column=STOCK_FIELDS.index(field) + 1).column_letter
        for cell in ws[letter][1:]:
            cell.number_format = "#,##0.##"
    ws.freeze_panes = "A2"
    ws.auto_filter.ref = ws.dimensions
    wb.save(filename)


class NumericItem(QTableWidgetItem):
    """숫자 크기로 정렬되는 표 셀 (문자열 정렬이면 '9,000'이 '10,000'보다 뒤로 감)"""

    def __lt__(self, other):
        return self.data(Qt.ItemDataRole.UserRole) < other.data(Qt.ItemDataRole.UserRole)


# ─────────────────────────────────────────────
# 백그라운드 수집 스레드 (GUI 멈춤 방지)
# ─────────────────────────────────────────────
class FetchWorker(QThread):
    done = pyqtSignal(dict, list, object)   # (지수, 구성종목, 기대 종목 수)
    failed = pyqtSignal(str)

    def run(self):
        try:
            with requests.Session() as session:
                session.headers.update(HEADERS)
                index = fetch_index(session)
                stocks = fetch_constituents(session)
                expected = fetch_expected_count(session)
        except (requests.RequestException, KeyError, IndexError, ValueError) as e:
            self.failed.emit(f"데이터를 가져오지 못했어요: {e}")
            return
        self.done.emit(index, stocks, expected)


# ─────────────────────────────────────────────
# 메인 윈도우
# ─────────────────────────────────────────────
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("📈 코스피200 시세판")
        self.resize(1150, 780)
        self.index = {}
        self.stocks = []
        self.worker = None

        title = QLabel("📈 코스피200 시세판")
        title.setObjectName("title")
        subtitle = QLabel("네이버 증권 데이터로 코스피200 지수와 구성종목을 한눈에 볼 수 있어요")
        subtitle.setObjectName("subtitle")

        # 지수 카드
        card = QFrame()
        card.setObjectName("card")
        self.index_name = QLabel("코스피 200")
        self.index_name.setObjectName("indexName")
        self.index_value = QLabel("-")
        self.index_value.setObjectName("indexValue")
        self.index_change = QLabel("")
        self.index_change.setObjectName("indexChange")
        self.index_time = QLabel("")
        self.index_time.setObjectName("statKey")

        left = QVBoxLayout()
        left.addWidget(self.index_name)
        left.addWidget(self.index_value)
        left.addWidget(self.index_change)
        left.addWidget(self.index_time)

        self.stat_labels = {}
        stats = QGridLayout()
        stats.setHorizontalSpacing(28)
        for i, key in enumerate(["시가", "고가", "저가", "거래량", "거래대금", "구성종목"]):
            k = QLabel(key)
            k.setObjectName("statKey")
            v = QLabel("-")
            v.setObjectName("statValue")
            self.stat_labels[key] = v
            stats.addWidget(k, (i // 3) * 2, i % 3)
            stats.addWidget(v, (i // 3) * 2 + 1, i % 3)

        card_layout = QHBoxLayout(card)
        card_layout.setContentsMargins(24, 16, 24, 16)
        card_layout.addLayout(left, 1)
        card_layout.addLayout(stats, 2)

        # 도구 모음
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("🔍 종목명 또는 종목코드로 찾기")
        self.search_edit.textChanged.connect(self.apply_filter)

        self.refresh_btn = QPushButton("🔄 새로고침")
        self.refresh_btn.clicked.connect(self.refresh)
        self.auto_check = QCheckBox("1분마다 자동 새로고침")
        self.auto_check.toggled.connect(self.toggle_auto_refresh)
        self.csv_btn = QPushButton("📝 CSV 저장")
        self.csv_btn.setObjectName("csvBtn")
        self.csv_btn.clicked.connect(self.save_results_csv)
        self.excel_btn = QPushButton("📊 엑셀 저장")
        self.excel_btn.setObjectName("excelBtn")
        self.excel_btn.clicked.connect(self.save_results_excel)
        for btn in (self.refresh_btn, self.csv_btn, self.excel_btn):
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.csv_btn.setEnabled(False)
        self.excel_btn.setEnabled(False)

        tools = QHBoxLayout()
        tools.setSpacing(8)
        tools.addWidget(self.search_edit, 1)
        tools.addWidget(self.auto_check)
        tools.addWidget(self.refresh_btn)
        tools.addWidget(self.csv_btn)
        tools.addWidget(self.excel_btn)

        # 구성종목 표
        self.table = QTableWidget(0, len(TABLE_FIELDS))
        self.table.setHorizontalHeaderLabels(TABLE_FIELDS)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.table.setAlternatingRowColors(True)
        self.table.setShowGrid(False)
        self.table.verticalHeader().setVisible(False)
        self.table.verticalHeader().setDefaultSectionSize(30)
        header = self.table.horizontalHeader()
        header.setSortIndicator(0, Qt.SortOrder.AscendingOrder)  # 처음엔 순위(시가총액) 오름차순
        self.table.setSortingEnabled(True)
        header.setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.table.cellDoubleClicked.connect(self.open_stock_page)

        # 상태 표시줄
        self.status_label = QLabel("💡 표 머리글을 누르면 정렬, 종목을 더블클릭하면 네이버 증권이 열려요")
        self.progress = QProgressBar()
        self.progress.setRange(0, 0)  # 진행률 대신 움직이는 막대
        self.progress.setFixedWidth(200)
        self.progress.setVisible(False)
        bottom = QHBoxLayout()
        bottom.addWidget(self.status_label, 1)
        bottom.addWidget(self.progress)

        layout = QVBoxLayout()
        layout.setContentsMargins(18, 14, 18, 12)
        layout.setSpacing(10)
        layout.addWidget(title)
        layout.addWidget(subtitle)
        layout.addWidget(card)
        layout.addLayout(tools)
        layout.addWidget(self.table, 1)
        layout.addLayout(bottom)
        container = QWidget()
        container.setObjectName("central")
        container.setLayout(layout)
        self.setCentralWidget(container)

        self.timer = QTimer(self)
        self.timer.setInterval(AUTO_REFRESH_MS)
        self.timer.timeout.connect(self.refresh)

        QTimer.singleShot(0, self.refresh)  # 앱을 열면 바로 한 번 수집

    # ── 수집 ──
    def refresh(self):
        if self.worker and self.worker.isRunning():
            return
        self.refresh_btn.setEnabled(False)
        self.progress.setVisible(True)
        self.status_label.setText("🐢 코스피200 데이터를 가져오는 중이에요... (5페이지, 약 3초)")

        self.worker = FetchWorker()
        self.worker.done.connect(self.on_done)
        self.worker.failed.connect(self.on_failed)
        self.worker.finished.connect(self.on_finished)
        self.worker.start()

    def on_done(self, index, stocks, expected):
        self.index, self.stocks = index, stocks
        self.show_index(index, len(stocks), expected)
        self.fill_table(stocks)
        self.apply_filter()
        self.csv_btn.setEnabled(True)
        self.excel_btn.setEnabled(True)

        check = ""
        if expected is not None:
            check = " (지수 구성종목 수와 일치 ✅)" if expected == len(stocks) else f" (⚠️ 지수 기준 {expected}개와 다름)"
        now = datetime.now().strftime("%H:%M:%S")
        self.status_label.setText(f"🎉 구성종목 {len(stocks)}개를 가져왔어요{check}  ·  {now} 업데이트")

    def on_failed(self, message):
        self.status_label.setText(f"😵 {message}")
        if not self.auto_check.isChecked():  # 자동 새로고침 중에는 팝업으로 방해하지 않음
            QMessageBox.critical(self, "앗, 문제가 생겼어요", message)

    def on_finished(self):
        self.refresh_btn.setEnabled(True)
        self.progress.setVisible(False)

    def toggle_auto_refresh(self, checked):
        if checked:
            self.timer.start()
        else:
            self.timer.stop()

    # ── 화면 표시 ──
    def show_index(self, index, count, expected):
        color = change_color(index["전일대비"])
        self.index_name.setText(f"{index['지수명']}  ·  {index['장상태']}")
        self.index_value.setText(str(index["현재값"]))
        self.index_value.setStyleSheet(f"color: {color};")
        self.index_change.setText(f"{signed(index['전일대비'])}  ({signed(index['등락률(%)'])[2:]}%)")
        self.index_change.setStyleSheet(f"color: {color};")
        self.index_time.setText(f"기준시각 {index['기준시각']}")

        self.stat_labels["시가"].setText(str(index["시가"]))
        self.stat_labels["고가"].setText(str(index["고가"]))
        self.stat_labels["저가"].setText(str(index["저가"]))
        self.stat_labels["거래량"].setText(str(index["거래량"]))      # API 값에 단위(천주)가 포함됨
        self.stat_labels["거래대금"].setText(str(index["거래대금"]))  # API 값에 단위(백만)가 포함됨
        self.stat_labels["구성종목"].setText(f"{count}개" + (f" / {expected}개" if expected else ""))

    def fill_table(self, stocks):
        self.table.setSortingEnabled(False)  # 채우는 동안 정렬을 끄지 않으면 행이 섞임
        self.table.setRowCount(len(stocks))
        for row, stock in enumerate(stocks):
            color = QColor(change_color(stock["전일비"]))
            for col, field in enumerate(TABLE_FIELDS):
                value = stock.get(field, "")
                if field in NUMERIC_FIELDS:
                    text = signed(value) if field == "전일비" else str(value)
                    if field == "등락률(%)":
                        text = f"{value}%"
                    item = NumericItem(text)
                    item.setData(Qt.ItemDataRole.UserRole, to_number(value))
                    item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                else:
                    item = QTableWidgetItem(str(value))
                    if field == "종목코드":
                        item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                if field in ("현재가", "전일비", "등락률(%)"):
                    item.setForeground(color)
                self.table.setItem(row, col, item)
        self.table.setSortingEnabled(True)

    def apply_filter(self):
        keyword = self.search_edit.text().strip().lower()
        name_col = TABLE_FIELDS.index("종목명")
        code_col = TABLE_FIELDS.index("종목코드")
        shown = 0
        for row in range(self.table.rowCount()):
            name = self.table.item(row, name_col).text().lower()
            code = self.table.item(row, code_col).text()
            hidden = bool(keyword) and keyword not in name and keyword not in code
            self.table.setRowHidden(row, hidden)
            shown += not hidden
        if keyword:
            self.status_label.setText(f"🔍 '{keyword}' 검색 결과 {shown}개")

    def open_stock_page(self, row, _col):
        code = self.table.item(row, TABLE_FIELDS.index("종목코드")).text()
        QDesktopServices.openUrl(QUrl(STOCK_PAGE_URL.format(code=code)))

    # ── 저장 ──
    def default_name(self, ext):
        return f"kospi200_stocks_{datetime.now().strftime('%Y%m%d_%H%M')}.{ext}"

    def save_results_csv(self):
        filename, _ = QFileDialog.getSaveFileName(self, "CSV 저장", self.default_name("csv"), "CSV 파일 (*.csv)")
        if not filename:
            return
        try:
            save_csv(filename, STOCK_FIELDS, self.stocks)
            # 지수 정보는 같은 위치에 _index 파일로 함께 저장
            index_file = os.path.splitext(filename)[0] + "_index.csv"
            save_csv(index_file, INDEX_FIELDS, [self.index])
            QMessageBox.information(self, "저장 완료 💾", f"구성종목 {len(self.stocks)}개와 지수 정보를 저장했어요.\n{filename}\n{index_file}")
        except OSError as e:
            QMessageBox.critical(self, "저장 실패", str(e))

    def save_results_excel(self):
        filename, _ = QFileDialog.getSaveFileName(self, "엑셀 저장", self.default_name("xlsx"), "엑셀 파일 (*.xlsx)")
        if not filename:
            return
        try:
            save_excel(self.stocks, filename)
            QMessageBox.information(self, "저장 완료 💾", f"구성종목 {len(self.stocks)}개를 엑셀로 저장했어요.\n{filename}")
        except OSError as e:  # 같은 파일이 엑셀에서 열려 있으면 PermissionError 발생
            QMessageBox.critical(self, "저장 실패", f"{e}\n\n파일이 엑셀에서 열려 있다면 닫고 다시 시도해 주세요.")

    def closeEvent(self, event):
        self.timer.stop()
        if self.worker and self.worker.isRunning():
            self.worker.wait()
        event.accept()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")  # 스타일시트가 OS 테마와 섞이지 않도록
    app.setStyleSheet(STYLE_SHEET)
    app.setWindowIcon(QIcon(resource_path("kospi200.ico")))
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
