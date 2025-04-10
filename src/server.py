import socket
import struct
import hashlib
import argparse
import json
from network_device import NetworkDevice

from settings import *

class Server(NetworkDevice):
    def __init__(self, host='127.0.0.1', port=5000, max_size=1024, operation_mode='step-by-step'):
        # Call parent constructor with correct parameters
        super().__init__(host, port, operation_mode, max_size)
        
        # Server-specific attributes
        self.host = host  # Used for binding
        self.port = port  # Used for binding

        # Client connection tracking
        self.client_sessions = {}
        
        # Socket setup
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        
    def handle_syn(self, client_socket:socket.socket, client_address, data):
        """
        HANDSHAKE STEP 2: SYN-ACK - Server → Client
        Handle SYN request from client and respond with SYN-ACK
        
        This is the server's response to the client's initial SYN request.
        The server evaluates the client's connection parameters and responds
        with accepted values and a unique session ID.
        """
        print(f'Received SYN from {client_address}: {data}')
        
        # Validate connection parameters
        operation_mode = data.get('operation_mode', self.operation_mode)
        requested_max_size = data.get('max_size', self.max_size)
        
        # Apply server-side limits if needed
        max_size = min(requested_max_size, self.max_size)
        
        # Generate a session ID
        session_id = hashlib.md5(f"{client_address}{socket.gethostname()}".encode()).hexdigest()[:8]
        
        # Store session parameters
        self.client_sessions[client_address] = {
            'operation_mode': operation_mode,
            'max_size': max_size,
            'session_id': session_id,
            'handshake_complete': False,
            'socket': client_socket
        }
        
        # Return SYN-ACK with negotiated parameters
        response = {
            'status': 'ok',
            'operation_mode': operation_mode,
            'max_size': max_size,
            'session_id': session_id,
            'message': 'SYN-ACK: Parameters accepted'
        }
        
        # Send SYN-ACK with ACK_TYPE (0x02)
        packet = self.create_packet(ACK_TYPE, json.dumps(response))
        
        client_socket.sendall(packet)
        
        return session_id
    
    def handle_ack(self, client_address, data):
        """
        HANDSHAKE STEP 3: Process Client's ACK
        Handle final ACK from client to complete the handshake
        
        This is the server processing the client's acknowledgment,
        which completes the three-way handshake. The connection
        is now established and ready for data exchange.
        """
        print(f'Received ACK from {client_address}: {data}')
        
        if client_address in self.client_sessions:
            self.client_sessions[client_address]['handshake_complete'] = True
            print(f'Handshake completed for client {client_address}')
            return True
        return False
    
    def handle_message(self, client_socket, client_address, data):
        """Handle a data message from client"""
        # Check if handshake is complete
        if not self.client_sessions.get(client_address, {}).get('handshake_complete', False):
            print(f'Rejected message from {client_address}: Handshake not complete')
            return
        
        try:
            # Try to decode as UTF-8 if it's text data
            decoded_message = data.decode('utf-8')
            print(f'Received message from {client_address}: {decoded_message}')
        except UnicodeDecodeError:
            # If not text, handle as binary data
            print(f'Received binary data from {client_address}: {len(data)} bytes')
        
        # Send acknowledgment
        ack_packet = self.create_packet(ACK_TYPE, "ACK")
        client_socket.sendall(ack_packet)
    
    def handle_disconnect(self, client_socket, client_address):
        """Handle client disconnect request"""
        print(f'Client disconnected: {client_address}')
        if client_address in self.client_sessions:
            # Send acknowledgment before closing
            ack_packet = self.create_packet(ACK_TYPE, "ACK")
            try:
                client_socket.sendall(ack_packet)
            except:
                pass  # Client might already be gone
                
            del self.client_sessions[client_address]
            return True
        return False
    
    def process_handshake(self, client_socket:socket.socket, client_address):
        """Process the initial handshake with a client"""
        try:
            # Receive initial 11 bytes for header
            header = client_socket.recv(11)
            if not header or len(header) < 11:
                return False
                
            # Parse header
            payload_length, message_type, sequence_num, checksum = struct.unpack('!IBH4s', header)
            
            # Receive payload
            payload = client_socket.recv(payload_length)
            
            # Handle SYN message
            if message_type == SYN_TYPE:  # SYN
                data = json.loads(payload)
                self.handle_syn(client_socket, client_address, data)
                
                # Wait for ACK from client
                header = client_socket.recv(11)
                if not header or len(header) < 11:
                    return False
                    
                payload_length, message_type, sequence_num, checksum = struct.unpack('!IBH4s', header)
                
                if message_type != 0x03:  # Not ACK
                    return False
                    
                payload = client_socket.recv(payload_length)
                data = json.loads(payload)
                
                # Process final ACK
                if self.handle_ack(client_address, data):
                    print(f"Handshake completed with {client_address}")
                    return True
            
            return False
                
        except Exception as e:
            print(f"Error in handshake with {client_address}: {e}")
            return False
    
    def handle_client_messages(self, client_socket:socket.socket, client_address):
        """Handle messages from a client after handshake"""
        while client_address in self.client_sessions:
            try:
                # Receive header
                header = client_socket.recv(11)
                if not header or len(header) < 11:
                    break
                
                # Parse header
                payload_length, message_type, sequence_num, checksum = struct.unpack('!IBH4s', header)
                
                # Receive payload
                payload = client_socket.recv(payload_length)
                if len(payload) < payload_length:
                    print(f"Incomplete payload received from {client_address}")
                    break
                
                # Handle message based on type
                if message_type == DATA_TYPE:  # DATA
                    self.handle_message(client_socket, client_address, payload)
                    
                elif message_type == DISCONNECT_TYPE:  # DISCONNECT
                    if self.handle_disconnect(client_socket, client_address):
                        break
                
            except Exception as e:
                print(f"Error handling messages from {client_address}: {e}")
                break
        
        # Clean up if not already done
        if client_address in self.client_sessions:
            del self.client_sessions[client_address]
            
        try:
            client_socket.close()
        except:
            pass
    
    def start(self):
        """Start the server and listen for incoming connections"""
        try:
            self.server_socket.bind((self.host, self.port))
            self.server_socket.listen(5)
            print(f'Server started on {self.host}:{self.port}')
            print(f'Operation mode: {self.operation_mode}, Max packet size: {self.max_size} bytes')
            
            while True:
                # Accept new client connection
                result = self.server_socket.accept()
                
                client_socket = result[0]
                addr = result[1]

                client_address = f"{addr[0]}:{addr[1]}"
                print(f'New connection from: {client_address}')
                
                # Process handshake
                if self.process_handshake(client_socket, client_address):
                    # If handshake successful, handle messages from this client
                    self.handle_client_messages(client_socket, client_address)
                else:
                    # If handshake failed, close connection
                    print(f"Handshake failed with {client_address}")
                    client_socket.close()
                
        except KeyboardInterrupt:
            print("Server shutting down...")
        finally:
            self.server_socket.close()


if __name__ == '__main__':
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Custom Protocol Server')
    parser.add_argument('--host', default='127.0.0.1', help='Host address to bind')
    parser.add_argument('--port', type=int, default=5000, help='Port to listen on')
    parser.add_argument('--max-size', type=int, default=1024, help='Maximum packet size')
    parser.add_argument('--operation-mode', choices=['step-by-step', 'burst'], 
                       default='step-by-step', help='Operation mode')
    
    args = parser.parse_args()
    
    # Start server with provided arguments
    server = Server(host=args.host, port=args.port, 
                   max_size=args.max_size, 
                   operation_mode=args.operation_mode)
    server.start()
