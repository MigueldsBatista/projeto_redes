import socket
import struct
import hashlib
import argparse
import json


class Server:
    def __init__(self, host='127.0.0.1', port=5000, max_size=1024, operation_mode='step-by-step'):
        # Server setup
        self.host = host
        self.port = port
        self.operation_mode = operation_mode
        self.max_size = max_size

        # Client connection tracking
        self.client_sessions = {}
        
        # Socket setup
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        
    def create_packet(self, message_type, payload, sequence_num=0):
        """
        Creates a packet with proper headers
        
        Args:
            message_type (int): Type of message (1=data, 2=ack, etc.)
            payload (bytes): Actual data
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
    
    def handle_syn(self, client_socket, client_address, data):
        """Handle SYN request from client (Step 2 of handshake)"""
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
        
        # Send SYN-ACK
        packet = self.create_packet(0x02, json.dumps(response))
        client_socket.sendall(packet)
        
        return session_id
    
    def handle_ack(self, client_address, data):
        """Handle final ACK from client (Step 3 of handshake)"""
        print(f'Received ACK from {client_address}: {data}')
        
        if client_address in self.client_sessions:
            self.client_sessions[client_address]['handshake_complete'] = True
            print(f'Handshake completed for client {client_address}')
            return True
        return False
    
    def handle_message(self, client_address, data):
        """Handle a data message from client"""
        # Check if handshake is complete
        if not self.client_sessions.get(client_address, {}).get('handshake_complete', False):
            print(f'Rejected message from {client_address}: Handshake not complete')
            return
            
        print(f'Received message from {client_address}: {data.decode("utf-8") if isinstance(data, bytes) else data}')
        
        # Send acknowledgment
        ack_packet = self.create_packet(0x02, "ACK")
        client_socket = self.client_sessions[client_address]['socket']
        client_socket.sendall(ack_packet)
    
    def handle_disconnect(self, client_address):
        """Handle client disconnect request"""
        print(f'Client disconnected: {client_address}')
        if client_address in self.client_sessions:
            # Send acknowledgment before closing
            ack_packet = self.create_packet(0x02, "ACK")
            try:
                self.client_sessions[client_address]['socket'].sendall(ack_packet)
            except:
                pass  # Client might already be gone
                
            del self.client_sessions[client_address]
    
    def handle_client(self, client_socket, client_address):
        """Handle all communication with a client"""
        try:
            # Receive initial 11 bytes for header
            header = client_socket.recv(11)
            if not header or len(header) < 11:
                return
                
            # Parse header
            payload_length, message_type, sequence_num, checksum = struct.unpack('!IBH4s', header)
            
            # Receive payload
            payload = client_socket.recv(payload_length)
            
            # Handle based on message type
            if message_type == 0x01:  # SYN
                data = json.loads(payload)
                self.handle_syn(client_socket, client_address, data)
                
            elif message_type == 0x03:  # ACK
                data = json.loads(payload)
                self.handle_ack(client_address, data)
                
            elif message_type == 0x01:  # DATA
                self.handle_message(client_address, payload)
                
            elif message_type == 0x05:  # DISCONNECT
                self.handle_disconnect(client_address)
                
        except Exception as e:
            print(f"Error handling client {client_address}: {e}")
            if client_address in self.client_sessions:
                del self.client_sessions[client_address]
    
    def start(self):
        """Start the server and listen for incoming connections"""
        try:
            self.server_socket.bind((self.host, self.port))
            self.server_socket.listen(5)
            print(f'Server started on {self.host}:{self.port}')
            print(f'Operation mode: {self.operation_mode}, Max packet size: {self.max_size} bytes')
            
            while True:
                # Accept new client connection
                client_socket, client_address = self.server_socket.accept()
                client_address = f"{client_address[0]}:{client_address[1]}"
                print(f'New connection from: {client_address}')
                
                # Handle this client (no threading yet)
                self.handle_client(client_socket, client_address)
                
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
