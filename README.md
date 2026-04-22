# 台灣統一發票中獎號碼查詢

靜態網站，顯示最近三期統一發票中獎號碼，並提供快速對獎功能。

## 功能

- 📋 顯示最近三期（半年）中獎號碼
- 🔍 快速輸入發票末8碼自動對獎
- 🌙 支援深色／亮色模式
- 📱 響應式設計，手機友善

## 資料更新機制

`data/lottery.json` 由 GitHub Actions 自動維護：

- **排程觸發**：每雙數月26日 01:00（台灣時間）自動執行，確保25日開獎後更新
- **手動觸發**：可在 Actions 頁面手動執行 `workflow_dispatch`
- 爬蟲腳本位於 `scripts/fetch_lottery.py`

## 本機執行爬蟲

```bash
pip install requests beautifulsoup4
python scripts/fetch_lottery.py
```

## 部署方式

本專案為純靜態網站，可部署至：

- **GitHub Pages**：啟用後自動部署 `main` 分支
- **Vercel / Netlify**：連結此 Repo 即可，靜態輸出目錄為根目錄
- **任何靜態主機**

## 資料格式

`data/lottery.json` 格式說明：

```json
{
  "updated_at": "ISO 8601 時間",
  "periods": [
    {
      "period": "115年1-2月",
      "year_month": "11501",
      "announce_date": "2026-03-25",
      "claim_start": "2026-04-06",
      "claim_end": "2026-07-06",
      "prizes": {
        "super":       { "name": "特別獎", "amount": 10000000, "numbers": ["XXXXXXXX"] },
        "special":     { "name": "特獎",   "amount": 2000000,  "numbers": ["XXXXXXXX"] },
        "first":       { "name": "頭獎",   "amount": 200000,   "numbers": ["XXXXXXXX", ...] },
        "sixth_extra": { "name": "增開六獎","amount": 200,      "numbers": ["XXX", ...] }
      }
    }
  ]
}
```

## 資料來源

- [財政部賦稅署公告](https://www.dot.gov.tw/singlehtml/ch26)
- [財政部稅務入口網](https://www.etax.nat.gov.tw)
- [電子發票整合服務平台](https://www.einvoice.nat.gov.tw)
