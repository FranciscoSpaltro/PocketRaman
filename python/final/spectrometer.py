import serial
import struct
import numpy as np

class SpectrometerDriver:
    HEADER_VAL = 0x7346
    END_BUFFER_VAL = 0x7347
    
    CMD_SET_INT_TIME        = 0xF001
    CMD_RESET               = 0xF002
    CMD_DATA_SENDING        = 0xF003
    CMD_SET_ACCUM           = 0xF004
    CMD_SET_SKIP_COUNTER    = 0xF005
    CMD_ACK                 = 0xFF46
    CCD_PIXELS = 3694

    def __init__(self, port="COM7", baud=921600, timeout=2):
        self.int_time_us = 100
        self.n_accum = 50
        self.skip_count = 0
        self.ser = None
        
        try:
            self.ser = serial.Serial(port, baud, timeout=timeout)
            self.ser.flushInput()
            print(f"Connected to {port} @ {baud}")
        except Exception as e:
            print(f"Error connecting to port: {e}")
            raise e

    def close(self):
        if self.ser and self.ser.is_open:
            self.ser.close()
            print("Connection closed.")

    def _calculate_checksum(self, data_bytes):
        if len(data_bytes) % 2 != 0: return 0
        num_words = len(data_bytes) // 2
        words = struct.unpack(f'<{num_words}H', data_bytes)
        cs = 0x0000
        for w in words:
            cs ^= w
        return cs

    def _send_command(self, cmd_id, payload_val=0xFFFFFFFF):
        try:
            packet_no_cs = struct.pack('<HHI', self.HEADER_VAL, cmd_id, payload_val)
            cs = self._calculate_checksum(packet_no_cs)
            final_packet = packet_no_cs + struct.pack('<H', cs)
            self.ser.write(final_packet)
            print(f"TX: {final_packet.hex().upper()}")
        except struct.error as e:
            print(f"Error packaging data: {e}")

    def reset_device(self):
        print("Sending RESET...")
        self._send_command(self.CMD_RESET)

    def set_integration_time(self, time_us):
        print(f"Set Integration Time: {time_us} us")
        self._send_command(self.CMD_SET_INT_TIME, time_us)
        self.int_time_us = time_us

    def set_accumulations(self, n_accum):
        print(f"Set Accumulations: {n_accum}")
        self._send_command(self.CMD_SET_ACCUM, n_accum)
        self.n_accum = n_accum

    def set_skip_counter(self, skip_count):
        print(f"Set skip counter: {skip_count}")
        self._send_command(self.CMD_SET_SKIP_COUNTER, skip_count)
        self.skip_count = skip_count

    def read_frame(self):
        if not self.ser or not self.ser.is_open:
            return None

        header_bytes = struct.pack('<H', self.HEADER_VAL)
        window = bytearray()
        
        # 1. Sincronizar Header (0x7346)
        while True:
            b = self.ser.read(1)
            if not b: return None # Timeout
            window += b
            if len(window) > 2: window = window[-2:]
            if window == header_bytes:
                break
        
        # 2. Leer el comando (2 bytes fijos)
        cmd_bytes = self.ser.read(2)
        if len(cmd_bytes) != 2:
            return None
        
        cmd_val = struct.unpack('<H', cmd_bytes)[0]

        # --- CASO A: CONFIRMACIÓN DE COMANDO (ACK = 0xFF46) ---
        if cmd_val == self.CMD_ACK: 
            # El ACK mide 12 bytes fijos. Ya fueron leidos Header + Cmd (4 bytes)
            # Quedan por leer exactamente 8 bytes en el bus serial.
            ack_rest = self.ser.read(8)
            if len(ack_rest) != 8:
                return None
            
            ack_arr = np.frombuffer(ack_rest, dtype=np.dtype('<u2'))
            
            if ack_arr[-1] == self.END_BUFFER_VAL: # 0x7347
                print("--> ACK RECIBIDO EN PC: Parámetros aplicados con éxito en el microcontrolador.")
            else:
                print(f"--> ACK Recibido pero corrupto: Footer incorrecto (0x{ack_arr[-1]:04X})")
                
            return None # Para no intentar graficar este paquete

        # --- CASO B: DATOS DEL CCD (0xF003) ---
        elif cmd_val == self.CMD_DATA_SENDING:
            # Quedan por leer: Pixeles (CCD_PIXELS * 2 bytes) + Checksum (2 bytes) + Footer (2 bytes)
            payload_size = self.CCD_PIXELS * 2
            rest_len = payload_size + 2 + 2 
            data = self.ser.read(rest_len)
            
            if len(data) != rest_len:
                print(f"Error: Datos CCD incompletos. Se esperaban {rest_len} bytes, llegaron {len(data)}.")
                return None

            # Conversion a enteros de 16 bits sin signo
            full_arr = np.frombuffer(data, dtype=np.dtype('<u2'))
            
            # El Footer (0x7347) tiene que estar obligatoriamente en la última posición del array
            if full_arr[-1] != self.END_BUFFER_VAL:
                print(f"Error: Fin de buffer CCD inválido (Se leyó: 0x{full_arr[-1]:04X}, esperado: 0x{self.END_BUFFER_VAL:04X})")
                return None

            pixels_clean = full_arr[:self.CCD_PIXELS]
            
            # Log para verificar el nivel de señal
            print(f"Espectro capturado OK. Máximo valor del ADC: {np.max(pixels_clean)} cuentas.")
            return pixels_clean
        
        # --- CASO C: COMANDO EXTRAÑO / RUIDO ---
        else:
            # Si entra basura, se lee un byte para desalojar el bus y no trabar el sincronismo
            self.ser.read(self.ser.in_waiting or 1)
            return None

##### Mock class for testing without hardware
from fake_spectra import generate_fake_raman_raw
class SpectrometerDriverMock:
    def __init__(self, port="COM7", baud=921600, timeout=2):
        self.int_time_us = 100
        self.n_accum = 50
        self.skip_count = 0
        self.ser = None
        
        try:
            print(f"Mock connection to {port} @ {baud}")
        except Exception as e:
            print(f"Error connecting to port: {e}")
            raise e

    def close(self):
        print("Connection closed.")

    def _send_command(self, cmd_id, payload_val=0xFFFFFFFF):
        try:
            print(f"Command sent")
        except struct.error as e:
            print(f"Error packaging data: {e}")

    def reset_device(self):
        print("Sending RESET...")


    def set_integration_time(self, time_us):
        print(f"Set Integration Time: {time_us} us")
        self.int_time_us = time_us

    def set_accumulations(self, n_accum):
        print(f"Set Accumulations: {n_accum}")
        self.n_accum = n_accum

    def set_skip_counter(self, skip_count):
        print(f"Set skip counter: {skip_count}")
        self.skip_count = skip_count

    def read_frame(self):
        pixels_clean = generate_fake_raman_raw(n_pixels=3694, peaks=None, baseline_offset=800, baseline_slope=0.08, baseline_curve=300, noise_std=20, adc_max=4095, seed=None)[1]
        return pixels_clean
        
