import socket
import json
import argparse
import time
from network_device import NetworkDevice

from settings import *

class Client(NetworkDevice):
    def __init__(self, server_addr='127.0.0.1', server_port=5000, operation_mode='step-by-step', max_size=1024):
        # Call parent constructor
        super().__init__(server_addr, server_port, operation_mode, max_size)
        
        # Client-specific attributes
        self.handshake_complete = False
        self.session_id = None
        self.client_socket = None
   
    def connect(self):
        try:
            # Create new socket
            #AF INET = IPv4
            #SOCK_STREAM = TCP
            self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.client_socket.connect((self.server_addr, self.server_port))
            
            # =============================================
            # HANDSHAKE STEP 1: SYN - Client → Server
            # Client initiates connection with parameters
            # =============================================
            print('Connected to server')
            print('Sending SYN...')
            syn_packet = self.create_packet(SYN_TYPE, json.dumps(self.connection_params))

            self.client_socket.sendall(syn_packet)
            
            # =============================================
            # HANDSHAKE STEP 2: Wait for SYN-ACK from Server
            # Server responds with accepted parameters
            # =============================================
            response_packet = self.client_socket.recv(self.connection_params['max_size'])
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
            
            # =============================================
            # HANDSHAKE STEP 3: ACK - Client → Server
            # Client acknowledges receipt of parameters
            # =============================================
            print('Sending ACK...')
            #0x03 = ACK
            ack_data = {'session_id': self.session_id, 'message': 'Connection established'}
            ack_packet = self.create_packet(0x03, json.dumps(ack_data))
            self.client_socket.sendall(ack_packet)
            
            # Handshake is now complete
            self.handshake_complete = True
            print('Handshake complete!')
            return True
            
        except Exception as e:
            print(f"Connection error: {e}")
            if self.client_socket:
                self.client_socket.close()
            return False
    
    def send_message(self, message):
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
            # Create data packet with DATA_TYPE (0x04) instead of generic 0x01
            data_packet = self.create_packet(DATA_TYPE, encoded_message)
            self.client_socket.sendall(data_packet)
            
            # If in step-by-step mode, wait for acknowledgment
            if self.connection_params['operation_mode'] == 'step-by-step':
                response_packet = self.client_socket.recv(1024)
                if not response_packet:
                    print("No acknowledgment received")
                    return False
                    
                parsed = self.parse_packet(response_packet)
                if parsed and parsed['type'] == ACK_TYPE:  # ACK
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
        if not self.client_socket:
            return
            
        try:
            print("Disconnecting from server...")
            # Send disconnect request
            disconnect_packet = self.create_packet(DISCONNECT_TYPE, "Disconnect")
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