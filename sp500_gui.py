"""
S&P 500 과거 데이터 분석 GUI 앱 (PyQt6)

    pip install pandas matplotlib PyQt6
    python sp500_gui.py
"""
import contextlib
import io
import sys
from pathlib import Path

import matplotlib
matplotlib.use("QtAgg")
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg, NavigationToolbar2QT
from matplotlib.figure import Figure
from PyQt6.QtCore import QDate, Qt
from PyQt6.QtGui import QColor, QFont, QIcon
from PyQt6.QtWidgets import (
    QApplication, QCheckBox, QDateEdit, QFileDialog, QFrame, QGridLayout, QHBoxLayout,
    QHeaderView, QLabel, QMainWindow, QMessageBox, QPlainTextEdit, QPushButton,
    QTableWidget, QTableWidgetItem, QTabWidget, QVBoxLayout, QWidget,
)

from sp500_analysis import DEFAULT_CSV, analyze, draw_close, draw_dashboard, load_and_clean

UP, DOWN = QColor("#2ca02c"), QColor("#d62728")


def resource_path(name):
    """PyInstaller로 묶인 exe에서는 임시 폴더(sys._MEIPASS)에서 리소스를 찾는다."""
    base = getattr(sys, "_MEIPASS", Path(__file__).resolve().parent)
    return str(Path(base) / name)


class ChartTab(QWidget):
    """matplotlib Figure + 툴바(확대/이동/저장)"""

    def __init__(self, figsize):
        super().__init__()
        self.figure = Figure(figsize=figsize)
        self.canvas = FigureCanvasQTAgg(self.figure)
        layout = QVBoxLayout(self)
        layout.addWidget(NavigationToolbar2QT(self.canvas, self))
        layout.addWidget(self.canvas)


class StatCard(QFrame):
    def __init__(self, title):
        super().__init__()
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setStyleSheet("StatCard { background: #f7f9fc; border: 1px solid #dde3ea; border-radius: 6px; }")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)
        caption = QLabel(title)
        caption.setStyleSheet("color: #667085; font-size: 11px;")
        self.value = QLabel("-")
        self.value.setStyleSheet("font-size: 18px; font-weight: bold;")
        layout.addWidget(caption)
        layout.addWidget(self.value)

    def set(self, text, color=None):
        self.value.setText(text)
        self.value.setStyleSheet(f"font-size: 18px; font-weight: bold; color: {color or '#101828'};")


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("S&P 500 데이터 분석기")
        self.resize(1300, 850)
        self.df = self.yearly = self.season = None

        # --- 상단 툴바 ---
        self.path_label = QLabel("CSV 파일을 열어 주세요")
        self.path_label.setStyleSheet("color: #475467;")
        open_btn = QPushButton("CSV 열기")
        open_btn.clicked.connect(self.open_csv)
        self.save_btn = QPushButton("정제 데이터 저장")
        self.save_btn.clicked.connect(self.save_cleaned)

        self.start_edit = QDateEdit(QDate(2000, 1, 1))
        self.end_edit = QDateEdit(QDate(2019, 12, 31))
        for edit in (self.start_edit, self.end_edit):
            edit.setCalendarPopup(True)
            edit.setDisplayFormat("yyyy-MM-dd")
            edit.dateChanged.connect(self.update_close_chart)
        self.ma_check = QCheckBox("이동평균(50/200일) 표시")
        self.ma_check.toggled.connect(self.update_close_chart)
        reset_btn = QPushButton("기간 초기화")
        reset_btn.clicked.connect(self.reset_period)

        top = QHBoxLayout()
        top.addWidget(open_btn)
        top.addWidget(self.save_btn)
        top.addWidget(self.path_label, 1)

        period = QHBoxLayout()
        period.addWidget(QLabel("기간:"))
        period.addWidget(self.start_edit)
        period.addWidget(QLabel("~"))
        period.addWidget(self.end_edit)
        period.addWidget(reset_btn)
        period.addSpacing(16)
        period.addWidget(self.ma_check)
        period.addStretch()

        # --- 요약 카드 ---
        self.cards = {name: StatCard(name) for name in
                      ["데이터 기간", "최종 종가", "총 수익률", "연평균 성장률(CAGR)", "최대 낙폭(MDD)", "연환산 변동성"]}
        cards = QGridLayout()
        for i, card in enumerate(self.cards.values()):
            cards.addWidget(card, 0, i)

        # --- 탭 ---
        self.close_tab = ChartTab((12, 5))
        self.dash_tab = ChartTab((14, 9))
        self.yearly_table = self.make_table()
        self.season_table = self.make_table()
        self.report = QPlainTextEdit(readOnly=True)
        self.report.setFont(QFont("D2Coding, Consolas", 10))

        self.tabs = QTabWidget()
        self.tabs.addTab(self.close_tab, "종가 추이")
        self.tabs.addTab(self.dash_tab, "다각도 분석")
        self.tabs.addTab(self.yearly_table, "연도별 통계")
        self.tabs.addTab(self.season_table, "월별 계절성")
        self.tabs.addTab(self.report, "분석 리포트")

        central = QWidget()
        layout = QVBoxLayout(central)
        layout.addLayout(top)
        layout.addLayout(period)
        layout.addLayout(cards)
        layout.addWidget(self.tabs, 1)
        self.setCentralWidget(central)
        self.statusBar().showMessage("준비")

        if Path(DEFAULT_CSV).exists():
            self.load(DEFAULT_CSV)

    @staticmethod
    def make_table():
        table = QTableWidget()
        table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        table.setAlternatingRowColors(True)
        table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        return table

    # ------------------------------------------------------------------
    def open_csv(self):
        path, _ = QFileDialog.getOpenFileName(self, "S&P 500 CSV 선택", str(Path(DEFAULT_CSV).parent), "CSV 파일 (*.csv)")
        if path:
            self.load(path)

    def load(self, path):
        buf = io.StringIO()
        try:
            with contextlib.redirect_stdout(buf):
                df = load_and_clean(path)
                self.df, self.yearly, self.season = analyze(df)
        except Exception as e:
            QMessageBox.critical(self, "불러오기 실패", f"파일을 분석하지 못했습니다.\n\n{e}")
            return

        self.path_label.setText(path)
        self.report.setPlainText(buf.getvalue())
        self.fill_cards()
        self.fill_table(self.yearly_table, self.yearly, index_name="연도", pct_cols={"연수익률(%)"})
        self.fill_table(self.season_table, self.season, index_name="월", pct_cols={"평균(%)", "중앙값(%)"})
        draw_dashboard(self.dash_tab.figure, self.df, self.yearly)
        self.dash_tab.canvas.draw()
        self.update_close_chart()
        self.statusBar().showMessage(
            f"{len(self.df):,}개 거래일 로드 완료 ({self.df.index.min():%Y-%m-%d} ~ {self.df.index.max():%Y-%m-%d})")

    def fill_cards(self):
        close, ret, dd = self.df["Close"], self.df["Return"], self.df["Drawdown"]
        years = (close.index[-1] - close.index[0]).days / 365.25
        total = (close.iloc[-1] / close.iloc[0] - 1) * 100
        cagr = ((close.iloc[-1] / close.iloc[0]) ** (1 / years) - 1) * 100
        color = lambda v: UP.name() if v >= 0 else DOWN.name()
        self.cards["데이터 기간"].set(f"{close.index[0]:%Y.%m} ~ {close.index[-1]:%Y.%m}")
        self.cards["최종 종가"].set(f"{close.iloc[-1]:,.2f}")
        self.cards["총 수익률"].set(f"{total:+.2f}%", color(total))
        self.cards["연평균 성장률(CAGR)"].set(f"{cagr:+.2f}%", color(cagr))
        self.cards["최대 낙폭(MDD)"].set(f"{dd.min():.2f}%", DOWN.name())
        self.cards["연환산 변동성"].set(f"{ret.std() * 252 ** 0.5:.2f}%")

    @staticmethod
    def fill_table(table, frame, index_name, pct_cols):
        table.clear()
        table.setRowCount(len(frame))
        table.setColumnCount(len(frame.columns) + 1)
        table.setHorizontalHeaderLabels([index_name, *frame.columns])
        table.verticalHeader().setVisible(False)
        for r, (idx, row) in enumerate(frame.iterrows()):
            table.setItem(r, 0, QTableWidgetItem(str(idx)))
            for c, (col, val) in enumerate(row.items(), start=1):
                item = QTableWidgetItem(f"{val:,.2f}")
                item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                if col in pct_cols:
                    item.setForeground(UP if val >= 0 else DOWN)
                table.setItem(r, c, item)

    def update_close_chart(self):
        if self.df is None:
            return
        start = self.start_edit.date().toString("yyyy-MM-dd")
        end = self.end_edit.date().toString("yyyy-MM-dd")
        if start > end:
            self.statusBar().showMessage("시작일이 종료일보다 늦습니다.")
            return
        draw_close(self.close_tab.figure, self.df, start, end, self.ma_check.isChecked())
        self.close_tab.canvas.draw()

    def reset_period(self):
        self.start_edit.setDate(QDate(2000, 1, 1))
        self.end_edit.setDate(QDate(2019, 12, 31))

    def save_cleaned(self):
        if self.df is None:
            return
        path, _ = QFileDialog.getSaveFileName(self, "정제 데이터 저장", "sp500_cleaned.csv", "CSV 파일 (*.csv)")
        if path:
            self.df.to_csv(path, encoding="utf-8-sig")
            self.statusBar().showMessage(f"저장 완료: {path}")


def main():
    app = QApplication(sys.argv)
    app.setFont(QFont("Malgun Gothic", 10))
    app.setWindowIcon(QIcon(resource_path("sp500.ico")))
    win = MainWindow()
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
