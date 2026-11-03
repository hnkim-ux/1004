"""
대한민국 출생아수 분석 GUI (PyQt6)

실행: python birth_gui.py
- 엑셀 파일 열기 -> 자동으로 클렌징/분석
- 탭: 출생아수 그래프 / 종합 대시보드 / 분석 결과 / 정제 데이터 / 분석 리포트
- 결과 내보내기: CSV, XLSX, PNG 저장
"""
import io
import numbers
import sys
from contextlib import redirect_stdout
from pathlib import Path

import matplotlib

matplotlib.use("QtAgg")  # birth_analysis가 pyplot을 import하기 전에 지정

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg, NavigationToolbar2QT
from matplotlib.figure import Figure
from PyQt6.QtCore import QAbstractTableModel, QModelIndex, Qt
from PyQt6.QtGui import QAction, QFont
from PyQt6.QtWidgets import (
    QApplication, QComboBox, QFileDialog, QGridLayout, QGroupBox, QHBoxLayout, QHeaderView,
    QLabel, QMainWindow, QMessageBox, QPlainTextEdit, QPushButton, QSpinBox, QTableView,
    QTabWidget, QVBoxLayout, QWidget,
)

from birth_analysis import DEFAULT_FILE, analyze, load_and_clean, plot_births_line, plot_dashboard, print_report

# exe(PyInstaller)로 실행 시 __file__은 임시 폴더를 가리키므로, 저장/열기 기본 위치는 exe가 있는 폴더로 지정
APP_DIR = Path(sys.executable).parent if getattr(sys, "frozen", False) else Path(__file__).parent


class DataFrameModel(QAbstractTableModel):
    """pandas DataFrame을 QTableView에 보여주는 모델"""

    def __init__(self, df: pd.DataFrame | None = None):
        super().__init__()
        self._df = df if df is not None else pd.DataFrame()

    def set_frame(self, df: pd.DataFrame):
        self.beginResetModel()
        self._df = df
        self.endResetModel()

    def rowCount(self, parent=QModelIndex()):
        return len(self._df)

    def columnCount(self, parent=QModelIndex()):
        return len(self._df.columns)

    def data(self, index, role=Qt.ItemDataRole.DisplayRole):
        if not index.isValid():
            return None
        value = self._df.iat[index.row(), index.column()]
        if role == Qt.ItemDataRole.DisplayRole:
            if pd.isna(value):
                return ""
            if isinstance(value, (bool, np.bool_)):
                return "예" if value else ""
            if isinstance(value, numbers.Integral):
                # 연도(4자리)에는 쉼표를 넣지 않음
                return f"{value:,}" if abs(value) >= 10000 else str(value)
            if isinstance(value, numbers.Real):
                return f"{value:,.0f}" if float(value).is_integer() and abs(value) >= 1000 else f"{value:,.2f}"
            return str(value)
        if role == Qt.ItemDataRole.TextAlignmentRole:
            if isinstance(value, str):
                return Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
            return Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
        return None

    def headerData(self, section, orientation, role=Qt.ItemDataRole.DisplayRole):
        if role != Qt.ItemDataRole.DisplayRole:
            return None
        if orientation == Qt.Orientation.Horizontal:
            return str(self._df.columns[section])
        return str(self._df.index[section])


class PlotWidget(QWidget):
    """matplotlib 그래프 + 확대/이동/저장 툴바"""

    def __init__(self, figsize=(13, 6)):
        super().__init__()
        self.figure = Figure(figsize=figsize)
        self.canvas = FigureCanvasQTAgg(self.figure)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(NavigationToolbar2QT(self.canvas, self))
        layout.addWidget(self.canvas)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("대한민국 출생아수 분석")
        self.resize(1300, 850)
        self.df: pd.DataFrame | None = None
        self.results: dict[str, pd.DataFrame] = {}

        self._build_menu()
        self._build_ui()
        self.statusBar().showMessage("엑셀 파일을 열어주세요 (파일 > 열기)")

        if DEFAULT_FILE.exists():
            self.load_file(DEFAULT_FILE)

    # ---------------- UI 구성 ----------------
    def _build_menu(self):
        file_menu = self.menuBar().addMenu("파일")
        open_act = QAction("열기...", self, shortcut="Ctrl+O", triggered=self.open_file)
        export_act = QAction("결과 내보내기...", self, shortcut="Ctrl+S", triggered=self.export_results)
        quit_act = QAction("종료", self, shortcut="Ctrl+Q", triggered=self.close)
        file_menu.addActions([open_act, export_act])
        file_menu.addSeparator()
        file_menu.addAction(quit_act)

        toolbar = self.addToolBar("메인")
        toolbar.setMovable(False)
        toolbar.addAction(open_act)
        toolbar.addAction(export_act)

    def _build_ui(self):
        central = QWidget()
        root = QVBoxLayout(central)

        # 상단 요약 카드
        summary_box = QGroupBox("요약")
        grid = QGridLayout(summary_box)
        self.summary_labels = {}
        keys = ["분석 기간", "최대 출생아수", "최소 출생아수", "최근 출생아수", "최저 합계출산율", "데드크로스"]
        for i, key in enumerate(keys):
            title = QLabel(key)
            title.setStyleSheet("color: gray;")
            value = QLabel("-")
            value.setFont(QFont("Malgun Gothic", 12, QFont.Weight.Bold))
            grid.addWidget(title, 0, i)
            grid.addWidget(value, 1, i)
            self.summary_labels[key] = value
        root.addWidget(summary_box)

        self.tabs = QTabWidget()
        root.addWidget(self.tabs, 1)

        # 탭1: 출생아수 라인 그래프
        line_tab = QWidget()
        lt = QVBoxLayout(line_tab)
        ctrl = QHBoxLayout()
        self.start_spin = QSpinBox()
        self.end_spin = QSpinBox()
        for spin in (self.start_spin, self.end_spin):
            spin.setRange(1900, 2100)
        self.start_spin.setValue(1970)
        self.end_spin.setValue(2025)
        draw_btn = QPushButton("그래프 그리기")
        draw_btn.clicked.connect(self.draw_line)
        ctrl.addWidget(QLabel("시작 연도"))
        ctrl.addWidget(self.start_spin)
        ctrl.addWidget(QLabel("종료 연도"))
        ctrl.addWidget(self.end_spin)
        ctrl.addWidget(draw_btn)
        ctrl.addStretch()
        lt.addLayout(ctrl)
        self.line_plot = PlotWidget((13, 6))
        lt.addWidget(self.line_plot)
        self.tabs.addTab(line_tab, "출생아수 그래프")

        # 탭2: 종합 대시보드
        self.dash_plot = PlotWidget((15, 10))
        self.tabs.addTab(self.dash_plot, "종합 대시보드")

        # 탭3: 분석 결과 표
        result_tab = QWidget()
        rt = QVBoxLayout(result_tab)
        sel = QHBoxLayout()
        sel.addWidget(QLabel("분석 항목"))
        self.result_combo = QComboBox()
        self.result_combo.currentTextChanged.connect(self.show_result)
        sel.addWidget(self.result_combo)
        sel.addStretch()
        rt.addLayout(sel)
        self.result_model = DataFrameModel()
        rt.addWidget(self._make_table(self.result_model))
        self.tabs.addTab(result_tab, "분석 결과")

        # 탭4: 정제 데이터
        self.data_model = DataFrameModel()
        self.tabs.addTab(self._make_table(self.data_model), "정제 데이터")

        # 탭5: 텍스트 리포트 (클렌징 로그 + 분석 출력)
        self.report_text = QPlainTextEdit(readOnly=True)
        self.report_text.setFont(QFont("D2Coding, Consolas, Malgun Gothic", 10))
        self.tabs.addTab(self.report_text, "분석 리포트")

        self.setCentralWidget(central)

    @staticmethod
    def _make_table(model: DataFrameModel) -> QTableView:
        view = QTableView()
        view.setModel(model)
        view.setAlternatingRowColors(True)
        view.verticalHeader().setVisible(False)
        view.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        return view

    # ---------------- 동작 ----------------
    def open_file(self):
        path, _ = QFileDialog.getOpenFileName(self, "출생아수 엑셀 파일 열기", str(APP_DIR),
                                              "Excel 파일 (*.xlsx *.xls)")
        if path:
            self.load_file(Path(path))

    def load_file(self, path: Path):
        log = io.StringIO()
        try:
            with redirect_stdout(log):
                df = load_and_clean(path)
                results = analyze(df)
                print_report(df, results)
        except Exception as e:
            QMessageBox.critical(self, "불러오기 실패", f"파일을 처리하지 못했습니다.\n\n{e}")
            return

        self.df, self.results = df, results
        self.report_text.setPlainText(log.getvalue())
        self.data_model.set_frame(df.reset_index())

        self.result_combo.blockSignals(True)
        self.result_combo.clear()
        self.result_combo.addItems(results.keys())
        self.result_combo.blockSignals(False)
        self.show_result(self.result_combo.currentText())

        lo, hi = int(df.index.min()), int(df.index.max())
        for spin in (self.start_spin, self.end_spin):
            spin.setRange(lo, hi)
        self.start_spin.setValue(max(lo, 1970))
        self.end_spin.setValue(min(hi, 2025))

        self.update_summary()
        self.draw_line()
        plot_dashboard(df, fig=self.dash_plot.figure)
        self.dash_plot.canvas.draw_idle()
        self.statusBar().showMessage(f"불러옴: {path}  ({lo}~{hi}, {len(df)}개 연도)")

    def update_summary(self):
        df, b, tfr = self.df, self.df["출생아수"], self.df["합계출산율"]
        last = df.index.max()
        cross = df[df["자연증가건수"] < 0].index.min()
        prov = " (잠정)" if df.loc[last, "잠정치"] else ""
        values = {
            "분석 기간": f"{df.index.min()}~{last}",
            "최대 출생아수": f"{b.max():,}명 ({b.idxmax()})",
            "최소 출생아수": f"{b.min():,}명 ({b.idxmin()})",
            "최근 출생아수": f"{b[last]:,}명 ({last}{prov})",
            "최저 합계출산율": f"{tfr.min()}명 ({tfr.idxmin()})",
            "데드크로스": f"{cross}년" if pd.notna(cross) else "없음",
        }
        for key, text in values.items():
            self.summary_labels[key].setText(text)

    def draw_line(self):
        if self.df is None:
            return
        start, end = self.start_spin.value(), self.end_spin.value()
        if start >= end:
            QMessageBox.warning(self, "연도 오류", "시작 연도는 종료 연도보다 작아야 합니다.")
            return
        plot_births_line(self.df, start, end, fig=self.line_plot.figure)
        self.line_plot.canvas.draw_idle()

    def show_result(self, name: str):
        if name in self.results:
            table = self.results[name]
            # 인덱스가 의미 있는 표(연대, 지표명 등)는 컬럼으로 꺼내서 보여줌
            if not isinstance(table.index, pd.RangeIndex):
                table = table.reset_index(names=table.index.name or "구분")
            self.result_model.set_frame(table)

    def export_results(self):
        if self.df is None:
            QMessageBox.information(self, "안내", "먼저 엑셀 파일을 열어주세요.")
            return
        folder = QFileDialog.getExistingDirectory(self, "저장할 폴더 선택", str(APP_DIR))
        if not folder:
            return
        out = Path(folder)
        try:
            self.df.to_csv(out / "births_clean.csv", encoding="utf-8-sig")
            with pd.ExcelWriter(out / "births_analysis.xlsx") as writer:
                self.df.to_excel(writer, sheet_name="정제데이터")
                for name, table in self.results.items():
                    table.to_excel(writer, sheet_name=name)
            start, end = self.start_spin.value(), self.end_spin.value()
            for fig in (plot_births_line(self.df, start, end, save_path=out / f"births_line_{start}_{end}.png"),
                        plot_dashboard(self.df, save_path=out / "births_dashboard.png")):
                plt.close(fig)
        except PermissionError:
            QMessageBox.critical(self, "저장 실패", "파일이 다른 프로그램(엑셀 등)에서 열려 있는지 확인해주세요.")
            return
        QMessageBox.information(self, "저장 완료", f"결과를 저장했습니다.\n{out}")


def main():
    app = QApplication(sys.argv)
    app.setFont(QFont("Malgun Gothic", 10))
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
