"""S&P 500 과거 데이터 클렌징 + 다각도 분석 + 종가 라인그래프 (2000.01 ~ 2019.12)"""
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

DEFAULT_CSV = r"C:\Users\user\Downloads\생산성본부_바이브코딩수업\DataSet\S&P 500 과거 데이터.csv"
OUT_DIR = Path(__file__).parent / "sp500_output"

plt.rcParams["font.family"] = "Malgun Gothic"   # 한글 폰트 (Windows)
plt.rcParams["axes.unicode_minus"] = False
pd.set_option("display.width", 120)
pd.set_option("display.float_format", "{:,.2f}".format)


def section(title):
    print(f"\n{'=' * 70}\n {title}\n{'=' * 70}")


# ------------------------------------------------------------------
# 1. 데이터 로드 & 클렌징
# ------------------------------------------------------------------
def load_and_clean(path):
    raw = pd.read_csv(path, encoding="utf-8-sig", dtype=str)
    section("1. 원본 데이터")
    print(f"행/열: {raw.shape}")
    print(raw.head())
    print("\n결측(빈 문자열 포함) 개수:")
    print(raw.replace("", pd.NA).isna().sum())

    df = raw.rename(columns={
        "날짜": "Date", "종가": "Close", "시가": "Open",
        "고가": "High", "저가": "Low", "거래량": "Volume", "변동 %": "ChangePct",
    })

    # 날짜: "2019- 11- 14" → 공백 제거 후 datetime
    df["Date"] = pd.to_datetime(df["Date"].str.replace(" ", ""), format="%Y-%m-%d", errors="coerce")

    # 가격: 천 단위 콤마 제거 후 float
    for col in ["Close", "Open", "High", "Low"]:
        df[col] = pd.to_numeric(df[col].str.replace(",", ""), errors="coerce")

    # 변동 %: "%" 제거 후 float
    df["ChangePct"] = pd.to_numeric(df["ChangePct"].str.replace("%", ""), errors="coerce")

    # 거래량: 전부 비어 있으면 컬럼 제거
    if df["Volume"].replace("", pd.NA).isna().all():
        df = df.drop(columns="Volume")
        print("\n※ 거래량 컬럼은 전부 비어 있어 제거했습니다.")

    before = len(df)
    df = (df.dropna(subset=["Date", "Close"])
            .drop_duplicates(subset="Date")
            .sort_values("Date")
            .set_index("Date"))

    # 논리 검증: 고가 >= max(시가, 종가), 저가 <= min(시가, 종가)
    bad = (df["High"] < df[["Open", "Close"]].max(axis=1)) | (df["Low"] > df[["Open", "Close"]].min(axis=1))
    print(f"제거된 행(결측/중복): {before - len(df)}")
    print(f"OHLC 논리 위반 행: {bad.sum()}")
    if bad.any():
        print(df[bad])
        # 보정: 고가/저가를 시가·종가를 포함하도록 맞춤
        df["High"] = df[["Open", "High", "Close"]].max(axis=1)
        df["Low"] = df[["Open", "Low", "Close"]].min(axis=1)
        print("→ 고가/저가를 시가·종가 범위에 맞게 보정했습니다.")

    section("2. 클렌징 결과")
    print(df.dtypes)
    print(f"\n기간: {df.index.min():%Y-%m-%d} ~ {df.index.max():%Y-%m-%d}, 거래일 {len(df):,}일")
    print(df.head())
    return df


# ------------------------------------------------------------------
# 2. 다각도 분석
# ------------------------------------------------------------------
def analyze(df):
    close = df["Close"]
    ret = close.pct_change() * 100   # 일간 수익률(%) — 원본 '변동 %'와 비교 검증용
    df["Return"] = ret

    section("3. 기술 통계")
    print(df[["Open", "High", "Low", "Close", "Return"]].describe())
    diff = (ret - df["ChangePct"]).abs().max()
    print(f"\n계산 수익률 vs 원본 '변동 %' 최대 차이: {diff:.3f}%p")

    section("4. 연도별 분석")
    yearly = pd.DataFrame({
        "시작": close.groupby(close.index.year).first(),
        "종료": close.groupby(close.index.year).last(),
        "최고": close.groupby(close.index.year).max(),
        "최저": close.groupby(close.index.year).min(),
        "변동성(%)": ret.groupby(ret.index.year).std() * (252 ** 0.5),
    })
    # 전년 말 종가 대비 수익률 (첫해는 연초 시가 대비)
    prev_end = yearly["종료"].shift(1).fillna(df["Open"].iloc[0])
    yearly["연수익률(%)"] = (yearly["종료"] / prev_end - 1) * 100
    print(yearly)
    print(f"\n최고의 해: {yearly['연수익률(%)'].idxmax()} ({yearly['연수익률(%)'].max():+.2f}%)")
    print(f"최악의 해: {yearly['연수익률(%)'].idxmin()} ({yearly['연수익률(%)'].min():+.2f}%)")

    section("5. 월별 계절성 (월 평균 수익률)")
    monthly_ret = close.resample("ME").last().pct_change() * 100
    season = monthly_ret.groupby(monthly_ret.index.month).agg(["mean", "median", lambda s: (s > 0).mean() * 100])
    season.columns = ["평균(%)", "중앙값(%)", "상승확률(%)"]
    season.index.name = "월"
    print(season)

    section("6. 요일별 평균 수익률")
    names = ["월", "화", "수", "목", "금"]
    dow = ret.groupby(ret.index.dayofweek).agg(["mean", "std", "count"])
    dow.index = [names[i] for i in dow.index]
    print(dow)

    section("7. 낙폭(Drawdown) 분석")
    peak = close.cummax()
    dd = (close / peak - 1) * 100
    df["Drawdown"] = dd
    trough = dd.idxmin()
    peak_date = close[:trough].idxmax()
    recover = close[trough:][close[trough:] >= close[peak_date]]
    print(f"최대 낙폭(MDD): {dd.min():.2f}%")
    print(f"  고점 {peak_date:%Y-%m-%d} ({close[peak_date]:,.2f}) → 저점 {trough:%Y-%m-%d} ({close[trough]:,.2f})")
    print(f"  회복일: {recover.index[0]:%Y-%m-%d}" if len(recover) else "  미회복")

    section("8. 극단적 일간 변동 Top 5")
    print("[상승]"); print(ret.nlargest(5).round(2).to_string())
    print("[하락]"); print(ret.nsmallest(5).round(2).to_string())

    section("9. 전체 기간 성과")
    years = (close.index[-1] - close.index[0]).days / 365.25
    cagr = ((close.iloc[-1] / close.iloc[0]) ** (1 / years) - 1) * 100
    vol = ret.std() * (252 ** 0.5)
    print(f"총 수익률: {(close.iloc[-1] / close.iloc[0] - 1) * 100:.2f}%")
    print(f"CAGR(연평균 성장률): {cagr:.2f}%")
    print(f"연환산 변동성: {vol:.2f}%")
    print(f"상승일 비율: {(ret > 0).mean() * 100:.1f}%")

    # 이동평균
    df["MA50"] = close.rolling(50).mean()
    df["MA200"] = close.rolling(200).mean()
    cross = (df["MA50"] > df["MA200"]).astype(int).diff()
    print(f"골든크로스 횟수: {(cross == 1).sum()}, 데드크로스 횟수: {(cross == -1).sum()}")
    return df, yearly, season


# ------------------------------------------------------------------
# 3. 시각화
# ------------------------------------------------------------------
def draw_close(fig, df, start="2000-01-01", end="2019-12-31", show_ma=False):
    """종가 라인그래프를 주어진 Figure에 그림 (기본: 2000년 1월 ~ 2019년 12월)"""
    period = df.loc[start:end]
    fig.clear()
    ax = fig.add_subplot(111)
    ax.plot(period.index, period["Close"], color="#1f77b4", linewidth=1.2, label="종가")
    if show_ma:
        ax.plot(period.index, period["MA50"], lw=1, color="#ff7f0e", label="50일 이동평균")
        ax.plot(period.index, period["MA200"], lw=1, color="#2ca02c", label="200일 이동평균")
    if len(period):
        ax.set_title(f"S&P 500 종가 추이 ({period.index.min():%Y.%m} ~ {period.index.max():%Y.%m})", fontsize=15)
    ax.set_xlabel("날짜")
    ax.set_ylabel("종가 (USD)")
    ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: f"{v:,.0f}"))
    ax.grid(alpha=0.3)
    ax.legend()
    fig.tight_layout()


def draw_dashboard(fig, df, yearly):
    fig.clear()
    axes = fig.subplots(2, 2)

    ax = axes[0, 0]
    ax.plot(df.index, df["Close"], lw=1, label="종가")
    ax.plot(df.index, df["MA50"], lw=1, label="50일 이동평균")
    ax.plot(df.index, df["MA200"], lw=1, label="200일 이동평균")
    ax.set_title("종가와 이동평균"); ax.legend(); ax.grid(alpha=0.3)

    ax = axes[0, 1]
    colors = ["#2ca02c" if v >= 0 else "#d62728" for v in yearly["연수익률(%)"]]
    ax.bar(yearly.index, yearly["연수익률(%)"], color=colors)
    ax.axhline(0, color="gray", lw=0.8)
    ax.set_xticks(yearly.index[::2])
    ax.set_title("연도별 수익률 (%)"); ax.grid(alpha=0.3, axis="y")

    ax = axes[1, 0]
    ax.fill_between(df.index, df["Drawdown"], 0, color="#d62728", alpha=0.4)
    ax.set_title("낙폭(Drawdown, %)"); ax.grid(alpha=0.3)

    ax = axes[1, 1]
    ax.hist(df["Return"].dropna(), bins=100, color="#1f77b4", alpha=0.8)
    ax.set_title("일간 수익률 분포 (%)"); ax.grid(alpha=0.3)

    fig.suptitle("S&P 500 다각도 분석", fontsize=16)
    fig.tight_layout()


def plot_close(df):
    fig = plt.figure(figsize=(14, 6))
    draw_close(fig, df)
    path = OUT_DIR / "sp500_close_2000_2019.png"
    fig.savefig(path, dpi=120)
    return path


def plot_dashboard(df, yearly):
    fig = plt.figure(figsize=(16, 10))
    draw_dashboard(fig, df, yearly)
    path = OUT_DIR / "sp500_dashboard.png"
    fig.savefig(path, dpi=110)
    return path


def main():
    csv_path = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_CSV
    OUT_DIR.mkdir(exist_ok=True)
    df = load_and_clean(csv_path)
    df, yearly, season = analyze(df)

    df.to_csv(OUT_DIR / "sp500_cleaned.csv", encoding="utf-8-sig")
    p1 = plot_close(df)
    p2 = plot_dashboard(df, yearly)
    section("저장 파일")
    print(OUT_DIR / "sp500_cleaned.csv"); print(p1); print(p2)
    plt.show()


if __name__ == "__main__":
    main()
