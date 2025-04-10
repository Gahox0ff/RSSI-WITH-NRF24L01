# Importación de librerías necesarias
import struct      # Para empaquetar/desempaquetar datos binarios
import utime       # Funciones de temporización para MicroPython
from machine import Pin, SPI, I2C  # Módulos para control de GPIO, SPI e I2C
from nrf24l01 import NRF24L01      # Librería para controlar el transceptor NRF24L01
import ssd1306     # Controlador para pantallas OLED basadas en SSD1306

# --- Configuración de pines SPI para NRF24L01 ---
SPI_ID = 0      # Identificador del bus SPI
SCK_PIN = 2     # Pin de reloj SPI
MOSI_PIN = 3    # Pin Master Out Slave In (datos salientes)
MISO_PIN = 4    # Pin Master In Slave Out (datos entrantes)
CSN_PIN = 5     # Pin Chip Select (selección de chip)
CE_PIN = 6      # Pin Chip Enable (habilitación de chip)

# --- Configuración de pines I2C para pantalla OLED ---
I2C_SDA = 14    # Pin de datos I2C
I2C_SCL = 15    # Pin de reloj I2C
WIDTH = 128     # Ancho de la pantalla OLED en píxeles
HEIGHT = 64     # Alto de la pantalla OLED en píxeles

# LED integrado en la placa para indicación visual
led = Pin("LED", Pin.OUT)

# --- Configuración de parámetros RF ---
CANAL_RF = 46                    # Canal de radiofrecuencia (0-125)
TX_ADDRESS = b"\xe1\xf0\xf0\xf0\xf0"  # Dirección del transmisor (5 bytes)
RX_ADDRESS = b"\xd2\xf0\xf0\xf0\xf0"  # Dirección receptora para respuestas
DATA_RATE = 1  # Tasa de datos: 0=1Mbps, 1=2Mbps, 2=250Kbps
RF_POWER = 3   # Potencia RF: 0=-18dBm, 1=-12dBm, 2=-6dBm, 3=0dBm (máxima)

# --- Inicialización de la pantalla OLED ---
i2c = I2C(1, scl=Pin(I2C_SCL), sda=Pin(I2C_SDA))
oled = ssd1306.SSD1306_I2C(WIDTH, HEIGHT, i2c)

def setup_nrf24l01():
    """
    Configura e inicializa el módulo NRF24L01 en modo receptor
    """
    # Inicialización del bus SPI con los pines definidos
    spi = SPI(SPI_ID, sck=Pin(SCK_PIN), mosi=Pin(MOSI_PIN), miso=Pin(MISO_PIN))
    csn = Pin(CSN_PIN, mode=Pin.OUT, value=1)  # CSN inicia en alto (inactivo)
    ce = Pin(CE_PIN, mode=Pin.OUT, value=0)    # CE inicia en bajo (standby)
    
    # Creación del objeto NRF24L01 con tamaño de paquete de 8 bytes
    nrf = NRF24L01(spi, csn, ce, payload_size=8)
    
    # Configuración del canal RF
    nrf.set_channel(CANAL_RF)
    
    # Configuración de potencia y tasa de bits (registro RF_SETUP - 0x06)
    # 0x26 = 00100110 en binario, donde:
    # - Bit 3-2 (RF_DR_HIGH, RF_DR_LOW): 10 selecciona 250 Kbps
    #   (00=1Mbps, 01=2Mbps, 10=250Kbps)
    # - Bit 1-0 (RF_PWR): 10 selecciona -6dBm (no es máxima potencia)
    #   (00=-18dBm, 01=-12dBm, 10=-6dBm, 11=0dBm)
    # NOTA: Esta configuración debe coincidir con el transmisor
    nrf.reg_write(0x06, 0x26)  # Configura 250kbps, potencia -6dBm
    
    # Para modificar la configuración de potencia y tasa:
    # - Para 1Mbps y potencia máxima (0dBm): nrf.reg_write(0x06, 0x07)  # 00000111
    # - Para 2Mbps y potencia media (-12dBm): nrf.reg_write(0x06, 0x09) # 00001001
    
    # Configuración de direcciones para comunicación bidireccional
    nrf.open_tx_pipe(RX_ADDRESS)    # Para enviar respuesta si es necesario
    nrf.open_rx_pipe(1, TX_ADDRESS) # Canal 1 escucha al transmisor
    
    print(f"NRF24L01 receptor en canal {CANAL_RF}")
    return nrf

def mostrar_en_oled(rssi):
    """
    Muestra el valor RSSI recibido en la pantalla OLED
    
    Args:
        rssi: Valor RSSI en dBm
    """
    oled.fill(0)  # Limpia la pantalla
    oled.text("Mensaje recibido:", 0, 0)
    oled.text(f"RSSI: {rssi} dBm", 0, 35)
    oled.show()  # Actualiza la pantalla

def receiver_loop(nrf):
    """
    Bucle principal de recepción
    
    Args:
        nrf: Objeto NRF24L01 inicializado
    """
    # Inicia el modo de escucha
    nrf.start_listening()
    print("\nEscuchando transmisiones...")
    
    while True:
        if nrf.any():  # Verifica si hay datos disponibles
            led.on()  # Enciende LED para indicar recepción
            
            # Procesa todos los paquetes en la cola
            while nrf.any():
                buf = nrf.recv()  # Recibe el paquete
                if len(buf) == 8:  # Verifica tamaño correcto
                    try:
                        # Desempaqueta los dos enteros: ID y RSSI
                        msg_id, rssi = struct.unpack("ii", buf)
                        # Solo muestra el RSSI, sin el ID
                        print(f"Recibido RSSI: {rssi} dBm")
                        mostrar_en_oled(rssi)
                    except Exception as e:
                        print("Error de decodificación:", e)
                utime.sleep_ms(50)  # Pequeña pausa entre paquetes
                
            # Apaga el LED al terminar de procesar paquetes
            led.off()
            
        utime.sleep_ms(100)  # Pequeña pausa entre comprobaciones

def main():
    """
    Función principal del programa
    """
    print("\n--- Iniciando receptor NRF24L01 con OLED ---")
    try:
        # Inicializa el módulo NRF24L01
        nrf = setup_nrf24l01()
        # Inicia el bucle de recepción
        receiver_loop(nrf)
    except Exception as e:
        print(f"Error al configurar NRF24L01: {e}")

# Punto de entrada del programa
if __name__ == "__main__": 
    main()
