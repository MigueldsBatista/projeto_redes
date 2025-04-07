import socket
import struct
import hashlib
import json
import argparse
import time


class Client:
    def __init__(self, server_addr='127.0.0.1', server_port=5000, operation_mode='step-by-step', max_size=1024):
        # Connection parameters
        self.connection_params = {
            "operation_mode": operation_mode,
            "max_size": max_size
        }
        
        self.server_addr = server_addr
        self.server_port = server_port
        self.handshake_complete = False
        self.session_id = None
        
        # Socket setup
        self.client_socket = None
        
    def create_packet(self, message_type, payload, sequence_num=0):
        """
        Creates a packet with proper headers
        
        Args:
            message_type (int): Type of message (1=SYN, 2=ACK, etc.)
            payload (bytes or str): Actual data
            sequence_num (int): Sequence number for ordering
            
        Returns:
            bytes: Complete packet
        """
        if isinstance(payload, str):
            payload = payload.encode('utf-8')
            
        payload_length = len(payload)
        checksum = hashlib.md5(payload).digest()[:4]  # 4-byte checksum
        
        # Pack header: length (4 bytes) + type (1 byte) + seq (2 bytes) + checksum (4 bytes)
        header = struct.pack('!IBH4s', payload_length, message_type, sequence_num, checksum)
        
        # Complete packet = header + payload
        return header + payload
        
    def parse_packet(self, packet):
        """Parse a packet into header and payload"""
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
    
    def connect(self):
        """Establish connection to server with handshake"""
        try:
            # Create new socket
            self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.client_socket.connect((self.server_addr, self.server_port))
            
            # Step 1: SYN - Send connection request
            print('Connected to server')
            print('Sending SYN...')
            syn_packet = self.create_packet(0x01, json.dumps(self.connection_params))
            self.client_socket.sendall(syn_packet)
            
            # Wait for SYN-ACK
            response_packet = self.client_socket.recv(1024)
            if not response_packet:
                print("No response from server")
                self.client_socket.close()
                return False
                
            # Parse response
            parsed = self.parse_packet(response_packet)
            if not parsed:
                print("Invalid response from server")
                self.client_socket.close()
                return False
                
            # Process SYN-ACK
            syn_ack_data = json.loads(parsed['payload'])
            print(f'Received SYN-ACK: {syn_ack_data}')
            
            if syn_ack_data.get('status') != 'ok':
                print(f'Handshake failed: {syn_ack_data.get("message", "Unknown error")}')
                self.client_socket.close()
                return False
                
            # Store session information
            self.session_id = syn_ack_data.get('session_id')
            self.connection_params['max_size'] = syn_ack_data.get('max_size', self.connection_params['max_size'])
            self.connection_params['operation_mode'] = syn_ack_data.get('operation_mode', 
                                                                     self.connection_params['operation_mode'])
            
            # Step 3: ACK - Send final acknowledgment
            print('Sending ACK...')
            ack_data = {'session_id': self.session_id, 'message': 'Connection established'}
            ack_packet = self.create_packet(0x03, json.dumps(ack_data))
            self.client_socket.sendall(ack_packet)
            
            self.handshake_complete = True
            print('Handshake complete!')
            return True
            
        except Exception as e:
            print(f"Connection error: {e}")
            if self.client_socket:
                self.client_socket.close()
            return False
    
    def send_message(self, message):
        """Send a message to the server"""
        if not self.handshake_complete:
            print("Cannot send message: Not connected")
            return False
            
        if isinstance(message, str):
            encoded_message = message.encode('utf-8')
        else:
            encoded_message = message
            
        if len(encoded_message) > self.connection_params["max_size"]:
            print(f"Message exceeds maximum size of {self.connection_params['max_size']} bytes")
            return False
            
        try:
            # Create data packet
            data_packet = self.create_packet(0x01, encoded_message)
            self.client_socket.sendall(data_packet)
            
            # If in step-by-step mode, wait for acknowledgment
            if self.connection_params['operation_mode'] == 'step-by-step':
                response_packet = self.client_socket.recv(1024)
                if not response_packet:
                    print("No acknowledgment received")
                    return False
                    
                parsed = self.parse_packet(response_packet)
                if parsed and parsed['type'] == 0x02:  # ACK
                    print("Message acknowledged by server")
                else:
                    print("Invalid acknowledgment from server")
                    return False
            
            # Short delay to prevent flooding
            time.sleep(0.1)
            return True
            
        except Exception as e:
            print(f"Error sending message: {e}")
            return False
    
    def disconnect(self):
        """Disconnect from server"""
        if not self.client_socket:
            return
            
        try:
            print("Disconnecting from server...")
            # Send disconnect request
            disconnect_packet = self.create_packet(0x05, "Disconnect")
            self.client_socket.sendall(disconnect_packet)
            
            # Wait for acknowledgment
            self.client_socket.settimeout(2.0)
            try:
                response_packet = self.client_socket.recv(1024)
                if response_packet:
                    print("Server acknowledged disconnect")
            except socket.timeout:
                pass  # Server might not respond
                
        except Exception as e:
            print(f"Error during disconnect: {e}")
            
        finally:
            self.client_socket.close()
            self.handshake_complete = False
            print("Disconnected")
    
    def run_interactive_session(self):
        """Run an interactive messaging session"""
        if not self.connect():
            return
            
        # Continuous message sending loop
        print("Enter messages (type 'exit' to quit):")
        while True:
            message = input('Message: ')
            
            if message.lower() == 'exit':
                break
                    
            self.send_message(message)
        
        self.disconnect()


if __name__ == '__main__':
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Custom Protocol Client')
    parser.add_argument('--server-addr', default='127.0.0.1', help='Server address')
    parser.add_argument('--server-port', type=int, default=5000, help='Server port')
    parser.add_argument('--max-size', type=int, default=1024, help='Maximum packet size')
    parser.add_argument('--operation-mode', choices=['step-by-step', 'burst'], 
                       default='step-by-step', help='Operation mode')
    
    args = parser.parse_args()
    
    # Create client with provided arguments
    client = Client(
        server_addr=args.server_addr,
        server_port=args.server_port,
        max_size=args.max_size,
        operation_mode=args.operation_mode
    )
    
    client.run_interactive_session()