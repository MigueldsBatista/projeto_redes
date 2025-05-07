import socket
import struct
import hashlib
import random
import time
import struct   

# Define message types
DISCONNECT_TYPE = 2  # Example value for disconnect type
NACK_TYPE = 3  # Example value for NACK type
ACK_TYPE = 1  # Example value for ACK type
DATA_TYPE = 0  # Example value for data type

class NetworkDevice:
    def __init__(self, server_addr:str, server_port:int, protocol='gbn', max_fragment_size=3, window_size=4):

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
        """Calculate a checksum for data integrity verification using MD5"""
        # Use MD5 for a more robust checksum
        return hashlib.md5(data).digest()[:4]  # 4-byte checksum
        
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


    def simulate_channel(self, data, packet_index=0):
        """
        Simulate channel conditions (loss, corruption, delay) based on probabilities.
        """
        # Simulate packet loss
        if self.loss_probability == 1.0 or (self.loss_probability > 0.0 and random.random() < self.loss_probability):
            print(f"[CHANNEL] Packet lost in transmission (seq={packet_index})!")
            return None

        # Simulate packet corruption
        if self.corruption_probability == 1.0 or (self.corruption_probability > 0.0 and random.random() < self.corruption_probability):
            print(f"[CHANNEL] Packet corrupted during transmission (seq={packet_index})!")
            data = bytearray(data)
            index = random.randint(0, len(data) - 1) if len(data) > 0 else 0
            data[index] = (data[index] + 1) % 256  # Corrupt a byte
            return bytes(data)

        # Simulate network delay
        if self.delay_probability == 1.0 or (self.delay_probability > 0.0 and random.random() < self.delay_probability):
            delay = self.delay_time
            print(f"[CHANNEL] Packet delayed by {delay:.2f} seconds (seq={packet_index})")
            time.sleep(delay)

        return data

    def handle_client_messages(self, client_socket: socket.socket, client_address: str):
        """Continuously receive and process messages from a connected client."""
        while client_address in self.client_sessions:
            try:
                # Receive header
                header = client_socket.recv(self.HEADER_SIZE)
                if not header or len(header) < self.HEADER_SIZE:
                    print(f"[ERROR] Incomplete or missing header from {client_address}")
                    break

                # Parse header
                try:
                    payload_length, message_type, sequence_num, checksum = struct.unpack('!IBH4s', header)
                except struct.error as e:
                    print(f"[ERROR] Failed to unpack header from {client_address}: {e}")
                    break

                # Receive payload
                payload = client_socket.recv(payload_length)
                if len(payload) < payload_length:
                    print(f"[ERROR] Incomplete payload received from {client_address}")
                    break

                # Simulate channel conditions
                processed_payload = self.simulate_channel(payload, sequence_num)
                if processed_payload is None:
                    print(f"[CHANNEL] Packet from {client_address} lost in simulated channel.")
                    if hasattr(self, 'simulate_loss_and_nack'):
                        self.simulate_loss_and_nack(client_socket, sequence_num)
                    continue

                # Verify checksum
                calculated_checksum = hashlib.md5(processed_payload).digest()[:4]
                if calculated_checksum != checksum:
                    print(f"[ERROR] Checksum mismatch for packet {sequence_num} from {client_address}")
                    if hasattr(self, 'simulate_corruption_and_nack'):
                        self.simulate_corruption_and_nack(client_socket, sequence_num, payload)
                    continue

                # Process message based on type
                if message_type == DATA_TYPE:
                    try:
                        decoded_message = processed_payload.decode('utf-8')
                        print(f"[LOG] Received message from {client_address}: {decoded_message}")
                    except UnicodeDecodeError:
                        print(f"[LOG] Received binary data from {client_address}: {len(processed_payload)} bytes")

                    # Send ACK for valid packet
                    ack_packet = self.create_packet(ACK_TYPE, f"ACK for seq {sequence_num}", sequence_num=sequence_num)
                    client_socket.sendall(ack_packet)
                    print(f"[LOG] Sent ACK for sequence {sequence_num}")

                elif message_type == DISCONNECT_TYPE:
                    if self.handle_disconnect(client_socket, client_address):
                        print(f"[LOG] Client {client_address} disconnected successfully.")
                        break

                else:
                    print(f"[ERROR] Unknown message type {message_type} from {client_address}")

                if hasattr(self, 'simulate_delay'):
                    self.simulate_delay()

            except Exception as e:
                print(f"[ERROR] Error handling messages from {client_address}: {e}")
                break

        # Clean up session
        if client_address in self.client_sessions:
            del self.client_sessions[client_address]

        try:
            client_socket.close()
            print(f"[LOG] Connection with {client_address} closed.")
        except Exception as e:
            print(f"[ERROR] Failed to close connection with {client_address}: {e}")
        
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
            print("[CONFIG] Simulating 100% packet loss. All packets will be dropped.")
            
            # Simulate packet loss and send NACK
            def simulate_loss_and_nack(client_socket, sequence_num):
                print(f"[CHANNEL] Simulating packet loss for sequence {sequence_num}")
                nack_packet = self.create_packet(NACK_TYPE, f"NACK for seq {sequence_num}", sequence_num=sequence_num)
                client_socket.sendall(nack_packet)
                print(f"[LOG] Sent NACK for sequence {sequence_num}")
            
            self.simulate_loss_and_nack = simulate_loss_and_nack  # Attach function dynamically

        elif self.corruption_probability == 1.0:
            mode = "Packet Corruption"
            print("[CONFIG] Simulating 100% packet corruption. All packets will be corrupted.")
            
            # Simulate packet corruption and send NACK
            def simulate_corruption_and_nack(client_socket, sequence_num, payload):
                print(f"[CHANNEL] Simulating packet corruption for sequence {sequence_num}")
                corrupted_payload = bytearray(payload)
                if len(corrupted_payload) > 0:
                    corrupted_payload[0] = (corrupted_payload[0] + 1) % 256  # Corrupt the first byte
                nack_packet = self.create_packet(NACK_TYPE, f"NACK for seq {sequence_num}", sequence_num=sequence_num)
                client_socket.sendall(nack_packet)
                print(f"[LOG] Sent NACK for sequence {sequence_num}")
            
            self.simulate_corruption_and_nack = simulate_corruption_and_nack  # Attach function dynamically

        elif self.delay_probability == 1.0:
            mode = "Network Delay"
            print(f"[CONFIG] Simulating 100% network delay. All packets will be delayed by {self.delay_time:.2f} seconds.")
            
            # Simulate delay
            def simulate_delay():
                print(f"[CHANNEL] Simulating network delay of {self.delay_time:.2f} seconds.")
                time.sleep(self.delay_time)
            
            self.simulate_delay = simulate_delay  # Attach function dynamically

        elif self.loss_probability == 0.0 and self.corruption_probability == 0.0 and self.delay_probability == 0.0:
            mode = "Normal"
            print("[CONFIG] Normal mode. No packet loss, corruption, or delay.")
        else:
            mode = "Custom"
            print(f"[CONFIG] Custom mode: loss={self.loss_probability}, corruption={self.corruption_probability}, delay={self.delay_probability}, delay_time={self.delay_time}s")
        
        print(f"[CONFIG] Channel set to {mode} mode.")

# Example usage of the NetworkDevice class
device = NetworkDevice("127.0.0.1", 8080)
device.set_channel_conditions(loss_prob=1.0)  # Simula 100% de perda de pacotes
device.set_channel_conditions(corruption_prob=1.0)  # Simula 100% de corrupção
device.set_channel_conditions(delay_prob=1.0, delay_time=2.0)  # Simula 100% de atraso com 2 segundos