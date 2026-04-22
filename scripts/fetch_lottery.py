#!/usr/bin/env python3
"""
台灣統一發票中獎號碼爬蟲
從財政部賦稅署網站取得最新三期中獎號碼，更新 data/lottery.json
每逢雙數月25日開獎，本腳本每月1日執行確保資料最新
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
    print("Installing dependencies...")
    os.system("pip install requests beautifulsoup4 -q")
    import requests
    from bs4 import BeautifulSoup

TW_TZ = timezone(timedelta(hours=8))
DATA_FILE = Path(__file__).parent.parent / "data" / "lottery.json"

# 財政部賦稅署公告列表
DOT_GOV_URL = "https://www.dot.gov.tw/singlehtml/ch26"
INVOS_URL = "https://invos.com.tw/invoice-list"

def roc_year(western_year: int) -> int:
    return western_year - 1911

def parse_invos():
    """從 invos.com.tw 取得最近三期號碼"""
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
    }
    try:
        resp = requests.get(INVOS_URL, headers=headers, timeout=15)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        text = soup.get_text()
        
        periods = []
        # 搜尋年份期別
        pattern = re.compile(r'(\d{3})年\s*(\d{1,2}[-–]\d{1,2})月')
        num_8 = re.compile(r'\b\d{8}\b')
        num_3 = re.compile(r'\b\d{3}\b')
        
        # 簡單解析：回傳 text 讓人工確認
        print("=== invos.com.tw text snippet ===")
        print(text[:3000])
        return []
    except Exception as e:
        print(f"Error fetching invos: {e}")
        return []

def parse_dot_gov():
    """從財政部賦稅署取得最新一期號碼"""
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
    }
    try:
        resp = requests.get(DOT_GOV_URL, headers=headers, timeout=15)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        text = soup.get_text(separator="\n")
        
        print("=== dot.gov.tw text snippet ===")
        # 找最新公告
        for link in soup.find_all("a"):
            href = link.get("href", "")
            title = link.get_text(strip=True)
            if "中獎" in title and "統一發票" in title:
                print(f"  {title}: {href}")
        return []
    except Exception as e:
        print(f"Error fetching dot.gov: {e}")
        return []

def fetch_period(roc_year_month: str) -> dict | None:
    """
    使用財政部電子發票 API 取得特定期別號碼
    roc_year_month: 民國年月，如 "11501" 表示115年1月(即1-2月期)
    
    注意：官方 API 需要 appID，這裡嘗試無驗證版本
    """
    url = "https://invoice.etax.nat.gov.tw/index.html"
    # 實際上財政部有公開的發票號碼頁面
    try:
        resp = requests.get(url, timeout=15)
        print(f"invoice.etax status: {resp.status_code}")
    except Exception as e:
        print(f"Error: {e}")
    return None

def get_latest_from_etax():
    """從財政部電子發票整合服務平台取得最新號碼"""
    # 此 API 端點為公開資訊，無需 appID
    # 使用 etax.nat.gov.tw 公開頁面
    urls_to_try = [
        "https://invoice.etax.nat.gov.tw/index.html",
        "https://www.etax.nat.gov.tw/etwmain/front/ETW118W/VIEW/",
    ]
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    for url in urls_to_try:
        try:
            resp = requests.get(url, headers=headers, timeout=15)
            print(f"Status {url}: {resp.status_code}")
            if resp.status_code == 200:
                soup = BeautifulSoup(resp.text, "html.parser")
                text = soup.get_text(separator="\n")
                # 找8碼號碼
                numbers = re.findall(r'\b\d{8}\b', text)
                print(f"Found 8-digit numbers: {numbers[:20]}")
                print("Text snippet:", text[:2000])
        except Exception as e:
            print(f"Error {url}: {e}")

def build_periods_from_known_data():
    """
    使用已知的最近三期資料建立 JSON
    資料來源：invos.com.tw 及財政部公告
    增開六獎號碼來自頭獎末3碼
    """
    now = datetime.now(TW_TZ)
    
    periods = [
        {
            "period": "115年1-2月",
            "year_month": "11501",
            "announce_date": "2026-03-25",
            "claim_start": "2026-04-06",
            "claim_end": "2026-07-06",
            "prizes": {
                "super": {"name": "特別獎", "amount": 10000000, "numbers": ["87510041"]},
                "special": {"name": "特獎", "amount": 2000000, "numbers": ["32220522"]},
                "first": {"name": "頭獎", "amount": 200000, "numbers": ["26649927", "59565539", "11460822"]},
                "sixth_extra": {"name": "增開六獎", "amount": 200, "numbers": ["927", "539", "822"]}
            }
        },
        {
            "period": "114年11-12月",
            "year_month": "11411",
            "announce_date": "2026-01-25",
            "claim_start": "2026-02-06",
            "claim_end": "2026-05-06",
            "prizes": {
                "super": {"name": "特別獎", "amount": 10000000, "numbers": ["97023797"]},
                "special": {"name": "特獎", "amount": 2000000, "numbers": ["00507588"]},
                "first": {"name": "頭獎", "amount": 200000, "numbers": ["92377231", "05232592", "78125249"]},
                "sixth_extra": {"name": "增開六獎", "amount": 200, "numbers": ["231", "592", "249"]}
            }
        },
        {
            "period": "114年9-10月",
            "year_month": "11409",
            "announce_date": "2025-11-25",
            "claim_start": "2025-12-06",
            "claim_end": "2026-03-06",
            "prizes": {
                "super": {"name": "特別獎", "amount": 10000000, "numbers": ["28630525"]},
                "special": {"name": "特獎", "amount": 2000000, "numbers": ["90028580"]},
                "first": {"name": "頭獎", "amount": 200000, "numbers": ["41016094", "98081574", "07309261"]},
                "sixth_extra": {"name": "增開六獎", "amount": 200, "numbers": ["094", "574", "261"]}
            }
        }
    ]
    
    data = {
        "updated_at": now.isoformat(),
        "periods": periods
    }
    
    DATA_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"✅ 已更新 {DATA_FILE}，共 {len(periods)} 期資料")
    return data

def scrape_latest():
    """
    主函數：嘗試從網路取得最新資料，失敗則保留現有 JSON
    實際上採用爬取 invos.com.tw 的方式取得最新期別
    """
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
    }
    
    print("📡 正在從 invos.com.tw 取得最新中獎號碼...")
    
    try:
        resp = requests.get(INVOS_URL, headers=headers, timeout=20)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        text = soup.get_text(separator="\n")
        
        # 讀取現有資料作為備份
        existing = json.loads(DATA_FILE.read_text(encoding="utf-8")) if DATA_FILE.exists() else {"periods": []}
        
        # 解析期別與號碼
        # 格式: "114年 統一發票 11 12 月" or "115年1-2月"
        period_pattern = re.compile(r'(\d{3})年\s*(\d{1,2})[-–\s]+(\d{1,2})\s*月')
        number_8_pattern = re.compile(r'\b(\d{8})\b')
        number_3_pattern = re.compile(r'\b(\d{3})\b')
        
        lines = [l.strip() for l in text.split("\n") if l.strip()]
        
        periods_found = []
        i = 0
        while i < len(lines) and len(periods_found) < 3:
            line = lines[i]
            m = period_pattern.search(line)
            if m:
                roc_y, m_start, m_end = m.group(1), m.group(2), m.group(3)
                period_label = f"{roc_y}年{m_start}-{m_end}月"
                year_month = f"{roc_y}{int(m_start):02d}"
                
                # 往後找號碼
                super_no = special_no = None
                first_nos = []
                j = i + 1
                while j < min(i + 30, len(lines)):
                    nums_8 = number_8_pattern.findall(lines[j])
                    if nums_8:
                        if "特別獎" in lines[j] or (super_no is None and not special_no and not first_nos):
                            super_no = nums_8[0]
                        elif "特獎" in lines[j] or (super_no and not special_no):
                            special_no = nums_8[0]
                        elif "頭獎" in lines[j] or special_no:
                            first_nos.extend(nums_8)
                    j += 1
                
                if super_no and special_no and first_nos:
                    # 增開六獎 = 頭獎末3碼
                    sixth_extra = list({n[-3:] for n in first_nos})
                    periods_found.append({
                        "period": period_label,
                        "year_month": year_month,
                        "prizes": {
                            "super": {"name": "特別獎", "amount": 10000000, "numbers": [super_no]},
                            "special": {"name": "特獎", "amount": 2000000, "numbers": [special_no]},
                            "first": {"name": "頭獎", "amount": 200000, "numbers": first_nos[:3]},
                            "sixth_extra": {"name": "增開六獎", "amount": 200, "numbers": sixth_extra}
                        }
                    })
            i += 1
        
        if len(periods_found) >= 2:
            # 計算領獎日期
            for p in periods_found:
                # 估算開獎日與領獎期
                ym = p["year_month"]
                roc_y = int(ym[:3])
                month = int(ym[3:])
                announce_western = 1911 + roc_y
                p["announce_date"] = f"{announce_western}-{month+1:02d}-25"
                p["claim_start"] = f"{announce_western}-{month+2:02d}-06" if month < 11 else f"{announce_western+1}-01-06"
                p["claim_end"] = f"{announce_western}-{month+5:02d}-06" if month < 9 else f"{announce_western+1}-{month-6:02d}-06"
            
            now = datetime.now(TW_TZ)
            data = {"updated_at": now.isoformat(), "periods": periods_found[:3]}
            DATA_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
            print(f"✅ 成功更新 {len(periods_found)} 期資料")
        else:
            print(f"⚠️  只找到 {len(periods_found)} 期，保留現有資料")
            
    except Exception as e:
        print(f"❌ 爬取失敗: {e}，保留現有資料")

if __name__ == "__main__":
    if "--build" in sys.argv:
        build_periods_from_known_data()
    else:
        scrape_latest()
