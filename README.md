# ESP32 Test Project

手持ちの **ESP32** および **ESP32-C3** 開発ボードの MicroPython 開発・検証用リポジトリです。  
Python 環境・パッケージ管理には `uv`（`esptool` / `mpremote`）を使用しています。

---

## 📦 手持ちボード一覧・比較

| 項目 | ボード ①：ESP32 (無印) | ボード ②：ESP32-C3（New） |
| :--- | :--- | :--- |
| **接続ポート (目安)** | `COM3` | `COM6` |
| **USB-シリアル変換** | CH340 (`VID: 1A86`, `PID: 7523`) | **内蔵 USB-Serial/JTAG** (`VID: 303A`, `PID: 1001`) |
| **USB端子** | USB Type-C | USB Type-C |
| **チップ** | ESP32-D0WD-V3 (rev v3.1) | **ESP32-C3 (QFN32)** (rev v0.4) |
| **CPU / 周波数** | Xtensa LX6 Dual Core / 〜240MHz | **RISC-V Single Core** / 〜160MHz |
| **ワイヤレス機能** | Wi-Fi, Bluetooth (Classic / BLE) | Wi-Fi, **Bluetooth 5 (LE)** ※Classic非対応 |
| **フラッシュ / 水晶** | 4MB / 40MHz | 4MB (XMC) / 40MHz |
| **MACアドレス** | - | `9c:cc:01:ab:99:ec` |
| **フォームファクタ** | NodeMCU-32S 30Pin (DOIT DevKit V1 互換)<br>+ スクリューターミナル拡張ボード | ESP32-C3 0.42インチ OLED 搭載ボード<br>(72×40 SSD1306 / SDA=`GPIO 5`, SCL=`GPIO 6`, `0x3C`) |
| **MicroPython ファーム** | [firmware.bin](firmware.bin) | [ESP32_GENERIC_C3-20260824-v1.29.0.bin](ESP32_GENERIC_C3-20260824-v1.29.0.bin) |
| **購入先 (AliExpress)** | [Item 1005005626482837](https://ja.aliexpress.com/item/1005005626482837.html) (2023/11) | [Item 1005009157602185](https://ja.aliexpress.com/item/1005009157602185.html) (2026/11) |

> **💡 接続ポートの確認方法 (Windows PowerShell)**
> ```powershell
> Get-PnpDevice -Class Ports -Status OK | Select-Object FriendlyName, InstanceId
> ```
> ※ `uv` コマンドにパスが通っていない環境では、`uv run ...` の代わりに `.\.venv\Scripts\esptool.exe` や `.\.venv\Scripts\mpremote.exe` を直接実行できます。

---

## 🛠️ クイックコマンド集

### 1. チップ・フラッシュ情報の確認 (`esptool`)
```powershell
# ボード ② (ESP32-C3 / COM6) の例
uv run esptool --port COM6 flash-id

# ボード ① (ESP32 / COM3) の例
uv run esptool --port COM3 flash-id
```

### 2. MicroPython ファームウェアの書き込み
※ **ESP32 (無印)** と **ESP32-C3** では書き込み開始アドレスが異なるため注意してください。

```powershell
# ▼ ボード ② (ESP32-C3 / COM6) の場合：アドレス 0x0 に書き込む
uv run esptool --port COM6 erase-flash
uv run esptool --port COM6 --baud 460800 write-flash 0x0 ESP32_GENERIC_C3-20260824-v1.29.0.bin

# ▼ ボード ① (ESP32 / COM3) の場合：アドレス 0x1000 に書き込む
uv run esptool --port COM3 erase-flash
uv run esptool --port COM3 --baud 460800 write-flash 0x1000 firmware.bin
```

### 3. スクリプト実行・動作確認 (`mpremote`)

#### 🔹 3機能統合 OLED ステーション（時計/天気・ポモドーロ・Web 伝言板）
[oled_station.py](oled_station.py) を `:main.py` として書き込むと、USB 給電だけで常時起動します。基板上の **BOOT ボタン (`GPIO 9`)** で3つの画面を切り替えられます。

| 操作 (`BOOT` ボタン / `GPIO 9`) | 動作 |
| :--- | :--- |
| **短押し（クリック）** | モード切替：**時計/天気 (`CLK`)** → **ポモドーロ (`POMO`)** → **Web ステータス (`WEB`)** |
| **長押し（0.6秒以上）** | ・`CLK` 中：時刻(NTP)＆天気を再取得<br>・`POMO` 中：タイマー **開始 / 一時停止**<br>・`WEB` 中：伝言メッセージを消去 |

- **Wi-Fi / Web 操作**: [wifi_config.py](wifi_config.py) の Wi-Fi に接続を試み、繋がらない場合は AP モード（SSID: `ESP32-C3-OLED` / パスワード不要 / `http://192.168.4.1`）で起動します。ブラウザからモード切替・ポモドーロ操作・OLED へのメッセージ送信が可能です。
  - ※ **ESP32-C3 0.42" OLED ボード特有の注意点**: 基板上の超小型アンテナの特性上、デフォルトの最大送信出力では周囲の Wi-Fi を検出・接続できないことがあります。そのため [oled_station.py](oled_station.py) では `wlan.config(txpower=8.5)` で送信出力を最適値に下げて安定接続する対策を組み込んでいます。
```powershell
# 本体へ書き込んで自動起動（常時稼働）にする場合
uv run mpremote connect COM6 cp wifi_config.py :wifi_config.py
uv run mpremote connect COM6 cp oled_station.py :main.py
uv run mpremote connect COM6 reset
```

#### 🔹 0.42インチ OLED 画面デモ（ESP32-C3 向け）
内蔵 0.42インチ OLED（72×40 / SSD1306 / `SDA=GPIO 5`, `SCL=GPIO 6`, アドレス `0x3C`）に、チップ温度・空きメモリ・アニメーションを表示します。
※ コントローラ RAM は `128×64` で、物理画面は `X=28, Y=24` からの `72×40` 領域にマッピングされています。
```powershell
# 初回のみドライバを本体へコピー
uv run mpremote connect COM6 cp ssd1306.py :ssd1306.py

# OLED デモを実行
uv run mpremote connect COM6 run oled_demo.py
```

#### 🔹 Lチカテスト
```powershell
# ESP32-C3 用（GPIO 8 通常LED / NeoPixel / GPIO 2 を順番にテスト）
uv run mpremote connect COM6 run blink_c3.py

# 無印 ESP32 用（内蔵LED GPIO 2 を 10 回点滅）
uv run mpremote connect COM3 run blink.py
```

#### 🔹 BOOT ボタン連動 LED（無印 ESP32 向け）
基板上の `BOOT` ボタン (`GPIO 0`) を押している間だけ `GPIO 2` の LED を点灯します。
```powershell
uv run mpremote connect COM3 run button_led.py
```

#### 🔹 IoT Web ダッシュボード（Wi-Fi AP モード）
ESP32 を Wi-Fi 親機（SSID: `ESP32-Dashboard` / パスワード不要）にし、ブラウザ（`http://192.168.4.1`）から LED 操作やセンサー値を確認できます。
```powershell
# 一時実行（例: COM3）
uv run mpremote connect COM3 run web_dashboard.py

# 本体に書き込んで起動時に自動実行させる場合
uv run mpremote connect COM3 cp web_dashboard.py :main.py
```

#### 🔹 MicroPython REPL（対話シェル）
```powershell
uv run mpremote connect COM6 repl
```
（終了するには `Ctrl + ]`）

---

## 📚 関連ドキュメント

> 以下のドキュメントは主に **ボード ①（ESP32 30ピン / DOIT DevKit V1 互換）** 向けに作成した資料です。

- 📌 **全ピンの役割・機能早見表**: [docs/pinout.md](docs/pinout.md)
- 📖 **内部構造・通信の仕組み解説**: [docs/how-it-works.md](docs/how-it-works.md)
- 💡 **工作・活用プロジェクトアイデア集**: [docs/ideas.md](docs/ideas.md)
- 🧪 **初回立ち上げ・IoTダッシュボード実験記録 (ESP32)**: [docs/experiment_log_20261121.md](docs/experiment_log_20261121.md)
- 🧪 **ESP32-C3 (0.42" OLED) 立ち上げ・Wi-Fi対策記録**: [docs/experiment_log_20261128.md](docs/experiment_log_20261128.md)
- 📄 **公式スペックシート (PDF)**: [docs/esp32_spec.pdf](docs/esp32_spec.pdf)
