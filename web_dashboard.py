import esp32
import gc
import json
import network
import socket
import time
from machine import Pin, TouchPad

# ハードウェア
led = Pin(2, Pin.OUT)
led.off()

boot_btn = Pin(0, Pin.IN, Pin.PULL_UP)
touch_d4 = TouchPad(Pin(4))
start_time = time.ticks_ms()

# Wi-Fi接続
try:
    import wifi_config
    SSID = wifi_config.WIFI_SSID
    PASS = wifi_config.WIFI_PASS
except Exception:
    SSID = None
    PASS = None

wlan = network.WLAN(network.STA_IF)
wlan.active(True)
if SSID and PASS:
    print(f"Wi-Fi ({SSID}) に接続中...")
    wlan.connect(SSID, PASS)
    for _ in range(30):
        if wlan.isconnected():
            break
        time.sleep(0.5)

if wlan.isconnected():
    assigned_ip = wlan.ifconfig()[0]
    print("=" * 45)
    print(" Wi-Fi接続成功!")
    print(f" URL: http://{assigned_ip}")
    print("=" * 45)
else:
    print("Wi-Fi接続失敗 -> APモードで起動")
    ap = network.WLAN(network.AP_IF)
    ap.active(True)
    ap.config(essid="ESP32-Dashboard", authmode=network.AUTH_OPEN)
    assigned_ip = "192.168.4.1"

# ダッシュボードHTML
HTML_PAGE = """<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>ESP32 Dashboard</title>
<style>
body{background:#0f172a;color:#f8fafc;font-family:sans-serif;margin:0;padding:16px;display:flex;justify-content:center}
.c{max-width:440px;width:100%;display:flex;flex-direction:column;gap:12px}
h1{color:#38bdf8;font-size:1.3rem;margin:4px 0;text-align:center}
.card{background:#1e293b;border:1px solid #334155;border-radius:10px;padding:14px}
.row{display:flex;justify-content:space-between;align-items:center}
.val{font-size:1.6rem;font-weight:bold}
.sub{color:#94a3b8;font-size:0.8rem}
.badge{padding:3px 8px;border-radius:12px;font-size:0.75rem;background:#334155;color:#94a3b8}
.on{background:#15803d;color:#86efac}
.red{background:#b91c1c;color:#fca5a5}
.btn{width:100%;padding:12px;font-size:1rem;font-weight:bold;border:none;border-radius:8px;background:#0284c7;color:#fff;cursor:pointer;margin-top:8px}
.bar{height:8px;background:#334155;border-radius:4px;overflow:hidden;margin-top:8px}
.bar-in{height:100%;background:#38bdf8;width:0%;transition:width .2s}
.grid{display:grid;grid-template-columns:1fr 1fr;gap:10px}
</style>
</head>
<body>
<div class="c">
  <h1>ESP32 Live Dashboard</h1>
  <div class="card">
    <div class="sub">内蔵LED (GPIO 2)</div>
    <div class="row"><div class="val" id="lt">OFF</div><span class="badge" id="lb">消灯中</span></div>
    <button class="btn" onclick="toggleLED()">LED を切り替える</button>
  </div>
  <div class="card">
    <div class="sub">D4 ネジ・タッチセンサー (静電容量)</div>
    <div class="row"><div class="val" id="tv">---</div><span class="badge" id="tb">離れています</span></div>
    <div class="bar"><div class="bar-in" id="tbar"></div></div>
    <div class="sub" style="margin-top:4px">※D4端子のネジに指で触れてください</div>
  </div>
  <div class="grid">
    <div class="card">
      <div class="sub">CPU 内蔵温度</div>
      <div class="val"><span id="tp">--</span> <span style="font-size:1rem;color:#94a3b8">℃</span></div>
    </div>
    <div class="card">
      <div class="sub">[BOOT] ボタン</div>
      <div class="val" id="bt" style="font-size:1.2rem">UP</div>
      <span class="badge" id="bb" style="margin-top:4px">未押下</span>
    </div>
  </div>
  <div class="card" style="font-size:0.8rem;color:#94a3b8">
    <div class="row"><span>空きメモリ: <b id="mf" style="color:#fff">--</b> KB</span><span>稼働時間: <b id="up" style="color:#fff">--</b> 秒</span></div>
  </div>
</div>
<script>
async function upd(){
  try{
    const r=await fetch('/api/status');
    const d=await r.json();
    document.getElementById('lt').innerText=d.led?'ON':'OFF';
    document.getElementById('lb').className=d.led?'badge on':'badge';
    document.getElementById('lb').innerText=d.led?'点灯中':'消灯中';
    document.getElementById('tv').innerText=d.touch;
    document.getElementById('tb').className=d.touched?'badge on':'badge';
    document.getElementById('tb').innerText=d.touched?'👉 触れています！':'離れています';
    document.getElementById('tbar').style.width=Math.min(100,Math.max(0,(d.touch/800)*100))+'%';
    document.getElementById('tp').innerText=d.temp_c;
    document.getElementById('bt').innerText=d.boot_pressed?'DOWN':'UP';
    document.getElementById('bb').className=d.boot_pressed?'badge red':'badge';
    document.getElementById('bb').innerText=d.boot_pressed?'押下中！':'未押下';
    document.getElementById('mf').innerText=d.free_kb;
    document.getElementById('up').innerText=d.uptime_s;
  }catch(e){}
}
async function toggleLED(){
  try{await fetch('/api/led?action=toggle');upd();}catch(e){}
}
setInterval(upd,1000);
upd();
</script>
</body>
</html>
"""

HTML_BYTES = HTML_PAGE.encode("utf-8")
HTML_HDR = (
    b"HTTP/1.1 200 OK\r\n"
    b"Content-Type: text/html; charset=utf-8\r\n"
    b"Content-Length: " + str(len(HTML_BYTES)).encode() + b"\r\n"
    b"Connection: close\r\n\r\n"
)

# ソケットサーバー初期化
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
s.bind(("", 80))
s.listen(5)
print(f"Webサーバー待機中: http://{assigned_ip}")

while True:
    try:
        conn, addr = s.accept()
        conn.settimeout(3.0)
        req = conn.recv(1024).decode()
        if not req:
            conn.close()
            continue

        parts = req.split()
        if len(parts) >= 2:
            path = parts[1]

            if path == "/api/status":
                touch_val = touch_d4.read()
                raw_f = esp32.raw_temperature()
                temp_c = round((raw_f - 32) * 5 / 9, 1)
                boot_pressed = (boot_btn.value() == 0)
                uptime_s = time.ticks_diff(time.ticks_ms(), start_time) // 1000
                free_kb = round(gc.mem_free() / 1024, 1)

                body = json.dumps({
                    "led": bool(led.value()),
                    "touch": touch_val,
                    "touched": bool(touch_val < 350),
                    "temp_c": temp_c,
                    "boot_pressed": boot_pressed,
                    "free_kb": free_kb,
                    "uptime_s": uptime_s,
                }).encode()

                hdr = (
                    b"HTTP/1.1 200 OK\r\n"
                    b"Content-Type: application/json\r\n"
                    b"Content-Length: " + str(len(body)).encode() + b"\r\n"
                    b"Connection: close\r\n\r\n"
                )
                conn.sendall(hdr + body)

            elif path.startswith("/api/led"):
                if "action=toggle" in path:
                    led.value(not led.value())
                body = b"{\"ok\":true}"
                hdr = (
                    b"HTTP/1.1 200 OK\r\n"
                    b"Content-Type: application/json\r\n"
                    b"Content-Length: " + str(len(body)).encode() + b"\r\n"
                    b"Connection: close\r\n\r\n"
                )
                conn.sendall(hdr + body)

            elif path == "/" or path == "/index.html":
                conn.sendall(HTML_HDR + HTML_BYTES)

            else:
                conn.sendall(b"HTTP/1.1 404 Not Found\r\nContent-Length: 0\r\nConnection: close\r\n\r\n")

        conn.close()
        gc.collect()
    except Exception as e:
        try:
            conn.close()
        except Exception:
            pass
