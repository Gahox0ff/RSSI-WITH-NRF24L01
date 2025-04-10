# Importación de librerías necesarias
import struct  # Para empaquetar/desempaquetar datos binarios
import time    # Para funciones de retardo
import math    # Para cálculos matemáticos (desviación estándar)
from machine import Pin, SPI  # Módulos para control de GPIO y comunicación SPI
from nrf24l01 import NRF24L01  # Librería para controlar el transceptor NRF24L01
import network  # Para gestionar conexiones WiFi

# Configuración del botón en el pin GPIO 18 con resistencia pull-up interna
boton = Pin(18, Pin.IN, Pin.PULL_UP)

# Configuración de credenciales WiFi
# 🚨 Sección para personalizar con tus propias credenciales
SSID = "Gaho00"     # Nombre de la red WiFi
PASSWORD = "capitancp"  # Contraseña de la red WiFi

# Inicialización del módulo WiFi en modo estación (cliente)
wifi = network.WLAN(network.STA_IF)
wifi.active(True)  # Activar la interfaz WiFi
wifi.connect(SSID, PASSWORD)  # Iniciar conexión con la red WiFi
print("Conectando a WiFi...")

# Bucle de verificación de conexión WiFi con 20 intentos
for i in range(20):
    if wifi.isconnected():
        print("✅ Conectado a WiFi")
        print("IP:", wifi.ifconfig()[0])  # Muestra la dirección IP asignada
        break
    else:
        print(f"Intento {i+1}/10: esperando conexión...")
        time.sleep(1)  # Espera 1 segundo entre intentos
else:  # Este bloque se ejecuta si el bucle termina normalmente (sin break)
    print("❌ No se pudo conectar a WiFi después de 10 segundos.")

# Definición de pines para la comunicación SPI con el NRF24L01
SPI_ID = 0      # Identificador del bus SPI a utilizar
SCK_PIN = 2     # Pin para la señal de reloj SPI
MOSI_PIN = 3    # Pin Master Out Slave In (datos salientes)
MISO_PIN = 4    # Pin Master In Slave Out (datos entrantes)
CSN_PIN = 5     # Pin Chip Select (selección de chip)
CE_PIN = 6      # Pin Chip Enable (habilitación de chip)

# Parámetros de configuración del NRF24L01
CANAL_RF = 46                # Canal de radiofrecuencia (0-125)
TX_ADDRESS = b"\xe1\xf0\xf0\xf0\xf0"  # Dirección de transmisión (5 bytes)
PAYLOAD_SIZE = 8             # Tamaño del paquete de datos en bytes

def setup_nrf24l01():
    """
    Configura e inicializa el módulo NRF24L01
    """
    # Inicialización del bus SPI con los pines definidos
    spi = SPI(SPI_ID, sck=Pin(SCK_PIN), mosi=Pin(MOSI_PIN), miso=Pin(MISO_PIN))
    csn = Pin(CSN_PIN, mode=Pin.OUT, value=1)  # CSN inicia en alto (inactivo)
    ce = Pin(CE_PIN, mode=Pin.OUT, value=0)    # CE inicia en bajo (modo standby)
    
    # Creación del objeto NRF24L01
    nrf = NRF24L01(spi, csn, ce, payload_size=PAYLOAD_SIZE)
    
    # Configuración del canal RF
    nrf.set_channel(CANAL_RF)
    
    # Configuración de potencia y tasa de bits (registro RF_SETUP - 0x06)
    # 0x26 = 00100110 en binario, donde:
    # - Bit 3-2 (RF_DR_HIGH, RF_DR_LOW): 10 selecciona 1 Mbps
    #   (00=1Mbps, 01=2Mbps, 10=250Kbps)
    # - Bit 1-0 (RF_PWR): 11 selecciona máxima potencia (0dBm)
    #   (00=-18dBm, 01=-12dBm, 10=-6dBm, 11=0dBm)
    # NOTA: Esta es la configuración clave para potencia de transmisión y tasa de bits
    nrf.reg_write(0x06, 0x26)  # Configura potencia 0dBm y tasa de 250 Kbps
    
    # Para cambiar la potencia y tasa, modifica el segundo parámetro:
    # - Para 2Mbps y 0dBm: nrf.reg_write(0x06, 0x0E)  # 00001110
    # - Para 1Mbps y -6dBm: nrf.reg_write(0x06, 0x0A) # 00001010
    # - Para 250Kbps y -18dBm: nrf.reg_write(0x06, 0x20) # 00100000
    
    # Apertura del canal de transmisión con la dirección especificada
    nrf.open_tx_pipe(TX_ADDRESS)
    
    print(f"NRF24L01 configurado en canal {CANAL_RF}")
    return nrf

def medir_rssi():
    """
    Realiza 10 mediciones del nivel de señal WiFi (RSSI) y guarda los resultados
    """
    rssi_values = []  # Lista para almacenar valores de RSSI
    
    # Realiza 10 mediciones consecutivas
    for i in range(10):
        if wifi.isconnected():
            rssi = wifi.status('rssi')  # Obtiene el RSSI actual
        else:
            rssi = -100  # Valor predeterminado si no hay conexión
        print(f"Medición {i+1}: RSSI = {rssi} dBm")
        rssi_values.append(rssi)
        time.sleep(0.1)  # Pequeña pausa entre mediciones
    
    # Cálculo de estadísticas básicas
    avg_rssi = sum(rssi_values) / len(rssi_values)  # Promedio
    # Cálculo de desviación estándar
    std_dev_rssi = math.sqrt(sum([(x - avg_rssi) ** 2 for x in rssi_values]) / len(rssi_values))
    
    print(f"Promedio RSSI: {avg_rssi:.2f} dBm")
    print(f"Desviación estándar: {std_dev_rssi:.2f} dBm")
    
    # Guarda las mediciones en un archivo
    with open("RSSI_Medicion.txt", "w") as log:
        for i, val in enumerate(rssi_values):
            log.write(f"{i},{val}\n")

def transmitir_archivo(nrf, file_path):
    """
    Lee un archivo de mediciones y transmite los datos usando el NRF24L01
    
    Args:
        nrf: Objeto NRF24L01 inicializado
        file_path: Ruta al archivo de mediciones
    """
    try:
        with open(file_path, "r") as file:
            for line in file:
                # Parsea cada línea del archivo (formato: "índice,valor_rssi")
                partes = line.strip().split(",")
                if len(partes) == 2:
                    try:
                        idx = int(partes[0])  # Índice de la medición
                        rssi = int(partes[1])  # Valor RSSI
                        # Empaqueta los datos como dos enteros para transmisión
                        payload = struct.pack("ii", idx, rssi)
                        # Envía el paquete de datos
                        nrf.send(payload)
                        # Solo mostramos el valor RSSI, sin el ID
                        print(f"Enviado RSSI: {rssi} dBm")
                        time.sleep(0.1)  # Pequeña pausa entre transmisiones
                    except ValueError:
                        print("Línea malformada:", line)
        print("Archivo enviado exitosamente.")
    except Exception as e:
        print(f"Error al transmitir archivo: {e}")

def main():
    """
    Función principal del programa
    """
    print("\n--- Transmisor NRF24L01 listo ---")
    try:
        # Inicializa el módulo NRF24L01
        nrf = setup_nrf24l01()
    except Exception as e:
        print(f"Error al configurar NRF24L01: {e}")
        return
    
    # Bucle principal - espera a que se presione el botón
    while True:
        if boton.value() == 0:  # Botón presionado (lógica invertida por pull-up)
            print("Botón presionado, midiendo RSSI...")
            medir_rssi()  # Realiza mediciones de RSSI
            # Transmite el archivo de mediciones vía NRF24L01
            transmitir_archivo(nrf, "RSSI_Medicion.txt")
            time.sleep(2)  # Evita rebotes del botón

# Punto de entrada del programa
if __name__ == "__main__": 
    main()
