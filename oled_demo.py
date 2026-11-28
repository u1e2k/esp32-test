import gc
import time
import esp32
from machine import Pin, SoftI2C
import ssd1306

# ESP32-C3 0.42" OLED (72x40) ピン設定
I2C_SDA = 5
I2C_SCL = 6
OLED_ADDR = 0x3C

# 物理パネルは 72x40 だが、コントローラ RAM は 128x64
WIDTH = 128
HEIGHT = 64
X_OFF = 28
Y_OFF = 24
VIEW_W = 72
VIEW_H = 40

i2c = SoftI2C(sda=Pin(I2C_SDA), scl=Pin(I2C_SCL), freq=400000)
devices = i2c.scan()
print("I2C devices:", [hex(d) for d in devices])

if OLED_ADDR not in devices:
    raise RuntimeError(f"OLED (0x{OLED_ADDR:02x}) not found!")

oled = ssd1306.SSD1306_I2C(WIDTH, HEIGHT, i2c, addr=OLED_ADDR)

print("Displaying demo on 0.42\" OLED (press Ctrl+C to stop)...")

# 10秒間、チップ温度とアニメーションを表示
for tick in range(20):
    temp_c = esp32.mcu_temperature()
    free_kb = gc.mem_free() // 1024

    oled.fill(0)
    # 72x40 領域の枠線
    oled.rect(X_OFF, Y_OFF, VIEW_W, VIEW_H, 1)
    # テキスト（X_OFF=28, Y=26..52 の重なり領域に配置）
    oled.text("ESP32-C3", X_OFF + 4, Y_OFF + 4, 1)
    oled.text(f"T:{temp_c:2d}C", X_OFF + 4, Y_OFF + 15, 1)
    oled.text(f"M:{free_kb:3d}K", X_OFF + 4, Y_OFF + 26, 1)

    # 右下に動くミニバー
    bar_x = X_OFF + 54 + (tick % 4) * 3
    oled.fill_rect(bar_x, Y_OFF + 16, 4, 8, 1)
    oled.show()
    time.sleep(0.5)

print("OLED demo finished!")
