import serial
import struct
import time
import numpy as np

# Agregar inicialización (por ejemplo chequear valores por default)

class SpectrometerDriver:
    HEADER_VAL = 0x7346
    END_BUFFER_VAL = 0x7347
    
    # Comandos
    CMD_SET_INT_TIME        = 0xF001
    CMD_RESET               = 0xF002
    CMD_DATA_SENDING        = 0xF003
    CMD_SET_ACCUM           = 0xF004
    CMD_SET_CONTINUOUS      = 0xF005
    CMD_SET_FIXED_LENGTH    = 0xF006
    
    CCD_PIXELS = 3694

    def __init__(self, port="COM7", baud=460800, timeout=2):
        self.int_time_us = 100
        self.n_accum = 50
        try:
            self.ser = serial.Serial(port, baud, timeout=timeout)
            self.ser.flushInput()
            print(f"Conectado a {port} @ {baud}")
        except Exception as e:
            print(f"Error conectando al puerto: {e}")
            raise e

    def close(self):
        if self.ser.is_open:
            self.ser.close()
            print("Conexión cerrada.")

    def _calculate_checksum(self, data_bytes):
        if len(data_bytes) % 2 != 0: return 0
        
        num_words = len(data_bytes) // 2
        words = struct.unpack(f'<{num_words}H', data_bytes)
        
        cs = 0x0000
        for w in words:
            cs ^= w
        return cs

    def _send_command(self, cmd_id, payload_val=0xFFFFFFFF):
        # Estructura (Little Endian <):
        # H: Header (2 bytes)
        # H: Command (2 bytes)
        # I: Payload (4 bytes)
        # H: Checksum (2 bytes)
                
        try:
            packet_no_cs = struct.pack('<HHI', 
                                       self.HEADER_VAL, 
                                       cmd_id, 
                                       payload_val)
            
            cs = self._calculate_checksum(packet_no_cs)
            
            final_packet = packet_no_cs + struct.pack('<H', cs)
            
            # Para debug
            # print(f"TX: {final_packet.hex().upper()}")
            
            self.ser.write(final_packet)
            
        except struct.error as e:
            print(f"Error empaquetando datos: {e}")
            print(f"Valores: CMD={cmd_id:X}, PAYLOAD={payload_val:X}")

    # --- API PÚBLICA ---

    def reset_device(self):
        print("Enviando RESET...")
        self._send_command(self.CMD_RESET)

    def set_integration_time(self, time_us):
        print(f"Set Tiempo Integración: {time_us} us")
        self._send_command(self.CMD_SET_INT_TIME, time_us)
        self.int_time_us = time_us                                  # Validar

    def set_accumulations(self, n_accum):
        print(f"Set Acumulaciones: {n_accum}")
        self._send_command(self.CMD_SET_ACCUM, n_accum)
        self.n_accum = n_accum                                      # Validar

    def set_continuous_mode(self):
        self._send_command(self.CMD_SET_CONTINUOUS)

    def set_fixed_length_mode(self):
        self._send_command(self.CMD_SET_FIXED_LENGTH)

    def read_frame(self):
        # Sincronizar Header
        header_bytes = struct.pack('<H', self.HEADER_VAL)
        window = bytearray()
        
        while True:
            b = self.ser.read(1)
            if not b: continue # Timeout o espera
            window += b
            if len(window) > 2: window = window[-2:]
            
            if window == header_bytes:
                break
        
        # Leer resto: Cmd(2) + Data(Pixel*2) + Checksum(2) + Footer(2) 
        payload_size = self.CCD_PIXELS * 2
        rest_len = 2 + payload_size + 2 + 2 
        data = self.ser.read(rest_len)
        
        if len(data) != rest_len:
            print("Error: Frame incompleto")
            return None

        # Estructura recibida: [CMD, Px1, Px2..., Checksum, Footer]
        full_arr = np.frombuffer(data, dtype=np.dtype('<u2'))
        
        if full_arr[0] !=  self.CMD_DATA_SENDING:
            print(f"Error: Comando inesperado {full_arr[0]:X}")
            return None
        if full_arr[-1] != self.END_BUFFER_VAL:
            print(f"Error: Footer inválido {full_arr[-1]:X}")
            return None
        
        pixel_data = full_arr[1 : 1 + self.CCD_PIXELS]
        
        return pixel_data