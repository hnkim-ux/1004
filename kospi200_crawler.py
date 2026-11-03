"""
코스피200 지수와 구성종목 시세를 수집해 콘솔에 출력하고 CSV로 저장하는 스크립트 (requests)

stock.naver.com/market/stock/kr 페이지는 Next.js로 만든 클라이언트 렌더링 페이지라
HTML에는 시세가 들어 있지 않고, 브라우저가 아래 JSON API를 호출해 화면을 그린다.
그래서 HTML을 BeautifulSoup으로 파싱하는 대신 같은 JSON API를 직접 호출한다.
(예전 finance.naver.com/sise/entryJongmok.naver 페이지는 "더 이상 제공되지 않습니다"로 바뀜)

    - 지수:     polling.finance.naver.com/api/realtime/domestic/index/KPI200
                (stock.naver.com 국내증시 페이지가 실제로 호출하는 API)
    - 구성종목: m.stock.naver.com/api/index/KPI200/enrollStocks?page=N&pageSize=50
                (네이버 증권 모바일의 코스피200 구성종목 API, pageSize 최대 60)
                빈 페이지(또는 50개 미만 페이지)가 나올 때까지 자동으로 다음 페이지를 요청한다.

코스피200은 보통 200종목이지만, 구성종목이 인적분할하면 분할 신설법인이
다음 정기변경 전까지 특례편입되어 일시적으로 200개를 넘을 수 있다.
그래서 개수를 200으로 자르지 않고, 지수 API의 상승/보합/하락 종목 수 합계와 대조해 검증한다.

사용법:
    pip install requests
    python kospi200_crawler.py                # 현재 폴더에 CSV 2개 저장
    python kospi200_crawler.py -o 결과폴더    # 저장 위치 지정
"""

import argparse
import csv
import os
import sys
import time
import unicodedata
from datetime import datetime

import requests

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36"
    ),
    "Referer": "https://stock.naver.com/market/stock/kr",
    "Accept": "application/json, text/plain, */*",
}

INDEX_URL = "https://polling.finance.naver.com/api/realtime/domestic/index/KPI200"
STOCKS_URL = "https://m.stock.naver.com/api/index/KPI200/enrollStocks"
INTEGRATION_URL = "https://m.stock.naver.com/api/index/KPI200/integration"
PAGE_SIZE = 50          # API가 허용하는 최대값은 60
MAX_PAGES = 20          # 응답이 비정상일 때 무한 반복을 막는 상한
REQUEST_DELAY = 0.5     # 요청 사이 지연(초)

INDEX_FIELDS = [
    "기준시각", "지수명", "현재값", "전일대비", "등락률(%)", "등락",
    "시가", "고가", "저가", "거래량", "거래대금", "장상태",
]
STOCK_FIELDS = [
    "순위", "종목코드", "종목명", "현재가", "전일비", "등락률(%)", "등락",
    "거래량", "거래대금(백만)", "시가총액(억)", "기준시각",
]


def fetch_json(session, url, params=None):
    resp = session.get(url, params=params, timeout=10)
    resp.raise_for_status()
    return resp.json()


def format_time(iso_text):
    """'2026-11-03T14:11:36+09:00' -> '2026-11-03 14:11:36'"""
    if not iso_text:
        return ""
    try:
        return datetime.fromisoformat(iso_text).strftime("%Y-%m-%d %H:%M:%S")
    except ValueError:
        return iso_text


def fetch_index(session):
    """코스피200 지수 현재 시세를 dict로 반환"""
    data = fetch_json(session, INDEX_URL)
    item = data["datas"][0]
    return {
        "기준시각": format_time(item.get("localTradedAt")),
        "지수명": item.get("stockName", ""),
        "현재값": item.get("closePrice", ""),
        "전일대비": item.get("compareToPreviousClosePrice", ""),
        "등락률(%)": item.get("fluctuationsRatio", ""),
        "등락": item.get("compareToPreviousPrice", {}).get("text", ""),
        "시가": item.get("openPrice", ""),
        "고가": item.get("highPrice", ""),
        "저가": item.get("lowPrice", ""),
        "거래량": item.get("accumulatedTradingVolume", ""),
        "거래대금": item.get("accumulatedTradingValue", ""),
        "장상태": item.get("marketStatus", ""),
    }


def fetch_constituents(session):
    """코스피200 구성종목 전체를 시가총액 순 list[dict]로 반환"""
    rows = []
    seen = set()
    for page in range(1, MAX_PAGES + 1):
        items = fetch_json(session, STOCKS_URL, {"page": page, "pageSize": PAGE_SIZE})
        if not items:
            break
        for item in items:
            code = item.get("itemCode", "")
            if code in seen:
                continue
            seen.add(code)
            rows.append({
                "순위": len(rows) + 1,
                "종목코드": code,
                "종목명": item.get("stockName", ""),
                "현재가": item.get("closePrice", ""),
                "전일비": item.get("compareToPreviousClosePrice", ""),
                "등락률(%)": item.get("fluctuationsRatio", ""),
                "등락": item.get("compareToPreviousPrice", {}).get("text", ""),
                "거래량": item.get("accumulatedTradingVolume", ""),
                "거래대금(백만)": item.get("accumulatedTradingValue", ""),
                "시가총액(억)": item.get("marketValue", ""),
                "기준시각": format_time(item.get("localTradedAt")),
            })
        print(f"  - {page}페이지: {len(items)}개 (누적 {len(rows)}개)")
        if len(items) < PAGE_SIZE:
            break
        time.sleep(REQUEST_DELAY)
    return rows


def fetch_expected_count(session):
    """지수 상세의 상한/상승/보합/하한/하락 종목 수 합계 = 현재 지수 구성종목 수 (실패 시 None)"""
    try:
        info = fetch_json(session, INTEGRATION_URL).get("upDownStockInfo", {})
        keys = ("upperCount", "riseCount", "steadyCount", "lowerCount", "fallCount")
        return sum(int(str(info[k]).replace(",", "")) for k in keys)
    except (requests.RequestException, KeyError, ValueError):
        return None


def save_csv(path, fields, rows):
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def pad(text, width, right=False):
    """한글(전각 문자)을 2칸으로 계산해 정렬 (기본 왼쪽, right=True면 오른쪽)"""
    text = str(text)
    display = sum(2 if unicodedata.east_asian_width(c) in "WF" else 1 for c in text)
    space = " " * max(0, width - display)
    return space + text if right else text + space


def print_index(index):
    print("\n[코스피200 지수]")
    print(f"  {index['지수명']}  {index['현재값']}  "
          f"{index['전일대비']} ({index['등락률(%)']}%)  {index['등락']}")
    print(f"  시가 {index['시가']} / 고가 {index['고가']} / 저가 {index['저가']}")
    print(f"  거래량 {index['거래량']} / 거래대금 {index['거래대금']}")
    print(f"  기준시각 {index['기준시각']} ({index['장상태']})")


def print_constituents(rows, limit=20):
    print(f"\n[코스피200 구성종목] 총 {len(rows)}개 (시가총액 상위 {min(limit, len(rows))}개 표시)")
    print(f"{pad('순위', 4)} {pad('코드', 7)} {pad('종목명', 18)} {pad('현재가', 10, True)} {pad('전일비', 9, True)} "
          f"{pad('등락률', 7, True)} {pad('거래량', 12, True)} {pad('시총(억)', 11, True)}")
    for r in rows[:limit]:
        print(f"{r['순위']:>4} {r['종목코드']:<7} {pad(r['종목명'], 18)} {r['현재가']:>10} "
              f"{r['전일비']:>9} {r['등락률(%)']:>6}% {r['거래량']:>12} {r['시가총액(억)']:>11}")


def main():
    parser = argparse.ArgumentParser(description="코스피200 지수/구성종목 크롤러")
    parser.add_argument("-o", "--outdir", default=".", help="CSV 저장 폴더 (기본: 현재 폴더)")
    parser.add_argument("-n", "--show", type=int, default=20, help="콘솔에 표시할 종목 수")
    args = parser.parse_args()

    os.makedirs(args.outdir, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M")

    with requests.Session() as session:
        session.headers.update(HEADERS)

        print("코스피200 지수 수집 중...")
        index = fetch_index(session)
        time.sleep(REQUEST_DELAY)

        print("코스피200 구성종목 수집 중...")
        stocks = fetch_constituents(session)
        time.sleep(REQUEST_DELAY)
        expected = fetch_expected_count(session)

    if expected is None:
        print(f"  구성종목 {len(stocks)}개 수집 (지수 종목 수 확인 실패)")
    elif expected == len(stocks):
        print(f"  구성종목 {len(stocks)}개 수집 - 지수 구성종목 수({expected}개)와 일치")
    else:
        print(f"  [경고] 수집 {len(stocks)}개 / 지수 구성종목 {expected}개 - 개수가 다릅니다")

    print_index(index)
    print_constituents(stocks, args.show)

    index_path = os.path.join(args.outdir, f"kospi200_index_{stamp}.csv")
    stocks_path = os.path.join(args.outdir, f"kospi200_stocks_{stamp}.csv")
    save_csv(index_path, INDEX_FIELDS, [index])
    save_csv(stocks_path, STOCK_FIELDS, stocks)
    print(f"\n저장 완료:\n  {os.path.abspath(index_path)}\n  {os.path.abspath(stocks_path)}")


if __name__ == "__main__":
    # PyInstaller exe를 더블클릭해 실행하면 끝나자마자 콘솔 창이 닫히므로,
    # exe일 때만 오류를 보여주고 엔터를 누를 때까지 기다린다.
    if getattr(sys, "frozen", False):
        try:
            main()
        except Exception as e:
            print(f"\n[오류] {e}")
        input("\n엔터를 누르면 종료합니다...")
    else:
        main()
