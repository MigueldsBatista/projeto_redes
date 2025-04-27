import socket
import struct
import hashlib
import random
import time

class NetworkDevice:
    def __init__(self, server_addr:str, server_port:int, protocol='gbn', max_fragment_size=3, window_size=4):
        """
        Initialize a network device with connection parameters.
        
        Args:
            server_addr: Server address for connection
            server_port: Server port for connection
            protocol: Protocol type ('gbn' or 'sr') for reliable data transfer
            max_fragment_size: Maximum message fragment size (defaults to 3 characters)
            window_size: Size of the sliding window (number of packets in flight)
        """
        # Minimum buffer size for receiving packets (header + max payload)
        self.BUFFER_SIZE = 1024
        
        # Header size is fixed at 11 bytes
        self.HEADER_SIZE = 11
        
        # Connection parameters
        self.connection_params = {
            "protocol": protocol,
            "max_fragment_size": max_fragment_size,
            "window_size": window_size
        }
        
        self.server_addr = server_addr
        self.server_port = server_port
        self.max_fragment_size = max_fragment_size
        self.protocol = protocol
        self.window_size = window_size
        
        # Sliding window parameters
        self.base_seq_num = 0
        self.next_seq_num = 0
        self.timeout = 1.0  # Timeout in seconds
        
        # Channel simulation parameters (default: normal channel)
        self.loss_probability = 0.0
        self.corruption_probability = 0.0
        self.delay_probability = 0.0
        self.delay_time = 0.0
        
        self._socket:socket.socket #DO NOT ASSIGN HERE, IT WILL BE ASSIGNED IN THE CONNECT METHOD

    def calculate_checksum(self, data):
        """Calculate a simple checksum for data integrity verification"""
        # Return the checksum as bytes to match the expected type in create_packet
        checksum_value = sum(data) % 256
        return checksum_value.to_bytes(4, byteorder='big')
        
    def create_packet(self, message_type, payload, sequence_num=0, checksum=None):
        """Create a packet with header and payload"""
        if isinstance(payload, str):
            payload = payload.encode('utf-8')
            
        payload_length = len(payload)
        
        # Calculate the checksum if not provided
        if checksum is None:
            checksum = hashlib.md5(payload).digest()[:4]  # 4-byte checksum
        elif not isinstance(checksum, bytes):
            # Ensure checksum is bytes if it's not already
            try:
                if isinstance(checksum, int):
                    checksum = checksum.to_bytes(4, byteorder='big')
                else:
                    checksum = bytes(checksum)
                    # Pad to 4 bytes if needed
                    if len(checksum) < 4:
                        checksum = checksum + b'\x00' * (4 - len(checksum))
                    # Truncate to 4 bytes if longer
                    checksum = checksum[:4]
            except (TypeError, ValueError):
                print("[ERROR] Invalid checksum type, using MD5 instead")
                checksum = hashlib.md5(payload).digest()[:4]
        
        # Pack header: length (4 bytes) + type (1 byte) + seq (2 bytes) + checksum (4 bytes)
        header = struct.pack('!IBH4s', payload_length, message_type, sequence_num, checksum)
        
        return header + payload
    
    def handle_packet(self, data_type, payload: str):
        """Create and send a packet with the given data type and payload"""
        data_packet = self.create_packet(data_type, payload)
        self._socket.sendall(data_packet)
        
    def parse_packet(self, packet):
        """Parse a received packet into its components"""
        # Check if packet is at least as long as the header
        if len(packet) < self.HEADER_SIZE:
            print(f"[ERROR] Received packet too small: {len(packet)} bytes, expected at least {self.HEADER_SIZE} bytes")
            return None
        
        # Extract header (11 bytes total)
        header = packet[:self.HEADER_SIZE]
        
        payload_length, message_type, sequence_num, checksum = struct.unpack('!IBH4s', header)
        
        # Check if we have enough data for the payload
        if len(packet) < self.HEADER_SIZE + payload_length:
            print(f"[ERROR] Incomplete packet: expected {self.HEADER_SIZE + payload_length} bytes, got {len(packet)} bytes")
            return None
        
        # Extract payload
        payload = packet[self.HEADER_SIZE:self.HEADER_SIZE+payload_length]
        
        # Verify checksum
        calculated_checksum = hashlib.md5(payload).digest()[:4]
        if calculated_checksum != checksum:
            print("[ERROR] Checksum verification failed!")
            return None
            
        return {
            'type': message_type,
            'sequence': sequence_num,
            'payload': payload,
            'length': payload_length
        }

    def set_channel_conditions(self, loss_prob=0.0, corruption_prob=0.0, delay_prob=0.0, delay_time=0.0):
        """Set the channel conditions for simulation"""
        self.loss_probability = max(0.0, min(1.0, loss_prob))
        self.corruption_probability = max(0.0, min(1.0, corruption_prob))
        self.delay_probability = max(0.0, min(1.0, delay_prob))
        self.delay_time = max(0.0, delay_time)
        
        # Determine simulation mode based on probabilities
        if self.loss_probability == 1.0:
            mode = "Packet Loss"
        elif self.corruption_probability == 1.0:
            mode = "Packet Corruption" 
        elif self.delay_probability == 1.0:
            mode = "Network Delay"
        elif self.loss_probability == 0.0 and self.corruption_probability == 0.0 and self.delay_probability == 0.0:
            mode = "Normal"
        else:
            mode = "Custom"
            
        print(f"[CONFIG] Channel set to {mode} mode: loss={self.loss_probability}, " +
              f"corruption={self.corruption_probability}, delay={self.delay_probability}, " +
              f"delay_time={self.delay_time}s")

    def simulate_channel(self, data, packet_index=0):

        # Deterministic simulation based on probabilities
        # If probability is 1.0, always apply the effect
        # If probability is 0.0, never apply the effect
        # Otherwise, use random chance
        
        # Simulate packet loss (always lose if probability is 1.0)
        if self.loss_probability == 1.0 or (self.loss_probability > 0.0 and random.random() < self.loss_probability):
            print(f"[CHANNEL] Packet lost in transmission (seq={packet_index})!")
            return None

        # Simulate packet corruption (always corrupt if probability is 1.0)
        if self.corruption_probability == 1.0 or (self.corruption_probability > 0.0 and random.random() < self.corruption_probability):
            print(f"[CHANNEL] Packet corrupted during transmission (seq={packet_index})!")
            data = bytearray(data)
            # Corrupt a byte in a deterministic way if possible
            index = packet_index % len(data) if len(data) > 0 else 0
            data[index] = (data[index] + 1) % 256 # this will corrupt the byte at index
            data = bytes(data) # %256 to ensure it stays within byte range

        # Simulate network delay (always delay if probability is 1.0)
        if self.delay_probability == 1.0 or (self.delay_probability > 0.0 and random.random() < self.delay_probability):
            delay = self.delay_time
            print(f"[CHANNEL] Packet delayed by {delay:.2f} seconds (seq={packet_index})")
            time.sleep(delay)

        return data