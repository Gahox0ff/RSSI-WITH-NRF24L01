import struct
import utime
from machine import Pin, SPI, I2C
from nrf24l01 import NRF24L01
import ssd1306
import math

# --- Pines SPI para el módulo NRF24L01 (mismos que en el transmisor) ---
SPI_ID = 0
PINES = {
    "sck": 2,     # Señal de reloj SPI
    "mosi": 3,    # Datos del maestro al esclavo
    "miso": 4,    # Datos del esclavo al maestro
    "csn": 5,     # Chip Select (activo en bajo)
    "ce": 6       # Habilitador del módulo NRF24L01
}

# --- Pines para la pantalla OLED I2C ---
I2C_SDA = 14     # Pin de datos I2C
I2C_SCL = 15     # Pin de reloj I2C
ANCHO = 128      # Ancho de la pantalla OLED
ALTO = 64        # Alto de la pantalla OLED

# LED incorporado del Raspberry Pi Pico W
led = Pin("LED", Pin.OUT)

# --- Configuración de direcciones y canal del módulo NRF24L01 ---
CANAL_RF = 46                             # Canal de comunicación (entre 0 y 125)
DIRECCION_TX = b"\xe1\xf0\xf0\xf0\xf0"    # Dirección del transmisor
DIRECCION_RX = b"\xd2\xf0\xf0\xf0\xf0"    # Dirección del receptor

# --- Inicialización de la pantalla OLED ---
i2c = I2C(1, scl=Pin(I2C_SCL), sda=Pin(I2C_SDA))  # Bus I2C número 1
oled = ssd1306.SSD1306_I2C(ANCHO, ALTO, i2c)      # Crear objeto OLED

# --- Función para configurar el módulo NRF24L01 ---
def configurar_nrf():
    # Inicializar la comunicación SPI con los pines definidos
    spi = SPI(
        SPI_ID,
        sck=Pin(PINES["sck"]),
        mosi=Pin(PINES["mosi"]),
        miso=Pin(PINES["miso"])
    )
    csn = Pin(PINES["csn"], mode=Pin.OUT, value=1)
    ce = Pin(PINES["ce"], mode=Pin.OUT, value=0)

    # Crear el objeto NRF24L01 con tamaño de mensaje de 4 bytes (entero)
    nrf = NRF24L01(spi, csn, ce, payload_size=4)
    nrf.set_channel(CANAL_RF)                      # Establecer el canal
    nrf.reg_write(0x06, 0x0E)                      # 2Mbps, potencia máxima

    # Abrir la tubería de recepción con la dirección del transmisor
    nrf.open_rx_pipe(1, DIRECCION_TX)
    nrf.open_tx_pipe(DIRECCION_RX)                # (opcional si se necesita enviar respuesta)
    nrf.start_listening()                         # Iniciar en modo escucha

    print(f"NRF24L01 configurado en canal {CANAL_RF}")
    return nrf

# --- Mostrar los resultados en la pantalla OLED ---
def mostrar_en_oled(promedio, desviacion):
    oled.fill(0)  # Limpiar la pantalla
    oled.text("Promedio RSSI:", 0, 10)
    oled.text(f"{promedio:.1f} dBm", 0, 25)
    oled.text("Desv. Estándar:", 0, 40)
    oled.text(f"{desviacion:.1f} dB", 0, 55)
    oled.show()

# --- Calcular promedio y desviación estándar ---
def calcular_estadisticas(lista):
    n = len(lista)
    if n == 0:
        return 0, 0
    promedio = sum(lista) / n
    varianza = sum((x - promedio) ** 2 for x in lista) / n
    desviacion = math.sqrt(varianza)
    return promedio, desviacion

# --- Código principal ---
print("--- Receptor NRF24L01 iniciado ---")
nrf = configurar_nrf()

while True:
    muestras = []                              # Lista para almacenar valores RSSI
    inicio = utime.ticks_ms()                  # Guardar el tiempo de inicio

    # Recolectar datos durante 5 segundos
    while utime.ticks_diff(utime.ticks_ms(), inicio) < 5000:
        if nrf.any():                          # Si hay datos disponibles
            try:
                datos = nrf.recv()             # Recibir los datos
                if len(datos) == 4:
                    rssi, = struct.unpack("i", datos)  # Convertir bytes a entero
                    muestras.append(rssi)             # Agregar a la lista
                    print(f"RSSI recibido: {rssi} dBm")
                    led.toggle()                      # Parpadeo del LED
            except Exception as error:
                print("Error al recibir:", error)
        utime.sleep_ms(100)                   # Pausa para evitar saturar el SPI

    # Calcular y mostrar estadísticas si se recibieron datos
    if muestras:
        promedio, desviacion = calcular_estadisticas(muestras)
        print(f"\nPromedio: {promedio:.1f} dBm | Desv.Estd: {desviacion:.1f} dB\n")
        mostrar_en_oled(promedio, desviacion)
    else:
        print("No se recibieron datos.")
