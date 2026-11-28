---
title: ESP32-C3 (0.42インチ OLED 搭載) 立ち上げ・Wi-Fi 安定化・3機能ステーション実験記録
date: 2026-11-28
tags:
  - esp32-c3
  - micropython
  - oled
  - ssd1306
  - wifi
  - iot
categories:
  - Hardware
---

# ESP32-C3 (0.42インチ OLED 搭載) 立ち上げ・実験記録

2026年11月28日に実施した、画面付き超小型 **ESP32-C3** ボードの立ち上げ、内蔵 OLED 仕様の特定、Wi-Fi 接続トラブルの解決（`txpower` 調整）、および 3機能統合ステーション構築の記録です。

---

## 1. 使用機材・ハードウェア仕様

* **メインマイコン**: ESP32-C3 (QFN32 / revision v0.4 / RISC-V Single Core 160MHz)
* **ワイヤレス**: Wi-Fi (2.4GHz), Bluetooth 5 (LE) ※Classic Bluetooth 非対応
* **フラッシュ / 水晶**: Embedded Flash 4MB (XMC) / 40MHz
* **MAC アドレス**: `9c:cc:01:ab:99:ec`
* **USB 接続**: 内蔵 **USB-Serial/JTAG** (`VID: 303A`, `PID: 1001`) / `COM6`（CH340 等の外付け変換 IC なし）
* **内蔵ディスプレイ**: 0.42インチ OLED（物理 `72×40` ピクセル / SSD1306 / I2C `0x3C`）
  * `SDA`: `GPIO 5` / `SCL`: `GPIO 6`
* **基板上ボタン**: `BOOT` ボタン = `GPIO 9`（内部プルアップ、押下で `0`）
* **購入先**: [AliExpress (Item 1005009157602185)](https://ja.aliexpress.com/item/1005009157602185.html)

---

## 2. 無印 ESP32 との違い・ハマりどころと解決知見

### ① ファームウェア書き込みアドレスの違い
* 無印 ESP32 は `0x1000` から書き込むが、**ESP32-C3 は `0x0` から書き込む**必要がある。
* 使用ファームウェア: `ESP32_GENERIC_C3-20260824-v1.29.0.bin`
  ```powershell
  uv run esptool --port COM6 erase-flash
  uv run esptool --port COM6 --baud 460800 write-flash 0x0 ESP32_GENERIC_C3-20260824-v1.29.0.bin
  ```

### ② 0.42インチ OLED (72×40) の座標オフセット
* SSD1306 ドライバはコントローラ仕様上 **`128×64`** として初期化する。
* ただし物理ガラス面は RAM 領域の中央寄りにクロップされており、`(0, 0)` に描画すると画面外になる。
* 本ボードでは **`X_OFF = 28`, `Y_OFF = 24`** を基準に `72×40` の枠内に描画することでぴったり収まることを確認（[oled_demo.py](../oled_demo.py)）。

### ③ 【重要】Wi-Fi が 0件しか見つからない問題と `txpower=8.5` 対策
* **症状**: `wlan.scan()` を実行しても `FOUND: 0` となり、ルーターがすぐ近くにあっても SSID を一切検出できず、AP モードへフォールバックしてしまう。
* **原因**: 0.42インチ OLED 搭載 ESP32-C3 や SuperMini 系ボードで広く知られているハードウェア特性。超小型基板上のセラミックアンテナ周辺のインピーダンス不整合・RF 反射により、デフォルトの最大送信出力では自らの電波が歪んで通信が成立しない。
* **解決策**: `wlan.active(True)` の直後に **送信出力を `8.5 dBm` に下げる**。
  ```python
  wlan = network.WLAN(network.STA_IF)
  wlan.active(True)
  wlan.config(txpower=8.5)
  ```
* **効果**: 設定前は 0件だったスキャン結果が、設定直後に **8件（`HUAWEI-010X4C`, RSSI `-56`）** へと劇的に改善し、Wi-Fi 接続（`192.168.0.12`）・NTP 同期・Open-Meteo 天気取得のすべてが安定動作した。
* **注意点**: AP モードと STA モードを切り替える際や連続設定時に `OSError: Wifi Internal State Error` が出ることがあるため、切り替え時は `active(False)` を挟むか `try/except` で保護すると安全。

### ④ 基板上の BOOT ボタンの GPIO 番号
* 無印 ESP32 は `GPIO 0` だが、**ESP32-C3 は `GPIO 9`** が `BOOT` ボタンになっている。

---

## 3. 構築したアプリケーション：`oled_station.py`（`:main.py`）

USB 給電のみで自動起動し、基板上の `BOOT` ボタン（`GPIO 9`）1つで操作できる 3機能統合ステーションを構築しました（[oled_station.py](../oled_station.py)）。

1. **時計＆天気 (`CLK`)**: `ntp.nict.jp` で日本時間を同期し、Open-Meteo（HTTP API）から東京の気温と天気を取得して 8×8 ドットアイコン付きで表示。
2. **ポモドーロタイマー (`POMO`)**: 作業 25分 ↔ 休憩 5分のカウントダウン、プログレスバー、終了時の画面フラッシュ通知。
3. **Web ステータス＆伝言板 (`WEB`)**: `uselect.poll()` を使ったノンブロッキング HTTP サーバーを内蔵し、同一ネットワーク上のスマホ・PC（`http://192.168.0.12`）からモード切替・タイマー操作・OLED へのメッセージ送信が可能。
