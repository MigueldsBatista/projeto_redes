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
        try:
            # Create new socket
            self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self._socket.connect((self.server_addr, self.server_port))

            # STEP 1: SYN - Client → Server
            print(f"[LOG] Connected to server at {self.server_addr}:{self.server_port}")
            print("[LOG] Sending SYN packet...")
            self.handle_packet(SYN_TYPE, json.dumps(self.connection_params))

            # STEP 2: Wait for SYN-ACK from Server
            print("[LOG] Waiting for SYN-ACK from server...")
            response_packet = self._socket.recv(self.connection_params['max_size'])
            if not response_packet:
                raise ConnectionError("No response from server")

            parsed = self.parse_packet(response_packet)
            if not parsed:
                raise ValueError("Invalid response from server")

            # Process SYN-ACK
            syn_ack_data = json.loads(parsed['payload'])
            print(f"[LOG] Received SYN-ACK: {syn_ack_data}")

            if syn_ack_data.get('status') != 'ok':
                raise ConnectionError(f"Handshake failed: {syn_ack_data.get('message', 'Unknown error')}")

            # Store session information
            self.session_id = syn_ack_data.get('session_id')
            self.connection_params['max_size'] = syn_ack_data.get('max_size', self.connection_params['max_size'])
            self.connection_params['operation_mode'] = syn_ack_data.get('operation_mode', self.connection_params['operation_mode'])

            # STEP 3: ACK - Client → Server
            print("[LOG] Sending final ACK packet...")
            ack_data = {'session_id': self.session_id, 'message': 'Connection established'}
            self.handle_packet(HANDSHAKE_ACK_TYPE, json.dumps(ack_data))

            self.handshake_complete = True
            print("[LOG] Handshake completed successfully!")
            return True
        except Exception as e:
            print(f"[ERROR] Failed to connect: {e}")
            return False
    
    def send_message(self, message):
        try:
            if not self.handshake_complete or not self._socket:
                raise ConnectionError("Cannot send message: Not connected")

            # Ensure the message is a string
            if not isinstance(message, str):
                raise ValueError("Message must be a string")

            # Fragment the message into chunks of 3 characters
            fragments = [message[i:i+3] for i in range(0, len(message), 3)]

            for fragment in fragments:
                encoded_message = fragment.encode('utf-8')

                if len(encoded_message) > 3:
                    raise ValueError("Fragment exceeds maximum size of 3 bytes")

                data_packet = self.create_packet(DATA_TYPE, encoded_message)
                print(f"[LOG] Sending fragment: {fragment}")
                self._socket.sendall(data_packet)

                if self.connection_params['operation_mode'] != 'step-by-step':
                    time.sleep(0.1)
                    continue

                print("[LOG] Waiting for ACK from server...")
                response_packet = self._socket.recv(1024)
                if not response_packet:
                    raise ConnectionError("No ACK received")

                parsed = self.parse_packet(response_packet)
                if not parsed or parsed['type'] != ACK_TYPE:
                    raise ValueError("Invalid ACK from server")

                print("[LOG] Server message: ACK received")
                time.sleep(0.1)

            return True
        except Exception as e:
            print(f"[ERROR] Failed to send message: {e}")
            return False
    
    def disconnect(self):
        try:
            if not self._socket:
                return

            print("[LOG] Initiating disconnection...")
            # Send disconnect request
            disconnect_packet = self.create_packet(DISCONNECT_TYPE, "Disconnect")
            self._socket.sendall(disconnect_packet)

            # Wait for acknowledgment
            print("[LOG] Waiting for server acknowledgment...")
            self._socket.settimeout(2.0)
            response_packet = self._socket.recv(1024)

            if not response_packet:
                raise ConnectionError("Server did not respond to disconnect request")

            print("[LOG] Server acknowledged disconnect. Closing socket...")
            self._socket.close()
            self.handshake_complete = False
            print("[LOG] Disconnected successfully.")
        except Exception as e:
            print(f"[ERROR] Failed to disconnect: {e}")

    def run_interactive_session(self):
        if not self.connect():
            print("[ERROR] Unable to establish connection. Exiting...")
            return
        print("[LOG] Interactive session started. Type 'exit' to quit.")
        # Continuous message sending loop
        while True:
            message = input('Message: ')
            
            if message.lower() == 'exit':
                break
                    
            self.send_message(message)
        
        print("[LOG] Interactive session ended. Disconnecting...")
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