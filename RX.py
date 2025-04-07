import struct
import utime
from machine import Pin, SPI, I2C
from nrf24l01 import NRF24L01
import ssd1306
import math

# --- Pines definidos como diccionario (igual que en TX) ---
SPI_ID = 0
PINS = {
    "sck": 2,
    "mosi": 3,
    "miso": 4,
    "csn": 5,
    "ce": 6,
}

# Pines para OLED I2C
I2C_SDA = 14
I2C_SCL = 15
WIDTH = 128
HEIGHT = 64

# LED interno
led = Pin("LED", Pin.OUT)

# --- Configuración RF ---
CANAL_RF = 46
TX_ADDRESS = b"\xe1\xf0\xf0\xf0\xf0"
RX_ADDRESS = b"\xd2\xf0\xf0\xf0\xf0"

# --- Inicializar OLED ---
i2c = I2C(1, scl=Pin(I2C_SCL), sda=Pin(I2C_SDA))
oled = ssd1306.SSD1306_I2C(WIDTH, HEIGHT, i2c)

def setup_nrf():
    spi = SPI(
        SPI_ID,
        sck=Pin(PINS["sck"]),
        mosi=Pin(PINS["mosi"]),
        miso=Pin(PINS["miso"])
    )
    csn = Pin(PINS["csn"], mode=Pin.OUT, value=1)
    ce = Pin(PINS["ce"], mode=Pin.OUT, value=0)

    nrf = NRF24L01(spi, csn, ce, payload_size=4)
    nrf.set_channel(CANAL_RF)
    nrf.reg_write(0x06, 0x0E)  # Velocidad 2Mbps, potencia máxima

    nrf.open_rx_pipe(1, TX_ADDRESS)
    nrf.open_tx_pipe(RX_ADDRESS)
    nrf.start_listening()
    
    print(f"NRF24L01 RX configurado en canal {CANAL_RF}")
    return nrf

def mostrar_oled(prom, desv):
    oled.fill(0)
    oled.text("Promedio RSSI:", 0, 10)
    oled.text(f"{prom:.1f} dBm", 0, 25)
    oled.text("Desv.Std:", 0, 40)
    oled.text(f"{desv:.1f} dB", 0, 55)
    oled.show()

def calcular_estadisticas(valores):
    n = len(valores)
    if n == 0:
        return 0, 0
    prom = sum(valores) / n
    varianza = sum((x - prom) ** 2 for x in valores) / n
    desv = math.sqrt(varianza)
    return prom, desv

# --- Código principal ---
print("--- Receptor NRF24L01 ---")
nrf = setup_nrf()

while True:
    muestras = []
    inicio = utime.ticks_ms()

    while utime.ticks_diff(utime.ticks_ms(), inicio) < 5000:
        if nrf.any():
            try:
                buf = nrf.recv()
                if len(buf) == 4:
                    rssi, = struct.unpack("i", buf)
                    muestras.append(rssi)
                    print(f"RSSI recibido: {rssi} dBm")
                    led.toggle()
            except Exception as e:
                print("Error:", e)
        utime.sleep_ms(100)

    if muestras:
        prom, desv = calcular_estadisticas(muestras)
        print(f"\nPromedio: {prom:.1f} dBm | Desv.Std: {desv:.1f} dB\n")
        mostrar_oled(prom, desv)
    else:
        print("No se recibieron datos.")
