import time
from machine import Pin

try:
    import neopixel
    HAS_NEOPIXEL = True
except ImportError:
    HAS_NEOPIXEL = False


def blink_gpio(pin_num: int, count: int = 5, interval: float = 0.25) -> None:
    print(f"Testing standard LED on GPIO {pin_num}...")
    led = Pin(pin_num, Pin.OUT)
    for i in range(count):
        led.value(1)
        time.sleep(interval)
        led.value(0)
        time.sleep(interval)
        print(f"  GPIO {pin_num} [{i + 1}/{count}]")
    led.off()


def test_neopixel(pin_num: int = 8) -> None:
    if not HAS_NEOPIXEL:
        print("neopixel module not available.")
        return
    print(f"Testing NeoPixel (RGB LED) on GPIO {pin_num}...")
    np = neopixel.NeoPixel(Pin(pin_num, Pin.OUT), 1)
    colors = [
        ("Red", (32, 0, 0)),
        ("Green", (0, 32, 0)),
        ("Blue", (0, 0, 32)),
        ("Off", (0, 0, 0)),
    ]
    for name, color in colors:
        print(f"  NeoPixel -> {name}")
        np[0] = color
        np.write()
        time.sleep(0.4)


print("=== ESP32-C3 LED Blink Test ===")
blink_gpio(8, count=5, interval=0.2)
test_neopixel(8)
blink_gpio(2, count=5, interval=0.2)
print("=== Test Completed ===")
