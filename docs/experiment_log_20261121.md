---
title: ESP32 & MicroPython 初回立ち上げ・IoTダッシュボード実験記録
date: 2026-11-21
tags:
  - esp32
  - micropython
  - iot
  - electronics
categories:
  - Hardware
---

# ESP32 & MicroPython 初回立ち上げ・IoTダッシュボード実験記録

2026年11月21日に実施した ESP32 開発ボードの環境構築、各種基本機能テスト、および外付け部品ゼロでの IoT Web ダッシュボード構築の実験レポートです。

---

## 1. 使用機材・ハードウェア

* **メインマイコン**: ESP32-D0WD-V3 (revision v3.1 / Xtensa LX6 Dual Core 240MHz)
* **フォームファクタ**: NodeMCU-32S Lua 30Pin (DOIT DevKit V1 互換) / **USB Type-C**
* **拡張ボード**: スクリューターミナル（緑色・ネジ留め端子台）ベースボード
* **フラッシュ容量**: 4MB (Flash voltage: 3.3V)
* **シリアル変換IC**: USB-SERIAL CH340 (`VID: 1A86`, `PID: 7523`) / `COM3`

---

## 2. 実施内容と検証結果

### ① 開発環境の構築 (Python / uv)
* パッケージ管理ツール `uv` を採用し、`esptool` および `mpremote` によるシリアル操作環境を整備。
* エディタの `from machine import Pin` エラー（missing-import）を解消するため、`micropython-esp32-stubs` を導入。インテリセンス・型補完を有効化。

### ② ファームウェアの導入 & 初Lチカ
* MicroPython 安定版ファームウェア（`ESP32_GENERIC`）をフラッシュメモリに消去・書き込み（0x1000）。
* `blink.py` を作成し、オンボード青色LED（`GPIO 2`）が 0.5 秒間隔で点滅することを確認。

### ③ 基板上ボタンの仕様把握 & 入力実験
* **EN (RST) ボタン**: チップのハードウェア再起動ピン。
* **BOOT (IO0) ボタン**: 起動時のブートローダー切替 兼 プログラム入力（`GPIO 0`）。
* `button_led.py` を作成し、BOOTボタンを押している間だけLEDが点灯する制御を検証。

### ④ 内蔵センサーの探索と仕様特定
* **D4 ネジ・タッチセンサー（静電容量式 TouchPad）**:
  * 外付けセンサーなしで、拡張ボードの **D4 端子ネジ** に指で触れるだけで値が約680から100〜200台へと激変することを実証。
* **CPU内蔵温度センサー**:
  * `esp32.raw_temperature()` によりチップ内部温度（約48〜50℃）が取得可能であることを確認。
* **磁気（ホール）センサーの調査**:
  * 初期ロットには存在したが、本基板のチップリビジョン（v3.1）および最新ESP-IDF/MicroPythonではメーカー公式に非推奨・廃止されていることを特定。

### ⑤ Wi-Fi & リアルタイム Web ダッシュボードの実装
* 1Password CLI (`op`) より自宅Wi-Fiの認証情報を安全に取得し、`wifi_config.py` として設定（Git対象外に保護）。
* 同期ソケット（`socket`）を用いた超軽量 HTTP Webサーバー（`web_dashboard.py`）を構築：
  * **応答速度**: 約 0.07 秒（爆速レスポンス）
  * **機能**: ブラウザ上のボタンからLED遠隔操作、D4タッチ検知、BOOTボタン押下、CPU温度、空きメモリ、稼働秒数を1秒毎にリアルタイム描画。
* `mpremote cp web_dashboard.py :main.py` により本体へ書き込み、**PCと切り離してもUSB給電のみで独立稼働するスタンドアロン動作** を達成。

---

## 3. 作成・整備したファイル一覧

| ファイル | 概要 |
| :--- | :--- |
| [README.md](file:///C:/Users/user/repos/esp32-test/README.md) | プロジェクト概要、接続情報、コマンド集 |
| [docs/pinout.md](file:///C:/Users/user/repos/esp32-test/docs/pinout.md) | 30ピン＋ネジ留め端子台のピン配置・役割早見表 |
| [docs/how-it-works.md](file:///C:/Users/user/repos/esp32-test/docs/how-it-works.md) | Raw REPL 通信シーケンス、スペック詳細、Arduinoとの違い |
| [docs/ideas.md](file:///C:/Users/user/repos/esp32-test/docs/ideas.md) | マクロキーボード、OLED時計、通知ガジェットの工作案 |
| [docs/esp32_spec.pdf](file:///C:/Users/user/repos/esp32-test/docs/esp32_spec.pdf) | ボード公式仕様書（PDF保管） |
| [blink.py](file:///C:/Users/user/repos/esp32-test/blink.py) | 基本Lチカスクリプト |
| [button_led.py](file:///C:/Users/user/repos/esp32-test/button_led.py) | BOOTボタン連動点灯スクリプト |
| [web_dashboard.py](file:///C:/Users/user/repos/esp32-test/web_dashboard.py) | Wi-Fi接続・リアルタイムIoTダッシュボードサーバー |

---

## 4. 今後の展望・ステップアップ案
1. **0.96インチ OLEDディスプレイ（SSD1306）の導入**:
   * 端子台（3V3, GND, D21/SDA, D22/SCL）にネジ留め4本で卓上スマートクロック・情報表示器を作成。
2. **PC / クラウド通知アラート**:
   * メールやDiscord/Slack新着、カレンダー予定を画面とLED点滅でお知らせする卓上通知ガジェット化。
3. **Bluetooth BLE マクロキーボード**:
   * 端子台にメカニカルキースイッチを接続し、ハンダ付け不要のワイヤレス左手デバイスを作成。
