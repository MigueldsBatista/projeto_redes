import socket
import struct
import hashlib
import argparse
import json
import random
from network_device import NetworkDevice
from settings import *

NACK_TYPE = 0x04
class Server(NetworkDevice):
    def __init__(self, host='127.0.0.1', port=5000, max_size=1024, operation_mode='step-by-step'):
        super().__init__(host, port, operation_mode, max_size)
        self.host = host
        self.port = port
        self.client_sessions = {}
        self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    def handle_syn(self, client_socket: socket.socket, client_address, data):
        print(f'Received SYN from {client_address}: {data}')
        operation_mode = data.get('operation_mode', self.operation_mode)
        requested_max_size = data.get('max_size', self.max_size)
        max_size = min(requested_max_size, self.max_size)
        session_id = hashlib.md5(f"{client_address}{socket.gethostname()}".encode()).hexdigest()[:8]

        self.client_sessions[client_address] = {
            'operation_mode': operation_mode,
            'max_size': max_size,
            'session_id': session_id,
            'handshake_complete': False,
            'socket': client_socket
        }

        response = {
            'status': 'ok',
            'operation_mode': operation_mode,
            'max_size': max_size,
            'session_id': session_id,
            'message': 'SYN-ACK: Parameters accepted'
        }

        packet = self.create_packet(ACK_TYPE, json.dumps(response))
        client_socket.sendall(packet)
        return session_id

    def handle_ack(self, client_address, data):
        print(f'Received ACK from {client_address}: {data}')
        if client_address in self.client_sessions:
            self.client_sessions[client_address]['handshake_complete'] = True
            print(f'Handshake completed for client {client_address}')
            return True
        return False

    def handle_message(self, client_socket, client_address, data):
        if not self.client_sessions.get(client_address, {}).get('handshake_complete', False):
            print(f'Rejected message from {client_address}: Handshake not complete')
            return
        try:
            decoded_message = data.decode('utf-8')
            print(f'Received message from {client_address}: {decoded_message}')
        except UnicodeDecodeError:
            print(f'Received binary data from {client_address}: {len(data)} bytes')

        ack_packet = self.create_packet(ACK_TYPE, "ACK")
        client_socket.sendall(ack_packet)

    def handle_disconnect(self, client_socket, client_address):
        print(f'Client disconnected: {client_address}')
        if client_address in self.client_sessions:
            ack_packet = self.create_packet(ACK_TYPE, "ACK")
            try:
                client_socket.sendall(ack_packet)
            except:
                pass
            del self.client_sessions[client_address]
            return True
        return False

    def process_handshake(self, client_socket: socket.socket, client_address):
        try:
            header = client_socket.recv(11)
            if not header or len(header) < 11:
                return False

            payload_length, message_type, sequence_num, checksum = struct.unpack('!IBH4s', header)
            payload = client_socket.recv(payload_length)

            if message_type != SYN_TYPE:
                return False

            data = json.loads(payload)
            self.protocol = data.get('protocol', 'gbn')
            self.handle_syn(client_socket, client_address, data)

            header = client_socket.recv(11)
            if not header or len(header) < 11:
                return False

            payload_length, message_type, sequence_num, checksum = struct.unpack('!IBH4s', header)

            if message_type != 0x03:
                return False

            payload = client_socket.recv(payload_length)
            data = json.loads(payload)

            if self.handle_ack(client_address, data):
                print(f"Handshake completed with {client_address}")
                return True

            return False
        except Exception as e:
            print(f"Error in handshake with {client_address}: {e}")
            return False

    def calculate_checksum(self, data):
        return sum(data) % 256

    def simulate_channel(self, data):
        loss_probability = 0.1
        error_probability = 0.1

        if random.random() < loss_probability:
            print("[LOG] Pacote perdido!")
            return None

        if random.random() < error_probability:
            print("[LOG] Pacote corrompido!")
            data = bytearray(data)
            index = random.randint(0, len(data) - 1)
            data[index] = (data[index] + random.randint(1, 255)) % 256
            return bytes(data)

        return data

    def handle_client_messages(self, client_socket: socket.socket, client_address):
        while client_address in self.client_sessions:
            try:
                header = client_socket.recv(11)
                if not header or len(header) < 11:
                    print(f"[ERROR] Incomplete or missing header from {client_address}")
                    break

                try:
                    payload_length, message_type, sequence_num, checksum = struct.unpack('!IBH4s', header)
                except struct.error as e:
                    print(f"[ERROR] Failed to unpack header from {client_address}: {e}")
                    break

                payload = client_socket.recv(payload_length)
                if len(payload) < payload_length:
                    print(f"[ERROR] Incomplete payload received from {client_address}")
                    break

                payload = self.simulate_channel(payload)
                if payload is None:
                    print(f"[LOG] Packet from {client_address} lost in simulated channel.")
                    continue

                if message_type == DATA_TYPE:
                    try:
                        decoded_message = payload.decode('utf-8')
                        print(f"[LOG] Received message from {client_address}: {decoded_message}")
                    except UnicodeDecodeError:
                        print(f"[LOG] Received binary data from {client_address}: {len(payload)} bytes")

                    if self.protocol == 'gbn':
                        ack_packet = self.create_packet(ACK_TYPE, "ACK for GBN")
                    elif self.protocol == 'sr':
                        ack_packet = self.create_packet(ACK_TYPE, f"ACK for {sequence_num}")
                    else:
                        ack_packet = self.create_packet(ACK_TYPE, "ACK")

                    client_socket.sendall(ack_packet)

                elif message_type == DISCONNECT_TYPE:
                    if self.handle_disconnect(client_socket, client_address):
                        break

            except Exception as e:
                print(f"[ERROR] Error handling messages from {client_address}: {e}")
                break

        if client_address in self.client_sessions:
            del self.client_sessions[client_address]

        try:
            client_socket.close()
        except:
            pass

    def start(self):
        try:
            self._socket.bind((self.host, self.port))
            self._socket.listen(5)
            print(f'Server started on {self.host}:{self.port}')
            print(f'Operation mode: {self.operation_mode}, Max packet size: {self.max_size} bytes')

            while True:
                result = self._socket.accept()
                client_socket = result[0]
                addr = result[1]
                client_address = f"{addr[0]}:{addr[1]}"
                print(f'New connection from: {client_address}')

                if self.process_handshake(client_socket, client_address):
                    self.handle_client_messages(client_socket, client_address)
                    continue

                print(f"Handshake failed with {client_address}")
                client_socket.close()
        except KeyboardInterrupt:
            print("Server shutting down...")
        finally:
            self._socket.close()


    def simulate_channel(self, data):
        """
        Simula um canal com perdas e erros.
        :param data: Dados recebidos (bytes)
        :return: Dados possivelmente alterados ou None (em caso de perda)
        """
        loss_probability = 0.1  # 10% de chance de perda
        error_probability = 0.1  # 10% de chance de erro

        # Simular perda de pacote
        if random.random() < loss_probability:
            print("[LOG] Pacote perdido!")
            return None

        # Simular erro no pacote
        if random.random() < error_probability:
            print("[LOG] Pacote corrompido!")
            data = bytearray(data)
            index = random.randint(0, len(data) - 1)
            data[index] = (data[index] + random.randint(1, 255)) % 256
            return bytes(data)

        return data


    def handle_client_messages(self, client_socket: socket.socket, client_address):
        while client_address in self.client_sessions:
            try:
                # Receber cabeçalho
                header = client_socket.recv(11)
                if not header or len(header) < 11:
                    print(f"[ERROR] Incomplete or missing header from {client_address}")
                    break

                # Parse do cabeçalho
                try:
                    payload_length, message_type, sequence_num, checksum = struct.unpack('!IBH4s', header)
                except struct.error as e:
                    print(f"[ERROR] Failed to unpack header from {client_address}: {e}")
                    break

                # Receber payload
                payload = client_socket.recv(payload_length)
                if len(payload) < payload_length:
                    print(f"[ERROR] Incomplete payload received from {client_address}")
                    break

                # Simular canal de perdas e erros
                payload = self.simulate_channel(payload)
                if payload is None:
                    print(f"[LOG] Packet from {client_address} lost in simulated channel.")
                    continue  # Pacote perdido, não processa

                # Processar mensagem com base no tipo
                if message_type == DATA_TYPE:
                    try:
                        decoded_message = payload.decode('utf-8')
                        print(f"[LOG] Received message from {client_address}: {decoded_message}")
                    except UnicodeDecodeError:
                        print(f"[LOG] Received binary data from {client_address}: {len(payload)} bytes")

                    # Enviar ACK
                    if self.protocol == 'gbn':
                        ack_packet = self.create_packet(ACK_TYPE, "ACK for GBN")
                    elif self.protocol == 'sr':
                        ack_packet = self.create_packet(ACK_TYPE, f"ACK for {sequence_num}")
                    else:
                        ack_packet = self.create_packet(ACK_TYPE, "ACK")

                    client_socket.sendall(ack_packet)
                    print(f"[LOG] Sent ACK to {client_address}")

                elif message_type == DISCONNECT_TYPE:
                    if self.handle_disconnect(client_socket, client_address):
                        print(f"[LOG] Client {client_address} disconnected successfully.")
                        break

                else:
                    print(f"[ERROR] Unknown message type {message_type} from {client_address}")

            except Exception as e:
                print(f"[ERROR] Error handling messages from {client_address}: {e}")
                break

        # Limpeza
        if client_address in self.client_sessions:
            del self.client_sessions[client_address]

        try:
            client_socket.close()
            print(f"[LOG] Connection with {client_address} closed.")
        except Exception as e:
            print(f"[ERROR] Failed to close connection with {client_address}: {e}")


if __name__ == '__main__':
    try:
            # Parse command line arguments
        parser = argparse.ArgumentParser(description='Custom Protocol Server')
        parser.add_argument('--host', default='127.0.0.1', help='Host address to bind')
        parser.add_argument('--port', type=int, default=5000, help='Port to listen on')
        parser.add_argument('--max-size', type=int, default=1024, help='Maximum packet size')
        parser.add_argument('--operation-mode', choices=['step-by-step', 'burst'],
                                default='step-by-step', help='Operation mode')
    
        args = parser.parse_args()
    
        # Start server with provided arguments
        server = Server(host=args.host,
                        port=args.port,
                        max_size=args.max_size,
                        operation_mode=args.operation_mode)
        server.start()
    
    except Exception as e:
        print(f"An error occurred: {e}")
