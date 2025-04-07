import struct
import utime
import network
import math
from machine import Pin, SPI
from nrf24l01 import NRF24L01

# --- Configuración WiFi y NRF24L01 ---
WIFI_SSID = "Gaho00"
WIFI_PASSWORD = "capitancp"

# --- Pines del SPI y botón ---
SPI_ID = 0
PINS = {
    "sck": 2,      # Pin de reloj SPI
    "mosi": 3,     # Pin de datos maestro-esclavo
    "miso": 4,     # Pin de datos esclavo-maestro
    "csn": 5,      # Pin CSN del NRF24L01
    "ce": 6,       # Pin CE del NRF24L01
    "boton": 10    # Pin para el botón físico
}

# --- Direcciones y canal RF ---
TX_ADDRESS = b"\xe1\xf0\xf0\xf0\xf0"  # Dirección del transmisor
RX_ADDRESS = b"\xd2\xf0\xf0\xf0\xf0"  # Dirección del receptor
CANAL_RF = 46                         # Canal de transmisión (0-125)
DATA_RATE = 2                         # 2 Mbps
RF_POWER = 3                          # Potencia máxima

# --- Clase para manejar la conexión WiFi ---
class WiFiManager:
    def __init__(self, ssid, password):
        self.wlan = network.WLAN(network.STA_IF)
        self.ssid = ssid
        self.password = password

    def conectar(self):
        self.wlan.active(True)
        if not self.wlan.isconnected():
            print("Conectando a WiFi...")
            self.wlan.connect(self.ssid, self.password)
            while not self.wlan.isconnected():
                utime.sleep(1)
        print("WiFi conectado:", self.wlan.ifconfig())

    def obtener_rssi(self):
        return self.wlan.status('rssi') if self.wlan.isconnected() else -100

# --- Clase para manejar el transmisor NRF24L01 ---
class NRFTransmitter:
    def __init__(self, pins):
        spi = SPI(SPI_ID,
                  sck=Pin(pins["sck"]),
                  mosi=Pin(pins["mosi"]),
                  miso=Pin(pins["miso"]))
        csn = Pin(pins["csn"], mode=Pin.OUT, value=1)
        ce = Pin(pins["ce"], mode=Pin.OUT, value=0)

        self.nrf = NRF24L01(spi, csn, ce, payload_size=4)
        self._configurar_radio()

    def _configurar_radio(self):
        self.nrf.set_channel(CANAL_RF)
        reg = 0x00
        if DATA_RATE == 2:
            reg |= (1 << 5)
        elif DATA_RATE == 1:
            reg |= (1 << 3)
        reg |= (RF_POWER & 0x03) << 1
        self.nrf.reg_write(0x06, reg)

        self.nrf.open_tx_pipe(RX_ADDRESS)
        self.nrf.open_rx_pipe(1, TX_ADDRESS)
        self.nrf.stop_listening()
        print(f"NRF24L01 configurado en canal {CANAL_RF}")

    def enviar(self, valor):
        payload = struct.pack("i", valor)  # Empaquetar entero en 4 bytes
        self.nrf.send(payload)

# --- Clase para manejar el botón físico ---
class Boton:
    def __init__(self, pin_num):
        self.pin = Pin(pin_num, Pin.IN, Pin.PULL_UP)

    def esta_presionado(self):
        return self.pin.value() == 0  # Botón presionado si está en bajo

# --- Clase para manejar el LED integrado ---
class IndicadorLED:
    def __init__(self):
        self.led = Pin("LED", Pin.OUT)

    def encender(self):
        self.led.on()

    def apagar(self):
        self.led.off()

# --- Funciones para cálculos estadísticos ---
def calcular_promedio(lista):
    return sum(lista) / len(lista)

def calcular_desviacion_estandar(lista):
    media = calcular_promedio(lista)
    varianza = sum((x - media) ** 2 for x in lista) / len(lista)
    return math.sqrt(varianza)

# --- Función principal ---
def ejecutar_transmisor():
    print("Iniciando transmisor con botón y análisis estadístico...")

    wifi = WiFiManager(WIFI_SSID, WIFI_PASSWORD)
    wifi.conectar()

    nrf = NRFTransmitter(PINS)
    boton = Boton(PINS["boton"])
    led = IndicadorLED()

    while True:
        if boton.esta_presionado():
            led.encender()
            print("🔘 Botón presionado. Midiendo durante 5 segundos...")

            muestras = []

            # Tomar 10 muestras en 5 segundos
            for _ in range(10):
                rssi = wifi.obtener_rssi()
                muestras.append(rssi)
                print("RSSI:", rssi)

                try:
                    nrf.enviar(rssi)  # Enviar cada dato individual
                except Exception as e:
                    print("Error al enviar dato:", e)

                utime.sleep(0.5)  # Espera entre muestras

            # Calcular estadísticas
            promedio = int(calcular_promedio(muestras))
            desviacion = int(calcular_desviacion_estandar(muestras))

            print(f" Promedio: {promedio} dBm | Desviación estándar: {desviacion}")

            # Enviar estadísticas
            try:
                nrf.enviar(promedio)
                utime.sleep_ms(100)
                nrf.enviar(desviacion)
                print("Promedio y desviación enviados.")
            except Exception as e:
                print("Error al enviar estadísticas:", e)

            led.apagar()
            utime.sleep(1)  # Anti-rebote del botón

        utime.sleep_ms(100)  # Espera corta para revisar botón

# Ejecutar el transmisor
ejecutar_transmisor()
