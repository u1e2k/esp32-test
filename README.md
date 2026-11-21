# ESP32 Test Project

このリポジトリは ESP32 開発・検証用プロジェクトです。

## 接続デバイス情報

| 項目 | 詳細 |
| :--- | :--- |
| **接続ポート** | `COM3` |
| **USB端子** | **USB Type-C** |
| **購入先** | [AliExpress 商品ページ (Item 1005005626482837)](https://ja.aliexpress.com/item/1005005626482837.html) (2023年11月購入) |
| **セット内容** | ESP32開発ボード本体 + **スクリューターミナル（ネジ留め端子台）拡張ボード** |
| **USB-シリアル変換チップ** | USB-SERIAL CH340 (`VID: 1A86`, `PID: 7523`) |
| **チップ種別 (Chip Type)** | ESP32-D0WD-V3 (revision v3.1) / Xtensa LX6 Dual Core |
| **ボード互換規格** | NodeMCU-32S Lua 30Pin (DOIT DevKit V1 互換) |
| **動作電圧 / 消費電流** | 2.3V 〜 3.6V (通常 3.3V, VIN/USB給電 5V) / 通常 約 80mA |
| **CPU / 周波数** | Dual Core + LP Core / 80MHz 〜 240MHz |
| **内蔵機能 (Features)** | Wi-Fi, Bluetooth (Classic / BLE) |
| **クリスタル周波数** | 40MHz |
| **フラッシュメモリ容量** | 4MB (Flash voltage: 3.3V) |

## ハードウェア・ピンレイアウト
- **フォームファクタ**: 30ピン（片側15ピン / NodeMCU-32S Lua 30Pin / DOIT DevKit V1 互換）
- **付属拡張ボード**: スクリューターミナル（ネジ留め端子台）拡張ベースボード
  - 各ピンがネジ留め端子台に引き出されており、マイナスドライバーでリード線やセンサーを直接頑丈に配線可能。ブレッドボード不要で接触不良を防げます。
- **基板上のボタン**:
  - **EN (RST)**: チップのハードウェアリセット（再起動）。
  - **BOOT (IO0)**: 起動モード切り替え ＆ ユーザー入力（`Pin(0, Pin.IN)` で通常のプッシュスイッチとしても利用可能）。
- 📌 **全ピンの役割・機能早見表**: [docs/pinout.md](docs/pinout.md)
- 📖 **内部構造・通信の仕組み解説**: [docs/how-it-works.md](docs/how-it-works.md)
- 💡 **工作・活用プロジェクトアイデア集**: [docs/ideas.md](docs/ideas.md)
- 🧪 **初回立ち上げ・IoTダッシュボード実験記録**: [docs/experiment_log_20261121.md](docs/experiment_log_20261121.md)
- 📄 **公式スペックシート (PDF)**: [docs/esp32_spec.pdf](docs/esp32_spec.pdf)

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

### Lチカ（MicroPythonスクリプト実行）
ESP32 内蔵LED (GPIO 2) を 0.5 秒間隔で 10 回点滅させます。
```powershell
uv run mpremote connect COM3 run blink.py
```

### BOOTボタンでLED制御
基板上の [BOOT] ボタンを押している間だけLEDを点灯させます。
```powershell
uv run mpremote connect COM3 run button_led.py
```

### 📱 IoT Webダッシュボード（Wi-Fiアクセスポイント ＆ リアルタイムモニター）
ESP32をWi-Fi親機（APモード）にし、ブラウザからLED操作や内蔵タッチセンサー・温度をリアルタイム確認できます。
```powershell
# 手動実行する場合
uv run mpremote connect COM3 run web_dashboard.py

# 本体に書き込んで常時稼働させる場合
uv run mpremote connect COM3 cp web_dashboard.py :main.py
```
- **接続先Wi-Fi (SSID)**: `ESP32-Dashboard`（パスワード不要）
- **ブラウザで開くURL**: `http://192.168.4.1`

### MicroPython インタラクティブ REPL 接続
```powershell
uv run --with mpremote mpremote connect COM3 repl
```
（終了時は `Ctrl + ]`）

### ボード起動時に自動常時実行させたい場合 (`main.py` として書き込み)
```powershell
uv run --with mpremote mpremote connect COM3 cp blink.py :main.py
```
