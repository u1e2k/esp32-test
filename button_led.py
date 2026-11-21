import time
from machine import Pin

# 内蔵LED (GPIO 2)
led = Pin(2, Pin.OUT)
# BOOTボタン (GPIO 0: 押すと 0, 離すと 1)
button = Pin(0, Pin.IN, Pin.PULL_UP)

print("=" * 45)
print("  BOOTボタン連動 LEDスクリプト")
print("  基板上の [BOOT] ボタンを押してみてください！")
print("  (押している間 点灯 / 離すと 消灯)")
print("=" * 45)

led.off()
prev_state = button.value()

try:
    while True:
        curr_state = button.value()
        # ボタンの状態変化を検知
        if curr_state != prev_state:
            if curr_state == 0:
                print(">> [BOOT] 押されました！ -> LED 点灯")
                led.on()
            else:
                print("<< [BOOT] 離されました -> LED 消灯")
                led.off()
            prev_state = curr_state
        time.sleep(0.02)  # チャタリング防止
except KeyboardInterrupt:
    led.off()
    print("\nスクリプトを終了しました。")
