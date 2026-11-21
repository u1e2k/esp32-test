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

## 基板上のボタン
- **EN (RST)**: チップのハードウェアリセット（再起動）。フリーズ時や最初からやり直す際に使用。
- **BOOT (IO0)**: 起動モード切り替え ＆ ユーザー入力（`Pin(0, Pin.IN)` で通常のプッシュスイッチとしても利用可能）。

詳細な内部仕様やコード転送の仕組みは [docs/how-it-works.md](docs/how-it-works.md) を参照してください。

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

### MicroPython インタラクティブ REPL 接続
```powershell
uv run --with mpremote mpremote connect COM3 repl
```
（終了時は `Ctrl + ]`）

### ボード起動時に自動常時実行させたい場合 (`main.py` として書き込み)
```powershell
uv run --with mpremote mpremote connect COM3 cp blink.py :main.py
```
