import socket
import hashlib
import argparse
import json
from network_device import NetworkDevice
from settings import *
import random
import struct
# We'll remove the direct import of ServerTerminalUI to avoid circular dependencies


class Server(NetworkDevice):
    def __init__(self, host='127.0.0.1', port=5000, protocol='gbn', max_fragment_size=3, window_size=4):
        super().__init__(host, port, protocol, max_fragment_size, window_size)
        self.host = host
        self.port = port
        self.client_sessions = {}
        self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    def display_sliding_window(self, client_address):
        """Display the current sliding window for a client session"""
        if client_address not in self.client_sessions:
            return
            
        session = self.client_sessions[client_address]
        protocol = session.get('protocol', 'gbn')
        expected = session.get('expected_seq_num', 0)
        window_size = session.get('window_size', self.window_size)
        
        if protocol == 'gbn':
            # For GBN, window is [expected, expected+window_size-1]
            start = expected
            end = start + window_size - 1
            print(f"[WINDOW] GBN Window: [{start}-{end}]")
        else:
            # For SR, window includes expected seq num and window size
            start = expected
            end = start + window_size - 1
            print(f"[WINDOW] SR Window: [{start}-{end}]")
            
            # For SR, also show which packets are buffered
            buffered = sorted(session.get('received_buffer', {}).keys())
            if buffered:
                print(f"[WINDOW] Buffered packets: {buffered}")

    def handle_syn(self, client_socket: socket.socket, client_address:str, data:dict):
        """Process SYN request during handshake and negotiate connection parameters"""
        print(f'[LOG] Received SYN from {client_address}: {data}')
        
        # Extract and validate connection parameters
        client_protocol = data.get('protocol', self.protocol)
        requested_fragment_size = data.get('max_fragment_size', self.max_fragment_size)
        requested_window_size = data.get('window_size', self.window_size)
        
        # Apply server-side limits if needed
        max_fragment_size = min(requested_fragment_size, self.max_fragment_size)
        
        # Generate a unique session ID
        session_id = hashlib.md5(f"{client_address}{socket.gethostname()}".encode()).hexdigest()[:8]
        
        # Store session information
        self.client_sessions[client_address] = {
            'protocol': client_protocol,
            'max_fragment_size': max_fragment_size,
            'window_size': requested_window_size,
            'session_id': session_id,
            'handshake_complete': False,
            'socket': client_socket,
            'expected_seq_num': 0,  # For GBN
            'received_buffer': {},  # For SR
            'last_ack_sent': -1     # For tracking ACKs
        }
        
        # Prepare SYN-ACK response with negotiated parameters
        response = {
            'status': 'ok',
            'protocol': client_protocol,
            'max_fragment_size': max_fragment_size,
            'window_size': requested_window_size,
            'session_id': session_id,
            'message': 'SYN-ACK: Parameters accepted'
        }
        
        # Send SYN-ACK
        packet = self.create_packet(ACK_TYPE, json.dumps(response))
        client_socket.sendall(packet)
        return session_id

    def handle_ack(self, client_address:str, data:dict):
        """Process final ACK to complete handshake"""
        print(f'[LOG] Received ACK from {client_address}: {data}')
        if client_address not in self.client_sessions:
            return False
            
        self.client_sessions[client_address]['handshake_complete'] = True
        print(f'[LOG] Handshake completed for client {client_address}')
        return True


    def process_handshake(self, client_socket: socket.socket, client_address: str):
        """Manage the complete three-way handshake process"""
        try:
            # Receive initial SYN header - use proper buffer size
            header = client_socket.recv(self.BUFFER_SIZE)
            if not header or len(header) < self.HEADER_SIZE:
                print(f"[ERROR] Invalid header received from {client_address}")
                return False

            # Parse header fields
            parsed = self.parse_packet(header)
            if not parsed:
                print(f"[ERROR] Failed to parse packet from {client_address}")
                return False

            # Verify message type is SYN
            if parsed['type'] != SYN_TYPE:
                print(f"[ERROR] Expected SYN but got message type {parsed['type']}")
                return False

            # Parse connection parameters
            data = json.loads(parsed['payload'])
            client_protocol = data.get('protocol', 'gbn')
            print(f"[LOG] Client requesting protocol: {client_protocol}")
            
            # Process SYN and send SYN-ACK
            self.handle_syn(client_socket, client_address, data)

            # Wait for final ACK - use proper buffer size
            header = client_socket.recv(self.BUFFER_SIZE)
            parsed = self.parse_packet(header)
            if not parsed:
                print(f"[ERROR] Failed to receive ACK from {client_address}")
                return False

            # Verify message type is HANDSHAKE_ACK
            if parsed['type'] != HANDSHAKE_ACK_TYPE:
                print(f"[ERROR] Expected HANDSHAKE_ACK but got message type {parsed['type']}")
                return False

            # Complete handshake
            data = json.loads(parsed['payload'])
            if not self.handle_ack(client_address, data):
                return False
                
            print(f"[LOG] Handshake completed with {client_address}")
            return True
            
        except Exception as e:
            print(f"[ERROR] Error in handshake with {client_address}: {e}")
            return False

    def start(self):
        """Initialize the server, bind to socket, and begin listening for connections"""
        try:
            self._socket.bind((self.host, self.port))
            self._socket.listen(5)
            print(f'[LOG] Server started on {self.host}:{self.port}')
            print(f'[LOG] Protocol: {self.protocol}, Max fragment size: {self.max_fragment_size} characters')
            print(f'[LOG] Window size: {self.window_size} packets')

            while True:
                client_socket , addr = self._socket.accept()
                client_address = f"{addr[0]}:{addr[1]}"
                print(f'[LOG] New connection from: {client_address}')

                if self.process_handshake(client_socket, client_address):
                    self.handle_client_messages(client_socket, client_address)
                    continue

                print(f"[ERROR] Handshake failed with {client_address}")
                client_socket.close()
                
        except KeyboardInterrupt:
            print("[LOG] Server shutting down gracefully...")
        except Exception as e:
            print(f"[ERROR] Server error: {e}")
        finally:
            self._socket.close()
            print("[LOG] Server socket closed")


if __name__ == '__main__':
    try:
        # Parse command line arguments
        parser = argparse.ArgumentParser(description='Custom Protocol Server')
        parser.add_argument('--host', default='127.0.0.1', help='Host address to bind')
        parser.add_argument('--port', type=int, default=5000, help='Port to listen on')
        parser.add_argument('--max-fragment-size', type=int, default=3, help='Maximum fragment size')
        parser.add_argument('--protocol', choices=['gbn', 'sr'], default='gbn',
                            help='Reliable transfer protocol (Go-Back-N or Selective Repeat)')
        parser.add_argument('--window-size', type=int, default=4,
                            help='Sliding window size (number of packets in flight)')
    
        args = parser.parse_args()
    
        # Start server with provided arguments
        server = Server(
            host=args.host,
            port=args.port,
            max_fragment_size=args.max_fragment_size,
            protocol=args.protocol,
            window_size=args.window_size
        )
        
        # Use lazy loading for ServerTerminalUI to avoid circular imports
        # Only import and use it when we actually need it
        from terminal_ui import ServerTerminalUI
        
        # Create server terminal UI
        server_ui = ServerTerminalUI(server)
        
        # Display server status
        server_ui.show_server_status()
        
        # Start the server
        server.start()
    
    except Exception as e:
        print(f"[ERROR] An error occurred: {e}")
