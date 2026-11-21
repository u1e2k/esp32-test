# ESP32 Test Project

このリポジトリは ESP32 開発・検証用プロジェクトです。

## 接続デバイス情報

| 項目 | 詳細 |
| :--- | :--- |
| **接続ポート** | `COM3` |
| **USB-シリアル変換チップ** | USB-SERIAL CH340 (`VID: 1A86`, `PID: 7523`) |
| **チップ種別 (Chip Type)** | ESP32-D0WD-V3 (revision v3.1) |
| **CPU / 周波数** | Dual Core + LP Core / 最大 240MHz |
| **内蔵機能 (Features)** | Wi-Fi, Bluetooth (Classic / BLE) |
| **クリスタル周波数** | 40MHz |
| **フラッシュメモリ容量** | 4MB (Flash voltage: 3.3V) |

---

## 便利なコマンドメモ

Python環境およびパッケージ管理には `uv` を使用します。

### チップ情報・接続確認
```powershell
uv run --with esptool esptool --port COM3 chip-id
```

### フラッシュ情報確認
```powershell
uv run --with esptool esptool --port COM3 flash-id
```

### シリアルモニタ接続
```powershell
uv run --with pyserial python -m serial.tools.miniterm COM3 115200
```
