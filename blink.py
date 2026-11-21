import time
from machine import Pin

# ESP32 内蔵LED (多くの場合 GPIO 2)
led = Pin(2, Pin.OUT)

print("Starting LED blink on GPIO 2...")
for i in range(10):
    led.value(not led.value())
    status = "ON" if led.value() else "OFF"
    print(f"[{i+1}/10] LED is {status}")
    time.sleep(0.5)

# テスト後は消灯
led.off()
print("Blink test completed!")
