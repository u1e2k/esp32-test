import gc
import json
import network
import ntptime
import socket
import time
import uselect
import esp32
from machine import Pin, SoftI2C
import ssd1306

# ===== ハードウェア設定 (ESP32-C3 + 0.42" OLED) =====
I2C_SDA = 5
I2C_SCL = 6
OLED_ADDR = 0x3C
BOOT_PIN = 9

# 物理パネル 72x40 (コントローラ 128x64 上のオフセット)
OLED_W = 128
OLED_H = 64
X_OFF = 28
Y_OFF = 24
VIEW_W = 72
VIEW_H = 40

# ===== アプリ設定 =====
LAT = 35.6762  # 東京
LON = 139.6503
JST_OFFSET = 9 * 3600
WEATHER_REFRESH_MS = 15 * 60 * 1000
WORK_SEC = 25 * 60
BREAK_SEC = 5 * 60
WEEKDAYS = ("MON", "TUE", "WED", "THU", "FRI", "SAT", "SUN")

MODE_CLOCK = 0
MODE_POMO = 1
MODE_WEB = 2
MODE_NAMES = ("CLK", "POMO", "WEB")

# 8x8 天気アイコン (各行 8bit MSB->LSB)
WEATHER_ICONS = {
    "SUN": (0x18, 0x99, 0x3C, 0x7E, 0x7E, 0x3C, 0x99, 0x18),
    "CLD": (0x00, 0x1C, 0x3E, 0x7F, 0xFF, 0xFF, 0x7E, 0x00),
    "RAN": (0x1C, 0x3E, 0x7F, 0xFF, 0x00, 0x49, 0x92, 0x24),
    "SNW": (0x24, 0x18, 0x7E, 0x18, 0x24, 0x00, 0x52, 0x24),
    "THN": (0x1C, 0x3E, 0x7F, 0x18, 0x30, 0x78, 0x18, 0x30),
}


def weather_label(code: int) -> str:
    if code in (0, 1):
        return "SUN"
    if code in (2, 3, 45, 48):
        return "CLD"
    if code in (71, 73, 75, 77, 85, 86):
        return "SNW"
    if code in (95, 96, 99):
        return "THN"
    return "RAN"


class MiniDisplay:
    """72x40 の仮想座標系で SSD1306 を扱うラッパー。"""

    def __init__(self, oled: ssd1306.SSD1306_I2C) -> None:
        self.oled = oled

    def clear(self) -> None:
        self.oled.fill(0)

    def text(self, s: str, x: int, y: int, col: int = 1) -> None:
        self.oled.text(s[:9], X_OFF + x, Y_OFF + y, col)

    def rect(self, x: int, y: int, w: int, h: int, col: int = 1) -> None:
        self.oled.rect(X_OFF + x, Y_OFF + y, w, h, col)

    def fill_rect(self, x: int, y: int, w: int, h: int, col: int = 1) -> None:
        self.oled.fill_rect(X_OFF + x, Y_OFF + y, w, h, col)

    def icon8x8(self, name: str, x: int, y: int) -> None:
        bits = WEATHER_ICONS.get(name, WEATHER_ICONS["CLD"])
        for row, byte in enumerate(bits):
            for bit in range(8):
                if (byte >> (7 - bit)) & 1:
                    self.oled.pixel(X_OFF + x + bit, Y_OFF + y + row, 1)

    def draw_mode_dots(self, mode: int) -> None:
        # 画面右下に 3つの小さなモードインジケータを表示
        base_x = 52
        y = 35
        for i in range(3):
            x = base_x + i * 6
            if i == mode:
                self.fill_rect(x, y, 4, 4, 1)
            else:
                self.rect(x, y, 4, 4, 1)

    def show(self) -> None:
        self.oled.show()

    def flash(self, times: int = 3) -> None:
        for _ in range(times):
            self.oled.invert(1)
            time.sleep(0.18)
            self.oled.invert(0)
            time.sleep(0.18)


def url_decode(s: str) -> str:
    res = bytearray()
    i = 0
    while i < len(s):
        ch = s[i]
        if ch == "+":
            res.append(32)
            i += 1
        elif ch == "%" and i + 2 < len(s):
            try:
                res.append(int(s[i + 1 : i + 3], 16))
                i += 3
                continue
            except ValueError:
                pass
            res.extend(ch.encode())
            i += 1
        else:
            res.extend(ch.encode())
            i += 1
    try:
        return res.decode("utf-8")
    except Exception:
        return "".join(chr(b) if 32 <= b < 127 else "?" for b in res)


def connect_wifi(disp: MiniDisplay):
    disp.clear()
    disp.text("Wi-Fi...", 0, 12)
    disp.show()

    ssid = None
    password = None
    try:
        import wifi_config

        ssid = wifi_config.WIFI_SSID
        password = wifi_config.WIFI_PASS
    except Exception:
        pass

    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    # ESP32-C3 0.42" OLED ボード特有のアンテナ干渉対策として送信出力を 8.5dBm に制限
    try:
        wlan.config(txpower=8.5)
    except Exception:
        pass
    if ssid and password:
        wlan.connect(ssid, password)
        for _ in range(24):
            if wlan.isconnected():
                ip = wlan.ifconfig()[0]
                print("Wi-Fi connected:", ip)
                return wlan, ip, False
            time.sleep(0.4)

    wlan.active(False)
    ap = network.WLAN(network.AP_IF)
    ap.active(True)
    try:
        ap.config(txpower=8.5)
    except Exception:
        pass
    ap.config(essid="ESP32-C3-OLED", authmode=network.AUTH_OPEN)
    ip = ap.ifconfig()[0]
    print("AP mode started:", ip)
    return ap, ip, True


def sync_ntp() -> bool:
    try:
        ntptime.host = "ntp.nict.jp"
        ntptime.settime()
        print("NTP synced")
        return True
    except Exception as e:
        print("NTP failed:", e)
        return False


def fetch_weather():
    """Open-Meteo から現在気温と天気コードを取得する。"""
    host = "api.open-meteo.com"
    path = (
        f"/v1/forecast?latitude={LAT}&longitude={LON}"
        "&current=temperature_2m,weather_code&timezone=Asia%2FTokyo"
    )
    s = None
    try:
        addr = socket.getaddrinfo(host, 80)[0][-1]
        s = socket.socket()
        s.settimeout(3.0)
        s.connect(addr)
        req = f"GET {path} HTTP/1.0\r\nHost: {host}\r\nConnection: close\r\n\r\n"
        s.send(req.encode())
        chunks = []
        while True:
            data = s.recv(512)
            if not data:
                break
            chunks.append(data)
        raw = b"".join(chunks).decode("utf-8", "ignore")
        body = raw.split("\r\n\r\n", 1)[-1]
        parsed = json.loads(body)
        cur = parsed.get("current", {})
        temp = cur.get("temperature_2m")
        code = cur.get("weather_code")
        if temp is not None and code is not None:
            return round(temp), weather_label(int(code))
    except Exception as e:
        print("Weather fetch error:", e)
    finally:
        if s:
            try:
                s.close()
            except Exception:
                pass
    return None, None


class OledStation:
    def __init__(self) -> None:
        i2c = SoftI2C(sda=Pin(I2C_SDA), scl=Pin(I2C_SCL), freq=400000)
        oled = ssd1306.SSD1306_I2C(OLED_W, OLED_H, i2c, addr=OLED_ADDR)
        self.disp = MiniDisplay(oled)
        self.btn = Pin(BOOT_PIN, Pin.IN, Pin.PULL_UP)

        self.mode = MODE_CLOCK
        self.wlan, self.ip, self.is_ap = connect_wifi(self.disp)

        self.ntp_ok = False
        self.weather_temp = None
        self.weather_cond = "CLD"
        self.last_weather_ms = -WEATHER_REFRESH_MS

        if not self.is_ap:
            self.disp.clear()
            self.disp.text("Sync...", 0, 12)
            self.disp.show()
            self.ntp_ok = sync_ntp()
            t, c = fetch_weather()
            if t is not None:
                self.weather_temp = t
                self.weather_cond = c
            self.last_weather_ms = time.ticks_ms()

        # ポモドーロ状態
        self.pomo_is_work = True
        self.pomo_cycle = 1
        self.pomo_running = False
        self.pomo_rem = WORK_SEC
        self.pomo_last_tick_ms = time.ticks_ms()

        # Web 伝言メッセージ
        self.web_msg = ""

        # ボタン状態管理
        self.btn_down = False
        self.btn_down_ms = 0
        self.btn_long_fired = False

        # HTTP サーバー（ノンブロッキング）
        self.srv = socket.socket()
        self.srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.srv.bind(("0.0.0.0", 80))
        self.srv.listen(3)
        self.srv.setblocking(False)
        self.poller = uselect.poll()
        self.poller.register(self.srv, uselect.POLLIN)

        self.last_draw_ms = 0

    def toggle_pomo(self) -> None:
        self.pomo_running = not self.pomo_running
        self.pomo_last_tick_ms = time.ticks_ms()

    def reset_pomo(self) -> None:
        self.pomo_running = False
        self.pomo_is_work = True
        self.pomo_cycle = 1
        self.pomo_rem = WORK_SEC

    def update_pomo(self, now_ms: int) -> None:
        if not self.pomo_running:
            self.pomo_last_tick_ms = now_ms
            return
        elapsed = time.ticks_diff(now_ms, self.pomo_last_tick_ms)
        if elapsed >= 1000:
            sec = elapsed // 1000
            self.pomo_last_tick_ms = time.ticks_add(self.pomo_last_tick_ms, sec * 1000)
            self.pomo_rem -= sec
            if self.pomo_rem <= 0:
                self.pomo_running = False
                self.disp.flash(3)
                if self.pomo_is_work:
                    self.pomo_is_work = False
                    self.pomo_rem = BREAK_SEC
                else:
                    self.pomo_is_work = True
                    self.pomo_cycle += 1
                    self.pomo_rem = WORK_SEC

    def handle_button(self, now_ms: int) -> bool:
        pressed = self.btn.value() == 0
        changed = False

        if pressed and not self.btn_down:
            self.btn_down = True
            self.btn_down_ms = now_ms
            self.btn_long_fired = False
        elif pressed and self.btn_down and not self.btn_long_fired:
            if time.ticks_diff(now_ms, self.btn_down_ms) >= 600:
                self.btn_long_fired = True
                changed = True
                if self.mode == MODE_POMO:
                    self.toggle_pomo()
                elif self.mode == MODE_CLOCK and not self.is_ap:
                    self.ntp_ok = sync_ntp()
                    t, c = fetch_weather()
                    if t is not None:
                        self.weather_temp = t
                        self.weather_cond = c
                    self.last_weather_ms = now_ms
                elif self.mode == MODE_WEB:
                    self.web_msg = ""
        elif not pressed and self.btn_down:
            held = time.ticks_diff(now_ms, self.btn_down_ms)
            self.btn_down = False
            if not self.btn_long_fired and held >= 35:
                self.mode = (self.mode + 1) % 3
                changed = True

        return changed

    def build_html(self) -> str:
        t_c = esp32.mcu_temperature()
        p_phase = "WORK" if self.pomo_is_work else "REST"
        p_state = "RUNNING" if self.pomo_running else "PAUSED"
        pm, ps = divmod(self.pomo_rem, 60)
        w_str = f"{self.weather_temp}C ({self.weather_cond})" if self.weather_temp is not None else "N/A"
        msg_esc = self.web_msg.replace("&", "&amp;").replace("<", "&lt;").replace('"', "&quot;")
        return f"""<!DOCTYPE html>
<html lang="ja"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>ESP32-C3 OLED</title>
<style>
body{{font-family:sans-serif;background:#111827;color:#f3f4f6;margin:0;padding:16px}}
.card{{max-width:420px;margin:0 auto 14px;background:#1f2937;border-radius:12px;padding:14px}}
h2{{margin:0 0 10px;font-size:1.1rem;color:#60a5fa}}
.row{{display:flex;gap:8px;flex-wrap:wrap;margin-top:8px}}
a.btn,button{{flex:1;min-width:80px;text-align:center;text-decoration:none;background:#374151;color:#fff;padding:10px;border-radius:8px;border:none;font-size:0.95rem;cursor:pointer}}
a.active{{background:#2563eb;font-weight:bold}}
input{{width:100%;box-sizing:border-box;padding:10px;border-radius:8px;border:1px solid #4b5563;background:#111827;color:#fff;margin-bottom:8px}}
</style></head><body>
<div class="card">
<h2>ESP32-C3 OLED Hub ({self.ip})</h2>
<div>Mode: <b>{MODE_NAMES[self.mode]}</b> | Weather: <b>{w_str}</b> | MCU: <b>{t_c}C</b></div>
<div class="row">
<a class="btn {'active' if self.mode==0 else ''}" href="/cmd?mode=0">Clock</a>
<a class="btn {'active' if self.mode==1 else ''}" href="/cmd?mode=1">Pomodoro</a>
<a class="btn {'active' if self.mode==2 else ''}" href="/cmd?mode=2">Web Stat</a>
</div></div>
<div class="card">
<h2>Pomodoro ({p_phase} #{self.pomo_cycle}) - {pm:02d}:{ps:02d} [{p_state}]</h2>
<div class="row">
<a class="btn" href="/cmd?pomo=toggle">{'Pause' if self.pomo_running else 'Start'}</a>
<a class="btn" href="/cmd?pomo=reset">Reset</a>
</div></div>
<div class="card">
<h2>OLED Message (ASCII)</h2>
<form action="/cmd" method="get">
<input type="text" name="msg" maxlength="18" value="{msg_esc}" placeholder="Hello! (max 18 chars)">
<button type="submit">Send to OLED</button>
</form></div>
</body></html>"""

    def handle_http(self) -> bool:
        events = self.poller.poll(0)
        if not events:
            return False

        changed = False
        conn = None
        try:
            conn, _ = self.srv.accept()
            conn.settimeout(1.0)
            req = conn.recv(1024).decode("utf-8", "ignore")
            first_line = req.split("\r\n", 1)[0]
            parts = first_line.split(" ")
            path = parts[1] if len(parts) > 1 else "/"

            if path.startswith("/cmd?"):
                query = path.split("?", 1)[1]
                for kv in query.split("&"):
                    if "=" not in kv:
                        continue
                    k, v = kv.split("=", 1)
                    v = url_decode(v)
                    if k == "mode" and v in ("0", "1", "2"):
                        self.mode = int(v)
                        changed = True
                    elif k == "pomo":
                        if v == "toggle":
                            self.toggle_pomo()
                        elif v == "reset":
                            self.reset_pomo()
                        changed = True
                    elif k == "msg":
                        self.web_msg = v[:18]
                        self.mode = MODE_WEB
                        changed = True
                conn.send(b"HTTP/1.0 302 Found\r\nLocation: /\r\n\r\n")
            else:
                html = self.build_html().encode("utf-8")
                conn.send(b"HTTP/1.0 200 OK\r\nContent-Type: text/html; charset=utf-8\r\nConnection: close\r\n\r\n")
                conn.sendall(html)
        except Exception:
            pass
        finally:
            if conn:
                try:
                    conn.close()
                except Exception:
                    pass
        return changed

    def draw(self) -> None:
        d = self.disp
        d.clear()

        if self.mode == MODE_CLOCK:
            lt = time.localtime(time.time() + JST_OFFSET)
            date_str = f"{lt[1]:02d}/{lt[2]:02d} {WEEKDAYS[lt[6]]}"
            time_str = f"{lt[3]:02d}:{lt[4]:02d}:{lt[5]:02d}"
            d.text(date_str, 0, 0)
            d.text(time_str, 4, 11)
            d.icon8x8(self.weather_cond, 0, 23)
            if self.weather_temp is not None:
                d.text(f"{self.weather_temp:2d}C {self.weather_cond}", 11, 23)
            else:
                d.text("--C", 11, 23)

        elif self.mode == MODE_POMO:
            phase = "WORK" if self.pomo_is_work else "REST"
            d.text(f"{phase} #{self.pomo_cycle}", 0, 0)
            pm, ps = divmod(self.pomo_rem, 60)
            mark = ">" if self.pomo_running else "||"
            d.text(f"{pm:02d}:{ps:02d} {mark}", 4, 11)

            total = WORK_SEC if self.pomo_is_work else BREAK_SEC
            ratio = (total - self.pomo_rem) / total if total > 0 else 0
            bar_w = int(68 * ratio)
            d.rect(0, 23, 70, 7)
            if bar_w > 0:
                d.fill_rect(1, 24, bar_w, 5)

            hint = "Hold:Stp" if self.pomo_running else "Hold:Go"
            d.text(hint[:6], 0, 32)

        else:  # MODE_WEB
            header = "AP MODE" if self.is_ap else "WEB STAT"
            d.text(header, 0, 0)
            # IP を 72px 幅に収まるよう 2行に分割
            ip_parts = self.ip.split(".")
            if len(ip_parts) == 4:
                d.text(f"{ip_parts[0]}.{ip_parts[1]}.", 0, 10)
                d.text(f".{ip_parts[2]}.{ip_parts[3]}", 16, 18)
            else:
                d.text(self.ip, 0, 10)

            if self.web_msg:
                d.text(self.web_msg[:9], 0, 29)
            else:
                d.text(f"T:{esp32.mcu_temperature()}C", 0, 29)

        d.draw_mode_dots(self.mode)
        d.show()

    def run(self) -> None:
        print(f"OLED Station started! Open http://{self.ip}")
        while True:
            now_ms = time.ticks_ms()

            if not self.is_ap and time.ticks_diff(now_ms, self.last_weather_ms) >= WEATHER_REFRESH_MS:
                t, c = fetch_weather()
                if t is not None:
                    self.weather_temp = t
                    self.weather_cond = c
                self.last_weather_ms = now_ms
                gc.collect()

            self.update_pomo(now_ms)
            btn_changed = self.handle_button(now_ms)
            web_changed = self.handle_http()

            if btn_changed or web_changed or time.ticks_diff(now_ms, self.last_draw_ms) >= 250:
                self.draw()
                self.last_draw_ms = now_ms

            time.sleep_ms(20)


if __name__ == "__main__":
    OledStation().run()
