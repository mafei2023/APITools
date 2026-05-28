# API Key Manager

[简体中文](README.md) | [English](README.en.md) | [繁体中文](README.zh-TW.md) | [日本語](README.ja.md)

一個本地執行的 API 金鑰管理工具，協助開發者快速批次匯入、分組、測試和清理 API 金鑰。

## 功能特色

- **批次匯入** — 支援貼上多個金鑰，自動去重，支援 Base64 編碼金鑰自動解碼
- **分組管理** — 按服務商或用途對金鑰進行分組，支援自訂分組匯總
- **一鍵測試** — 多執行緒並行測試金鑰可用性，顯示延遲和錯誤資訊
- **統計概覽** — 可用/失效/總數一目了然
- **清理失效金鑰** — 快速剔除測試失敗的金鑰
- **淺色/深色佈景主題** — 自動跟隨系統偏好切換

## 技術堆疊

| 層 | 技術 |
|---|---|
| 後端 | Python / Flask |
| 前端 | 單檔 HTML（原生 JS，無框架） |
| 資料庫 | SQLite |
| API 協定 | OpenAI 相容介面 |

## 快速開始

### 環境需求

- Python 3.9+

### 安裝與執行

```bash
# 安裝相依套件
pip install -r requirements.txt

# 啟動服務
python app.py
```

服務啟動後訪問 http://localhost:5000

Windows 使用者也可以直接雙擊 `start.bat` 啟動。

## 專案結構

```
APITools/
├── app.py              # Flask 後端 + API 路由
├── index.html          # 前端單頁應用
├── data.db             # SQLite 資料庫（執行時自動建立）
├── requirements.txt    # Python 相依套件
├── start.bat           # Windows 一鍵啟動腳本
├── PRODUCT.md          # 產品定義
└── DESIGN.md           # 設計規範
```

## 使用流程

1. **建立分組** — 按 API 服務商（如 OpenAI、Claude）建立分組，設定介面協定和模型
2. **新增金鑰** — 批次貼上金鑰到對應分組，新增時自動測試可用性
3. **檢視狀態** — 在統計頁檢視全域狀態，或在分組內檢視每個金鑰的詳細資訊
4. **清理金鑰** — 一鍵移除失效金鑰，保持金鑰庫乾淨

## 友情連結

- [LINUX DO](https://linux.do) — 一個關於 Linux 和開源的技術社群

## 授權條款

MIT
