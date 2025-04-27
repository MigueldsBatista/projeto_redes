import socket
import json
import argparse
import time
from network_device import NetworkDevice
from settings import *

class Client(NetworkDevice):
    def __init__(self, server_addr='127.0.0.1', server_port=5000, protocol='gbn', max_fragment_size=3, window_size=4):
        # Call parent constructor with the new parameter name
        super().__init__(server_addr, server_port, protocol, max_fragment_size, window_size)
        
        # Client-specific attributes
        self.handshake_complete = False
        self.session_id = None
        
        # Sliding window buffers
        self.packet_buffer = {}  # Store packets that have been sent but not acknowledged
        self.ack_received = set()  # Keep track of which packets have been acknowledged
        self.last_timeout = 0  # Track when the last timeout occurred
        self.retry_count = 0    # Track retry attempts
        self.max_retries = 5    # Maximum number of retries before giving up
        
        # Simulation mode - for deterministic outcomes
        self.simulation_mode = "normal"  # Options: normal, loss, corruption, delay
        
    def connect(self):
        """Establish a connection with the server using the three-way handshake protocol"""
        try:
            # Create new socket
            self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self._socket.connect((self.server_addr, self.server_port))

            # STEP 1: SYN - Client → Server
            print(f"[LOG] Connected to server at {self.server_addr}:{self.server_port}")
            print(f"[LOG] Sending SYN packet with protocol={self.protocol}, max_fragment_size={self.max_fragment_size}, window_size={self.window_size}...")
            self.handle_packet(SYN_TYPE, json.dumps(self.connection_params))

            # STEP 2: Wait for SYN-ACK from Server
            print("[LOG] Waiting for SYN-ACK from server...")
            # Use proper buffer size for receiving complete packets
            response_packet = self._socket.recv(self.BUFFER_SIZE)
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
            self.max_fragment_size = syn_ack_data.get('max_fragment_size', self.max_fragment_size)
            self.protocol = syn_ack_data.get('protocol', self.protocol)
            self.window_size = syn_ack_data.get('window_size', self.window_size)
            
            # Update connection params to reflect negotiated values
            self.connection_params['max_fragment_size'] = self.max_fragment_size
            self.connection_params['protocol'] = self.protocol
            self.connection_params['window_size'] = self.window_size

            # STEP 3: ACK - Client → Server
            print("[LOG] Sending final ACK packet...")
            ack_data = {'session_id': self.session_id, 'message': 'Connection established'}
            self.handle_packet(HANDSHAKE_ACK_TYPE, json.dumps(ack_data))

            self.handshake_complete = True
            print("[LOG] Handshake completed successfully!")
            print(f"[LOG] Connection established with protocol={self.protocol}, max_fragment_size={self.max_fragment_size}, window_size={self.window_size}")
            return True
        except Exception as e:
            print(f"[ERROR] Failed to connect: {e}")
            return False

    def handle_timeout(self):
        """Handle timeout for unacknowledged packets with limited retries"""
        # Prevent timeout spam by limiting how often we can time out
        current_time = time.time()
        if current_time - self.last_timeout < self.timeout:
            # Too soon for another timeout
            return
            
        self.last_timeout = current_time
        self.retry_count += 1
        
        # Check if we've exceeded maximum retries
        if self.retry_count > self.max_retries:
            print(f"[ERROR] Maximum retries ({self.max_retries}) exceeded. Message delivery failed.")
            # We could raise an exception here, but instead we'll let the send_message method
            # handle this by checking retry_count in its loop
            return
        
        if self.protocol == 'gbn':
            # Go-Back-N: Resend all packets from base to next_seq_num - 1
            print(f"[LOG] Timeout detected: Resending packets from {self.base_seq_num} to {self.next_seq_num-1} (Attempt {self.retry_count}/{self.max_retries})")
            for seq in range(self.base_seq_num, self.next_seq_num):
                if seq in self.packet_buffer:
                    print(f"[LOG] Resending packet with sequence number {seq}")
                    self._socket.sendall(self.packet_buffer[seq])
        
        elif self.protocol == 'sr':
            # Selective Repeat: Resend only unacknowledged packets
            for seq in range(self.base_seq_num, self.next_seq_num):
                if seq not in self.ack_received and seq in self.packet_buffer:
                    print(f"[LOG] Resending packet with sequence number {seq}")
                    self._socket.sendall(self.packet_buffer[seq])

    def send_message(self, message):
        """Fragment and send a message using sliding window protocol with simulation modes"""
        try:
            if not self.handshake_complete or not self._socket:
                raise ConnectionError("Cannot send message: Not connected")

            # Ensure the message is a string
            if not isinstance(message, str):
                raise ValueError("Message must be a string")

            # Reset sequence numbers for this message
            self.base_seq_num = 0
            self.next_seq_num = 0
            self.packet_buffer.clear()
            self.ack_received.clear()
            self.last_timeout = 0
            self.retry_count = 0  # Reset retry counter for new message

            # Fragment the message into chunks based on max_fragment_size
            fragments = [message[i:i+self.max_fragment_size] for i in range(0, len(message), self.max_fragment_size)]
            print(f"[LOG] Message fragmented into {len(fragments)} chunks of max size {self.max_fragment_size}")
            
            # Set the socket to non-blocking mode for the sliding window
            self._socket.setblocking(False)
            
            # Start the sender loop
            last_action_time = time.time()
            
            while self.base_seq_num < len(fragments):
                # Check if maximum retries exceeded
                if self.retry_count > self.max_retries:
                    print(f"[ERROR] Failed to send message after {self.max_retries} attempts")
                    return False
                
                # Send packets within the window
                while self.next_seq_num < len(fragments) and self.next_seq_num < self.base_seq_num + self.window_size:
                    fragment = fragments[self.next_seq_num]
                    encoded_message = fragment.encode('utf-8')
                    
                    # Calculate checksum
                    checksum = self.calculate_checksum(encoded_message)
                    
                    # Create packet with sequence number and checksum
                    data_packet = self.create_packet(DATA_TYPE, encoded_message, sequence_num=self.next_seq_num, checksum=checksum)
                    
                    # Store packet for potential retransmission
                    self.packet_buffer[self.next_seq_num] = data_packet
                    
                    print(f"[LOG] Sending fragment {self.next_seq_num+1}/{len(fragments)}: '{fragment}' (seq={self.next_seq_num})")
                    self._socket.sendall(data_packet)
                    
                    # Update last action time
                    last_action_time = time.time()
                    
                    self.next_seq_num += 1
                
                # Try to receive ACKs (non-blocking)
                try:
                    while True:
                        response_packet = self._socket.recv(self.BUFFER_SIZE)
                        if not response_packet:
                            break
                        
                        parsed = self.parse_packet(response_packet)
                        if not parsed:
                            continue
                        
                        if parsed['type'] == ACK_TYPE:
                            if self.protocol == 'gbn':
                                # Go-Back-N: Move the base forward
                                ack_seq = parsed.get('sequence', 0)
                                print(f"[LOG] Received ACK for sequence {ack_seq}")
                                
                                if ack_seq >= self.base_seq_num:
                                    # Update the base sequence number
                                    old_base = self.base_seq_num
                                    self.base_seq_num = ack_seq + 1
                                    
                                    # Clean up the buffer for acknowledged packets
                                    for seq in range(old_base, self.base_seq_num):
                                        if seq in self.packet_buffer:
                                            del self.packet_buffer[seq]
                                    
                                    # Update last action time
                                    last_action_time = time.time()
                                
                            elif self.protocol == 'sr':
                                # Selective Repeat: Mark the specific packet as acknowledged
                                ack_seq = parsed.get('sequence', 0)
                                print(f"[LOG] Received ACK for sequence {ack_seq}")
                                
                                # Mark this packet as acknowledged
                                self.ack_received.add(ack_seq)
                                
                                # Move the base if possible
                                while self.base_seq_num in self.ack_received:
                                    # Clean up the buffer for the base packet
                                    if self.base_seq_num in self.packet_buffer:
                                        del self.packet_buffer[self.base_seq_num]
                                    
                                    self.base_seq_num += 1
                                
                                # Update last action time
                                last_action_time = time.time()
                        
                        elif parsed['type'] == NACK_TYPE:
                            if self.protocol == 'gbn':
                                # Go-Back-N: Resend all packets from base to next_seq_num - 1
                                print("[LOG] Received NACK, resending window")
                                for seq in range(self.base_seq_num, self.next_seq_num):
                                    if seq in self.packet_buffer:
                                        print(f"[LOG] Resending packet {seq}")
                                        self._socket.sendall(self.packet_buffer[seq])
                                
                                # Update last action time
                                last_action_time = time.time()
                            
                            elif self.protocol == 'sr':
                                # Selective Repeat: Resend only the NACKed packet
                                nack_seq = parsed.get('sequence', 0)
                                print(f"[LOG] Received NACK for sequence {nack_seq}")
                                
                                if nack_seq in self.packet_buffer:
                                    print(f"[LOG] Resending packet {nack_seq}")
                                    self._socket.sendall(self.packet_buffer[nack_seq])
                                    
                                # Update last action time
                                last_action_time = time.time()
                
                except BlockingIOError:
                    # No more data to read, this is expected
                    pass
                except Exception as e:
                    print(f"[ERROR] Error receiving ACK: {e}")
                
                # Check for timeout - if no action has occurred for the timeout period
                if time.time() - last_action_time > self.timeout and self.base_seq_num < self.next_seq_num:
                    self.handle_timeout()
                    last_action_time = time.time()  # Reset after handling timeout
                    
                    # NEW CODE: Break out of the loop if max retries exceeded after timeout
                    if self.retry_count > self.max_retries:
                        print(f"[ERROR] Maximum retries ({self.max_retries}) exceeded after timeout. Aborting message send.")
                        break
                
                # Small delay to prevent CPU hogging
                time.sleep(0.01)
            
            # Set the socket back to blocking mode
            self._socket.setblocking(True)
            
            # Clean up
            self.packet_buffer.clear()
            self.ack_received.clear()
            
            # Only show success message if we didn't time out
            if self.retry_count <= self.max_retries:
                print(f"[LOG] Message sent successfully in {len(fragments)} fragments")
                return True
            else:
                return False
        
        except Exception as e:
            print(f"[ERROR] Failed to send message: {e}")
            # Set the socket back to blocking mode in case of error
            if self._socket:
                self._socket.setblocking(True)
            return False

    def disconnect(self):
        """Terminate the connection with the server gracefully"""
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
            response_packet = self._socket.recv(self.BUFFER_SIZE)

            if not response_packet:
                raise ConnectionError("Server did not respond to disconnect request")

            print("[LOG] Server acknowledged disconnect. Closing socket...")
            self._socket.close()
            self.handshake_complete = False
            print("[LOG] Disconnected successfully.")
        except Exception as e:
            print(f"[ERROR] Failed to disconnect: {e}")


if __name__ == '__main__':
    try:
        # Parse command line arguments
        parser = argparse.ArgumentParser(description='Custom Protocol Client')
        parser.add_argument('--server-addr', default='127.0.0.1', help='Server address')
        parser.add_argument('--server-port', type=int, default=5000, help='Server port')
        parser.add_argument('--max-fragment-size', type=int, default=3, help='Maximum fragment size')
        parser.add_argument('--protocol', choices=['gbn', 'sr'], default='gbn', 
                           help='Reliable transfer protocol (Go-Back-N or Selective Repeat)')
        parser.add_argument('--window-size', type=int, default=4,
                           help='Sliding window size (number of packets in flight)')

        args = parser.parse_args()

        # Create client with provided arguments
        client = Client(
            server_addr=args.server_addr,
            server_port=args.server_port,
            max_fragment_size=args.max_fragment_size,
            protocol=args.protocol,
            window_size=args.window_size
        )

        # Create terminal UI and run interactive session
        from terminal_ui import TerminalUI
        terminal = TerminalUI(client)
        terminal.run_interactive_session()
    except KeyboardInterrupt:
        print("\n[LOG] Keyboard interrupt detected. Terminating client safely...")
    except Exception as e:
        print(f"[ERROR] An error occurred: {e}")
