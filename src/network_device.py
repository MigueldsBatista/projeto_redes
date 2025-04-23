import struct
import hashlib

class NetworkDevice:
    def __init__(self, server_addr, server_port, operation_mode='step-by-step', max_size=1024):
        """
        Initialize a network device with connection parameters
        
        The three-way handshake process:
        1. Client sends SYN with parameters (operation_mode, max_size)
        2. Server responds with SYN-ACK, containing accepted parameters and session_id
        3. Client confirms with ACK, completing the handshake
        
        After the handshake is complete, devices can exchange data messages.
        """
        # Connection parameters
        self.connection_params = {
            "operation_mode": operation_mode,
            "max_size": max_size
        }
        
        self.server_addr = server_addr
        self.server_port = server_port
        self.max_size = max_size
        self.operation_mode = operation_mode
     
    def create_packet(self, message_type, payload, sequence_num=0):
        if isinstance(payload, str):
            payload = payload.encode('utf-8')
            
        payload_length = len(payload)
        checksum = hashlib.md5(payload).digest()[:4]  # 4-byte checksum
        
        #!IBH4s # é o formato do struct.pack que quer dizer que o primeiro byte é um inteiro,
        # o segundo byte é um inteiro, o terceiro byte é um inteiro e o quarto byte é uma string de 4 bytes

        # Pack header: length (4 bytes) + type (1 byte) + seq (2 bytes) + checksum (4 bytes)
        header = struct.pack('!IBH4s', payload_length, message_type, sequence_num, checksum)
        
        # Complete packet = header + payload
        return header + payload
        
    def parse_packet(self, packet):
        # Extract header (11 bytes total)
        header = packet[:11]
        
        payload_length, message_type, sequence_num, checksum = struct.unpack('!IBH4s', header)
        
        # Extract payload
        payload = packet[11:11+payload_length]
        
        # Verify checksum
        calculated_checksum = hashlib.md5(payload).digest()[:4]
        if calculated_checksum != checksum:
            print("Checksum error!")
            return None
            
        return {
            'type': message_type,
            'sequence': sequence_num,
            'payload': payload,
            'length': payload_length
        }