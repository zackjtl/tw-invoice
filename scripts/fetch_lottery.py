#!/usr/bin/env python3
"""
台灣統一發票中獎號碼爬蟲
資料來源：財政部稅務入口網 https://www.etax.nat.gov.tw/etwmain/etw183w
開獎規則：每雙數月 25 日開獎（1-2月、3-4月…11-12月）
本腳本由 GitHub Actions 每雙數月 26 日 01:00（台灣時間）自動執行
"""

import json
import re
import sys
import os
from datetime import datetime, timezone, timedelta
from pathlib import Path

try:
    import requests
    from bs4 import BeautifulSoup
except ImportError:
    os.system("pip install requests beautifulsoup4 -q")
    import requests
    from bs4 import BeautifulSoup

TW_TZ = timezone(timedelta(hours=8))
DATA_FILE = Path(__file__).parent.parent / "data" / "lottery.json"

# 財政部稅務入口網各期網址格式：ETW183W2_{yyyMM}
# 例如 115年1-2月 → ETW183W2_11501
ETAX_LIST_URL = "https://www.etax.nat.gov.tw/etwmain/etw183w"
ETAX_PERIOD_URL = "https://www.etax.nat.gov.tw/etwmain/ETW183W2_{year_month}/"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
}


def roc_to_western(roc_year: int) -> int:
    return roc_year + 1911


def current_latest_period() -> tuple[int, int]:
    """
    根據當前台灣時間，計算「最新已開獎」的期別。
    開獎時間表：
      1-2月 → 開獎日 2月25日（民國年同西元年）
      3-4月 → 4月25日
      5-6月 → 6月25日
      7-8月 → 8月25日
      9-10月→ 10月25日
      11-12月→ 12月25日

    回傳 (roc_year, start_month) 例如 (115, 1) 代表 115年1-2月
    """
    now = datetime.now(TW_TZ)
    western_year = now.year
    month = now.month
    day = now.day

    roc_year = western_year - 1911

    # 找到最近一個已過的開獎月份（偶數月25日）
    # 開獎月份：2, 4, 6, 8, 10, 12
    announce_months = [2, 4, 6, 8, 10, 12]

    latest_start_month = None
    latest_roc = roc_year

    for am in reversed(announce_months):
        # 開獎日為 am 月 25 日
        if month > am or (month == am and day >= 25):
            # 已過此開獎日
            latest_start_month = am - 1  # 期別開始月（奇數月）
            latest_roc = roc_year
            break
        if month < am:
            continue

    if latest_start_month is None:
        # 今年還未到2月25日，最新期是上一年的11-12月
        latest_start_month = 11
        latest_roc = roc_year - 1

    return latest_roc, latest_start_month


def period_label(roc_year: int, start_month: int) -> str:
    end_month = start_month + 1
    return f"{roc_year}年{start_month}-{end_month}月"


def year_month_code(roc_year: int, start_month: int) -> str:
    """例如 (115, 1) → '11501'"""
    return f"{roc_year}{start_month:02d}"


def announce_date(roc_year: int, start_month: int) -> str:
    """開獎日 = 結束月 25 日"""
    western = roc_to_western(roc_year)
    end_month = start_month + 1
    return f"{western}-{end_month:02d}-25"


def claim_dates(roc_year: int, start_month: int) -> tuple[str, str]:
    """
    領獎期間：開獎後第 12 天（約 3月6日）起，領3個月（至 7月5日）
    簡化計算：claim_start = 開獎月+1 的 06 日，claim_end = 開獎月+4 的 05 日
    """
    western = roc_to_western(roc_year)
    end_month = start_month + 1  # 開獎月
    claim_start_m = end_month + 1
    claim_end_m = end_month + 4

    # 跨年處理
    start_year = western
    end_year = western
    if claim_start_m > 12:
        claim_start_m -= 12
        start_year += 1
    if claim_end_m > 12:
        claim_end_m -= 12
        end_year += 1

    return (
        f"{start_year}-{claim_start_m:02d}-06",
        f"{end_year}-{claim_end_m:02d}-05",
    )


def fetch_period_data(roc_year: int, start_month: int) -> dict | None:
    """
    從財政部稅務入口網抓取特定期別的中獎號碼
    URL 格式：https://www.etax.nat.gov.tw/etwmain/ETW183W2_{yyyMM}/
    """
    ym = year_month_code(roc_year, start_month)
    url = ETAX_PERIOD_URL.format(year_month=ym)
    source_url = url

    try:
        resp = requests.get(url, headers=HEADERS, timeout=20)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        text = soup.get_text(separator="\n")

        # 找 8 碼號碼
        nums_8 = re.findall(r'\b(\d{8})\b', text)
        # 找 3 碼增開六獎（通常在「增開六獎」附近）
        nums_3 = []

        # 嘗試用結構化方式解析表格
        super_no = None
        special_no = None
        first_nos = []
        extra_nos = []

        lines = [l.strip() for l in text.split('\n') if l.strip()]
        for i, line in enumerate(lines):
            context = ' '.join(lines[max(0, i-2):i+3])
            found_8 = re.findall(r'\b(\d{8})\b', context)
            found_3 = re.findall(r'\b(\d{3})\b', line)

            if '特別獎' in line and found_8:
                super_no = found_8[0]
            elif '特獎' in line and not '特別' in line and found_8:
                if not special_no:
                    special_no = found_8[0]
            elif '頭獎' in line and found_8:
                first_nos.extend(found_8)
            elif '增開' in line:
                # 增開六獎是3碼
                e3 = re.findall(r'\b(\d{3})\b', ' '.join(lines[i:i+5]))
                if e3:
                    extra_nos = e3[:6]

        # fallback：從所有 8 碼號碼依序判斷
        if not super_no and len(nums_8) >= 1:
            super_no = nums_8[0]
        if not special_no and len(nums_8) >= 2:
            special_no = nums_8[1]
        if not first_nos and len(nums_8) >= 3:
            first_nos = nums_8[2:5]

        if not super_no or not special_no or not first_nos:
            print(f"⚠️  {ym} 解析不完整：super={super_no}, special={special_no}, first={first_nos}")
            return None

        # 若無增開六獎資料，預設為空
        if not extra_nos:
            extra_nos = []

        claim_start, claim_end = claim_dates(roc_year, start_month)

        return {
            "period": period_label(roc_year, start_month),
            "year_month": ym,
            "announce_date": announce_date(roc_year, start_month),
            "claim_start": claim_start,
            "claim_end": claim_end,
            "source_url": source_url,
            "source_label": "財政部稅務入口網",
            "prizes": {
                "super":       {"name": "特別獎", "amount": 10000000, "numbers": [super_no]},
                "special":     {"name": "特獎",   "amount": 2000000,  "numbers": [special_no]},
                "first":       {"name": "頭獎",   "amount": 200000,   "numbers": list(dict.fromkeys(first_nos))[:3]},
                "sixth_extra": {"name": "增開六獎","amount": 200,      "numbers": extra_nos},
            }
        }

    except Exception as e:
        print(f"❌ 抓取 {ym} 失敗：{e}")
        return None


def prev_period(roc_year: int, start_month: int) -> tuple[int, int]:
    """計算上一期"""
    if start_month == 1:
        return roc_year - 1, 11
    return roc_year, start_month - 2


def scrape_latest():
    """抓取最近三期資料並更新 lottery.json"""
    now = datetime.now(TW_TZ)

    # 計算最近三期
    latest_roc, latest_sm = current_latest_period()
    p2_roc, p2_sm = prev_period(latest_roc, latest_sm)
    p3_roc, p3_sm = prev_period(p2_roc, p2_sm)

    target_periods = [
        (latest_roc, latest_sm),
        (p2_roc, p2_sm),
        (p3_roc, p3_sm),
    ]

    print(f"📅 當前台灣時間：{now.strftime('%Y-%m-%d %H:%M')} (UTC+8)")
    print(f"📋 計算最新三期：{[period_label(r, m) for r, m in target_periods]}")

    # 讀取現有資料作為備份
    existing = {}
    if DATA_FILE.exists():
        try:
            old = json.loads(DATA_FILE.read_text(encoding="utf-8"))
            for p in old.get("periods", []):
                existing[p["year_month"]] = p
        except Exception:
            pass

    periods = []
    for roc_y, sm in target_periods:
        ym = year_month_code(roc_y, sm)
        print(f"\n🔍 抓取 {period_label(roc_y, sm)}（{ym}）...")

        data = fetch_period_data(roc_y, sm)
        if data:
            print(f"  ✅ 特別獎：{data['prizes']['super']['numbers'][0]}")
            print(f"  ✅ 特獎：{data['prizes']['special']['numbers'][0]}")
            print(f"  ✅ 頭獎：{data['prizes']['first']['numbers']}")
            periods.append(data)
        elif ym in existing:
            print(f"  ⚠️  抓取失敗，使用快取資料")
            periods.append(existing[ym])
        else:
            print(f"  ❌ 無法取得資料，跳過")

    if not periods:
        print("❌ 完全無法取得資料，保留原有 JSON")
        return

    output = {
        "updated_at": now.isoformat(),
        "periods": periods
    }

    DATA_FILE.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n✅ 已更新 {DATA_FILE}，共 {len(periods)} 期")


if __name__ == "__main__":
    scrape_latest()
