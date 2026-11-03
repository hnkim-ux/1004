"""
대한민국 출생아수·합계출산율·자연증가 데이터 클렌징 및 분석 (출처: 통계청 KOSIS 인구동향조사)

실행: python birth_analysis.py [엑셀파일경로]
결과: output/ 폴더에 정제 데이터(CSV), 분석 결과(XLSX), 그래프(PNG) 저장
"""
import re
import sys
import warnings
from pathlib import Path

import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import pandas as pd

warnings.filterwarnings("ignore", category=UserWarning, module="openpyxl")

BASE_DIR = Path(__file__).parent
DEFAULT_FILE = BASE_DIR / "data" / "births.xlsx"
OUT_DIR = BASE_DIR / "output"

# 원본 항목명 -> 분석용 컬럼명
COLUMN_MAP = {
    "출생아수(명)": "출생아수",
    "자연증가건수(명)": "자연증가건수",
    "조출생률(천명당)": "조출생률",
    "자연증가율(천명당)": "자연증가율",
    "합계출산율(명)": "합계출산율",
    "출생성비(명)": "출생성비",
}

plt.rcParams["font.family"] = "Malgun Gothic"  # 윈도우 한글 폰트
plt.rcParams["axes.unicode_minus"] = False


# ---------------------------------------------------------------------------
# 1. 데이터 클렌징
# ---------------------------------------------------------------------------
def load_and_clean(path: Path) -> pd.DataFrame:
    # 첫 번째 시트(데이터)만 사용, 두 번째 시트는 메타정보
    raw = pd.read_excel(path, sheet_name=0, header=0)
    print(f"[원본] shape={raw.shape}  (행=지표, 열=연도: 가로형 구조)")

    # (1) 지표명을 인덱스로 하고 행/열 전치 -> 연도별 세로형(tidy) 구조
    raw = raw.rename(columns={raw.columns[0]: "항목"})
    raw["항목"] = raw["항목"].astype(str).str.strip()
    df = raw.set_index("항목").T

    # (2) 컬럼명 정리: 단위 표기 제거
    df = df.rename(columns=COLUMN_MAP)
    df.columns.name = None

    # (3) 연도 파싱: '2025 p)' 같은 잠정치 표기 분리
    year_str = df.index.astype(str).str.strip()
    df["잠정치"] = year_str.str.contains(r"p\)", regex=True)
    df.index = [int(float(re.match(r"\d{4}(\.0)?", y).group())) for y in year_str]
    df.index.name = "연도"

    # (4) 숫자형 변환 (쉼표, '-' 등 비정상 값은 NaN 처리)
    value_cols = list(COLUMN_MAP.values())
    for col in value_cols:
        df[col] = pd.to_numeric(
            df[col].astype(str).str.replace(",", "").str.strip(), errors="coerce"
        )

    # (5) 품질 점검: 결측, 중복 연도, 연속성
    missing = df[value_cols].isna().sum()
    dup_years = df.index.duplicated().sum()
    full_range = set(range(df.index.min(), df.index.max() + 1))
    gaps = sorted(full_range - set(df.index))
    print(f"[점검] 결측치: {missing.to_dict()}")
    print(f"[점검] 중복 연도: {dup_years}개, 누락 연도: {gaps or '없음'}")

    df = df[~df.index.duplicated(keep="last")].sort_index()
    if missing.any():
        df[value_cols] = df[value_cols].interpolate(limit_area="inside")

    # (6) 자료형 정리: 건수는 정수, 비율은 실수
    for col in ["출생아수", "자연증가건수"]:
        df[col] = df[col].round().astype("int64")

    # (7) 파생 변수: 사망자수 = 출생아수 - 자연증가건수
    df["사망자수"] = df["출생아수"] - df["자연증가건수"]

    print(f"[정제] shape={df.shape}, 기간 {df.index.min()}~{df.index.max()}\n")
    return df


# ---------------------------------------------------------------------------
# 2. 다각도 분석
# ---------------------------------------------------------------------------
def analyze(df: pd.DataFrame) -> dict[str, pd.DataFrame]:
    results = {}
    b = df["출생아수"]

    # 2-1. 기술통계
    results["기술통계"] = df.drop(columns="잠정치").describe().T.round(2)

    # 2-2. 전년 대비 증감
    yoy = pd.DataFrame({
        "출생아수": b,
        "증감(명)": b.diff(),
        "증감률(%)": (b.pct_change() * 100).round(2),
        "합계출산율": df["합계출산율"],
    })
    results["전년대비증감"] = yoy

    # 2-3. 연대별 평균
    decade = df.drop(columns="잠정치").groupby((df.index // 10) * 10).agg({
        "출생아수": "mean", "사망자수": "mean", "자연증가건수": "mean",
        "합계출산율": "mean", "출생성비": "mean",
    }).round(2)
    decade.index = [f"{d}년대" for d in decade.index]
    results["연대별평균"] = decade

    # 2-4. 주요 시점(이정표)
    tfr = df["합계출산율"]
    milestones = [
        ("출생아수 최대", b.idxmax(), f"{b.max():,}명"),
        ("출생아수 최소", b.idxmin(), f"{b.min():,}명"),
        ("최대 감소폭", yoy["증감(명)"].idxmin(), f"{yoy['증감(명)'].min():,.0f}명"),
        ("합계출산율 대체수준(2.1) 미만 진입", tfr[tfr < 2.1].index.min(), ""),
        ("초저출산(1.3) 미만 진입", tfr[tfr < 1.3].index.min(), ""),
        ("합계출산율 1.0 미만 진입", tfr[tfr < 1.0].index.min(), ""),
        ("합계출산율 최저", tfr.idxmin(), f"{tfr.min()}명"),
        ("인구 데드크로스(자연감소 시작)", df[df["자연증가건수"] < 0].index.min(), ""),
        ("출생성비 최고", df["출생성비"].idxmax(), f"{df['출생성비'].max()}"),
    ]
    results["주요시점"] = pd.DataFrame(milestones, columns=["구분", "연도", "값"])

    # 2-5. 1970년 대비 및 연평균 증감률(CAGR)
    start, end = df.index.min(), df.index.max()
    years = end - start
    cagr = (b[end] / b[start]) ** (1 / years) - 1
    results["장기변화"] = pd.DataFrame({
        "항목": ["시작연도 출생아수", "최근연도 출생아수", "감소율(%)", "연평균증감률 CAGR(%)"],
        "값": [b[start], b[end], round((b[end] / b[start] - 1) * 100, 2), round(cagr * 100, 2)],
    })

    # 2-6. 지표 간 상관관계
    results["상관관계"] = df[["출생아수", "조출생률", "합계출산율", "사망자수", "출생성비"]].corr().round(3)

    # 2-7. 연속 감소 구간
    down = (b.diff() < 0).astype(int)
    group = (down != down.shift()).cumsum()
    streaks = (
        pd.DataFrame({"감소": down, "grp": group})
        .query("감소 == 1").groupby("grp")
        .apply(lambda g: pd.Series({"시작": g.index.min(), "종료": g.index.max(), "연속(년)": len(g)}),
               include_groups=False)
        .sort_values("연속(년)", ascending=False).reset_index(drop=True)
    )
    results["연속감소구간"] = streaks.head(5)

    return results


def print_report(df: pd.DataFrame, results: dict[str, pd.DataFrame]) -> None:
    pd.set_option("display.width", 200)
    pd.set_option("display.float_format", lambda v: f"{v:,.2f}")
    for name in ["기술통계", "연대별평균", "주요시점", "장기변화", "상관관계", "연속감소구간"]:
        print(f"=== {name} ===")
        print(results[name].to_string())
        print()
    print("=== 최근 10년 전년대비 증감 ===")
    print(results["전년대비증감"].tail(10).to_string())
    if df["잠정치"].any():
        print(f"\n※ {', '.join(map(str, df.index[df['잠정치']]))}년은 잠정치(p)입니다.")


# ---------------------------------------------------------------------------
# 3. 시각화
# ---------------------------------------------------------------------------
def plot_births_line(df: pd.DataFrame, start: int = 1970, end: int = 2025,
                     save_path: Path | None = None, fig=None):
    """출생아수 연도별 라인 그래프 (start~end). fig를 넘기면 그 위에 그림(GUI 임베드용)"""
    data = df.loc[start:end, "출생아수"]

    if fig is None:
        fig = plt.figure(figsize=(13, 6))
    fig.clear()
    ax = fig.add_subplot()
    ax.plot(data.index, data.values, color="#2E6BD9", linewidth=2.2, marker="o", markersize=3.5)
    ax.fill_between(data.index, data.values, alpha=0.08, color="#2E6BD9")

    # 최대/최소/최근값 표시
    for year, label in [(data.idxmax(), "최대"), (data.idxmin(), "최소"), (data.index[-1], "최근")]:
        val = data[year]
        ax.annotate(f"{label} {year}년\n{val:,.0f}명", xy=(year, val),
                    xytext=(0, 18 if label != "최소" else -38), textcoords="offset points",
                    ha="center", fontsize=9, arrowprops=dict(arrowstyle="-", color="gray"))

    # 잠정치 구간 점선 표시
    prov = df.loc[start:end].index[df.loc[start:end, "잠정치"]]
    if len(prov):
        ax.plot(data.loc[prov[0] - 1:].index, data.loc[prov[0] - 1:].values,
                color="white", linewidth=1.2, linestyle=(0, (2, 2)))

    ax.set_title(f"대한민국 연도별 출생아수 ({start}~{end})", fontsize=15, fontweight="bold", pad=15)
    ax.set_xlabel("연도")
    ax.set_ylabel("출생아수 (명)")
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda v, _: f"{v / 10000:,.0f}만"))
    ax.set_xticks(range(start, end + 1, 5))
    ax.set_xlim(start - 1, end + 1)
    ax.set_ylim(0, data.max() * 1.15)
    ax.grid(axis="y", alpha=0.3)
    ax.spines[["top", "right"]].set_visible(False)
    note = f" ({', '.join(map(str, prov))}년 잠정치)" if len(prov) else ""
    fig.text(0.99, 0.01, f"자료: 통계청 KOSIS 인구동향조사{note}", ha="right", fontsize=8, color="gray")
    fig.tight_layout()

    if save_path:
        fig.savefig(save_path, dpi=150)
    return fig


def plot_dashboard(df: pd.DataFrame, save_path: Path | None = None, fig=None):
    """다각도 분석 4분할 그래프. fig를 넘기면 그 위에 그림(GUI 임베드용)"""
    if fig is None:
        fig = plt.figure(figsize=(15, 10))
    fig.clear()
    axes = fig.subplots(2, 2)

    # (1) 출생아수 vs 사망자수 -> 데드크로스
    ax = axes[0, 0]
    ax.plot(df.index, df["출생아수"] / 10000, label="출생아수", color="#2E6BD9", lw=2)
    ax.plot(df.index, df["사망자수"] / 10000, label="사망자수", color="#D9534F", lw=2)
    cross = df[df["자연증가건수"] < 0].index.min()
    ax.axvline(cross, color="gray", ls="--", lw=1)
    ax.text(cross, ax.get_ylim()[1] * 0.9, f" 데드크로스\n {cross}년", fontsize=9)
    ax.set_title("출생아수 vs 사망자수 (만 명)")
    ax.legend()

    # (2) 합계출산율 + 기준선
    ax = axes[0, 1]
    ax.plot(df.index, df["합계출산율"], color="#5CB85C", lw=2, marker="o", ms=3)
    for y, lbl in [(2.1, "대체출산율 2.1"), (1.3, "초저출산 1.3"), (1.0, "1.0")]:
        ax.axhline(y, color="gray", ls=":", lw=1)
        ax.text(df.index.max(), y, f" {lbl}", va="center", fontsize=8)
    ax.set_title("합계출산율 (명)")

    # (3) 전년 대비 증감률
    ax = axes[1, 0]
    pct = df["출생아수"].pct_change() * 100
    ax.bar(pct.index, pct, color=["#D9534F" if v < 0 else "#2E6BD9" for v in pct])
    ax.axhline(0, color="black", lw=0.8)
    ax.set_title("출생아수 전년 대비 증감률 (%)")

    # (4) 출생성비
    ax = axes[1, 1]
    ax.plot(df.index, df["출생성비"], color="#8E44AD", lw=2)
    ax.axhspan(103, 107, color="#8E44AD", alpha=0.1, label="자연 성비 범위(103~107)")
    ax.set_title("출생성비 (여아 100명당 남아)")
    ax.legend()

    for ax in axes.flat:
        ax.grid(alpha=0.3)
        ax.spines[["top", "right"]].set_visible(False)
    fig.suptitle(f"대한민국 출생 관련 지표 종합 ({df.index.min()}~{df.index.max()})",
                 fontsize=16, fontweight="bold")
    fig.tight_layout()
    if save_path:
        fig.savefig(save_path, dpi=150)
    return fig


# ---------------------------------------------------------------------------
def main():
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_FILE
    OUT_DIR.mkdir(exist_ok=True)

    df = load_and_clean(path)
    df.to_csv(OUT_DIR / "births_clean.csv", encoding="utf-8-sig")

    results = analyze(df)
    print_report(df, results)
    with pd.ExcelWriter(OUT_DIR / "births_analysis.xlsx") as writer:
        df.to_excel(writer, sheet_name="정제데이터")
        for name, table in results.items():
            table.to_excel(writer, sheet_name=name)

    plot_births_line(df, 1970, 2025, save_path=OUT_DIR / "births_line_1970_2025.png")
    plot_dashboard(df, OUT_DIR / "births_dashboard.png")
    print(f"\n결과 저장 위치: {OUT_DIR.resolve()}")
    plt.show()


if __name__ == "__main__":
    main()
