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

    def connect(self):
        # Create new socket
        self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._socket.connect((self.server_addr, self.server_port))

        # STEP 1: SYN - Client → Server
        print('Connected to server')
        print('Sending SYN...')
        self.handle_packet(SYN_TYPE, json.dumps(self.connection_params))

        # STEP 2: Wait for SYN-ACK from Server
        response_packet = self._socket.recv(self.connection_params['max_size'])
        if not response_packet:
            raise ConnectionError("No response from server")

        parsed = self.parse_packet(response_packet)
        if not parsed:
            raise ValueError("Invalid response from server")

        # Process SYN-ACK
        syn_ack_data = json.loads(parsed['payload'])
        print(f'Received SYN-ACK: {syn_ack_data}')

        if syn_ack_data.get('status') != 'ok':
            raise ConnectionError(f"Handshake failed: {syn_ack_data.get('message', 'Unknown error')}")

        # Store session information
        self.session_id = syn_ack_data.get('session_id')
        self.connection_params['max_size'] = syn_ack_data.get('max_size', self.connection_params['max_size'])
        self.connection_params['operation_mode'] = syn_ack_data.get('operation_mode', self.connection_params['operation_mode'])

        # STEP 3: ACK - Client → Server
        print('Sending ACK...')
        ack_data = {'session_id': self.session_id, 'message': 'Connection established'}
        self.handle_packet(HANDSHAKE_ACK_TYPE, json.dumps(ack_data))

        self.handshake_complete = True
        print('Handshake complete!')
        return True
    
    def send_message(self, message):
        if not self.handshake_complete or not self._socket:
            raise ConnectionError("Cannot send message: Not connected")

        encoded_message = message.encode('utf-8') if isinstance(message, str) else message

        if len(encoded_message) > self.connection_params["max_size"]:
            raise ValueError(f"Message exceeds maximum size of {self.connection_params['max_size']} bytes")

        data_packet = self.create_packet(DATA_TYPE, encoded_message)
        self._socket.sendall(data_packet)

        if self.connection_params['operation_mode'] != 'step-by-step':
            time.sleep(0.1)
            return True

        response_packet = self._socket.recv(1024)
        if not response_packet:
            raise ConnectionError("No acknowledgment received")

        parsed = self.parse_packet(response_packet)
        if not parsed or parsed['type'] != ACK_TYPE:
            raise ValueError("Invalid acknowledgment from server")

        time.sleep(0.1)
        return True
    
    def disconnect(self):
        if not self._socket:
            return

        print("Disconnecting from server...")
        # Send disconnect request
        disconnect_packet = self.create_packet(DISCONNECT_TYPE, "Disconnect")
        self._socket.sendall(disconnect_packet)

        # Wait for acknowledgment
        self._socket.settimeout(2.0)
        response_packet = self._socket.recv(1024)

        if not response_packet:
            raise ConnectionError("Server did not respond to disconnect request")

        print("Server acknowledged disconnect")
        self._socket.close()
        self.handshake_complete = False
        print("Disconnected")
    
    def run_interactive_session(self):
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
    try:
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
    except Exception as e:
        print(f"An error occurred: {e}")