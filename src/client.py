import socket
import json
import argparse
import time
from network_device import NetworkDevice
from settings import *

#ultimo teste de vez
class Client(NetworkDevice):
    def __init__(self, server_addr='127.0.0.1', server_port=5000, protocol='gbn', max_fragment_size=3, window_size=4):
        # Call parent constructor with the new parameter name
        super().__init__(server_addr, server_port, protocol, max_fragment_size, window_size)
        
        # Client-specific attributes
        self.handshake_complete = False
        self.session_id = None
        self.is_connected = False
        # Sliding window buffers
        self.packet_buffer = {}  # Store packets that have been sent but not acknowledged
        self.ack_received = set()  # Keep track of which packets have been acknowledged
        self.last_timeout = 0  # Track when the last timeout occurred
        self.retry_count = 0    # Track retry attempts
        self.max_retries = 5    # Maximum number of retries before giving up
        
        # Simulation mode - for deterministic outcomes
        self.simulation_mode = "normal"  # Options: normal, loss, corruption, delay
        
        # For SR, window also includes base and window size
        window_start = self.base_seq_num
        window_end = window_start + self.window_size - 1
        print(f"[WINDOW] SR Window: [{window_start}-{window_end}]")
        # For SR, show which packets have been acked within the window
        acked_in_window = [seq for seq in self.ack_received if window_start <= seq <= window_end]
        if acked_in_window:
            print(f"[WINDOW] Acked packets: {sorted(acked_in_window)}")
        
        # Show packets that haven't been acked yet
        unacked = [seq for seq in range(window_start, min(self.next_seq_num, window_end + 1))
                    if seq not in self.ack_received]
        if unacked:
            print(f"[WINDOW] Waiting for ACK: {unacked}")
        
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
            self.is_connected = True
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
            # We'll let the send_message method handle this by checking retry_count in its loop
            return
        
        if self.protocol == 'gbn':
            # Go-Back-N: Resend all packets from base to next_seq_num - 1
            print(f"[LOG] Timeout detected: Resending packets from {self.base_seq_num} to {self.next_seq_num-1} (Attempt {self.retry_count}/{self.max_retries})")
            for seq in range(self.base_seq_num, self.next_seq_num):
                if seq in self.packet_buffer:
                    print(f"[LOG] Resending packet with sequence number {seq}")
                    self._socket.sendall(self.packet_buffer[seq])
            return
        
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
    
            self.reset_parameters()  # Reset parameters for new message

            # Fragment the message into chunks based on max_fragment_size
            fragments = self.fragment_message(message)
            print(f"[LOG] Message fragmented into {len(fragments)} chunks of max size {self.max_fragment_size}")
            
            # Send each fragment and handle ACK/NACK
            for seq_num, fragment in enumerate(fragments):
                while True:
                    encoded_message = fragment.encode('utf-8')
                    
                    last_packet = False

                    if seq_num == len(fragments) - 1:
                        last_packet = True

                    # Create packet with sequence number and checksum
                    data_packet = self.create_packet(DATA_TYPE, encoded_message, sequence_num=seq_num, last_packet=last_packet)
                    print(f"[LOG] Sending fragment {seq_num+1}/{len(fragments)}: '{fragment}' (seq={seq_num})")
                    self._socket.sendall(data_packet)
    
                    # Wait for ACK or NACK
                    response_packet = self._socket.recv(self.BUFFER_SIZE)
                    if not response_packet:
                        raise ConnectionError("No response received")
    
                    parsed = self.parse_packet(response_packet)
                    if not parsed:
                        raise ValueError("Invalid response from server")
    
                    if parsed['type'] == ACK_TYPE and parsed['sequence'] == seq_num:
                        print(f"[LOG] Server acknowledged fragment {seq_num}")
                        break  # Move to the next fragment
                    elif parsed['type'] == NACK_TYPE and parsed['sequence'] == seq_num:
                        print(f"[LOG] Server requested retransmission for fragment {seq_num}")
                        continue  # Retransmit the current fragment
                    else:
                        print(f"[ERROR] Unexpected response from server: {parsed}")
                        raise ValueError("Unexpected response from server")
            
            print(f"[LOG] Message sent successfully in {len(fragments)} fragments")
            return True
        except Exception as e:
            print(f"[ERROR] Failed to send message: {e}")
            self.is_connected=False

            # Set the socket back to blocking mode in case of error
            if self._socket:
                try:
                    self._socket.setblocking(True)
                except Exception:
                    pass
            return False


    def reset_parameters(self):
        # Reset sequence numbers for this message
        self.base_seq_num = 0
        self.next_seq_num = 0
        self.packet_buffer.clear()
        self.ack_received.clear()
        self.last_timeout = 0
        self.retry_count = 0  # Reset retry counter for new message

    def fragment_message(self, message):
        """Fragment the message into smaller chunks based on max_fragment_size"""
        fragments = []
        for i in range(0, len(message), self.max_fragment_size):
            fragment = message[i:i + self.max_fragment_size]
            fragments.append(fragment)
        return fragments


    def process_acks(self):
        """Helper method to process acknowledgments"""
        try:
            while True:
                response_packet = self._socket.recv(self.BUFFER_SIZE)
                if not response_packet:
                    break
                
                parsed = self.parse_packet(response_packet)
                if not parsed:
                    continue
                
                if parsed['type'] == ACK_TYPE:
                    self.handle_ack(parsed)
                elif parsed['type'] == NACK_TYPE:
                    self.handle_nack(parsed)
        
        except BlockingIOError:
            # No more data to read, this is expected
            pass
        except Exception as e:
            print(f"[ERROR] Error receiving ACK: {e}")
    
    def handle_ack(self, parsed):
        """Process an acknowledgment packet"""
        ack_seq = parsed.get('sequence', 0)
        
        if self.protocol == 'gbn':
            # Go-Back-N: Move the base forward
            print(f"[LOG] Received ACK for sequence {ack_seq}")
            
            if ack_seq < self.base_seq_num:
                # Duplicate or old ACK, ignore
                return
                
            # Update the base sequence number
            old_base = self.base_seq_num
            self.base_seq_num = ack_seq + 1
            
            # Clean up the buffer for acknowledged packets
            for seq in range(old_base, self.base_seq_num):
                if seq in self.packet_buffer:
                    del self.packet_buffer[seq]
            
            # Display window update
            print(f"[WINDOW] Window moved: [{old_base}-{old_base + self.window_size - 1}] → [{self.base_seq_num}-{self.base_seq_num + self.window_size - 1}]")
            return
            
        # Selective Repeat: Mark the specific packet as acknowledged
        print(f"[LOG] Received ACK for sequence {ack_seq}")
        
        # Mark this packet as acknowledged
        self.ack_received.add(ack_seq)
        
        # Move the base if possible
        old_base = self.base_seq_num
        while self.base_seq_num in self.ack_received:
            # Clean up the buffer for the base packet
            if self.base_seq_num in self.packet_buffer:
                del self.packet_buffer[self.base_seq_num]
            
            self.base_seq_num += 1
        
        # Display window update if it moved
        if old_base != self.base_seq_num:
            print(f"[WINDOW] Window moved: [{old_base}-{old_base + self.window_size - 1}] → [{self.base_seq_num}-{self.base_seq_num + self.window_size - 1}]")
    
    def handle_nack(self, parsed):
        """Process a negative acknowledgment packet"""
        nack_seq = parsed.get('sequence', 0)
        
        if self.protocol == 'gbn':
            # Go-Back-N: Resend all packets from base to next_seq_num - 1
            print("[LOG] Received NACK, resending window")
            for seq in range(self.base_seq_num, self.next_seq_num):
                if seq in self.packet_buffer:
                    print(f"[LOG] Resending packet {seq}")
                    self._socket.sendall(self.packet_buffer[seq])
            return
            
        # Selective Repeat: Resend only the NACKed packet
        print(f"[LOG] Received NACK for sequence {nack_seq}")
        
        if nack_seq in self.packet_buffer:
            print(f"[LOG] Resending packet {nack_seq}")
            self._socket.sendall(self.packet_buffer[nack_seq])

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
        parser.add_argument('--host', default='127.0.0.1', help='Server address')
        parser.add_argument('--port', type=int, default=5000, help='Server port')
        parser.add_argument('--max-fragment-size', type=int, default=3, help='Maximum fragment size')
        parser.add_argument('--protocol', choices=['gbn', 'sr'], default='gbn', 
                           help='Reliable transfer protocol (Go-Back-N or Selective Repeat)')
        parser.add_argument('--window-size', type=int, default=4,
                           help='Sliding window size (number of packets in flight)')

        args = parser.parse_args()

        # Create client with provided arguments
        client = Client(
            server_addr=args.host,
            server_port=args.port,
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
