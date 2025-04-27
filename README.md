# Custom Network Protocol Documentation

This document provides a detailed explanation of how our custom protocol implementation works, including the handshake process, message exchange, and connection termination.

## How to Start Reading and Understanding the Code

To understand the codebase, follow these steps:

### 1. **Understand the Theoretical Concepts**

Before diving into the code, familiarize yourself with the following networking concepts:
- **Sockets**: A socket is an endpoint for sending or receiving data across a computer network.
- **TCP/IP Protocol**: The Transmission Control Protocol ensures reliable communication between devices.
- **Three-Way Handshake**: A process used to establish a TCP connection between a client and a server.
- **Custom Protocols**: Protocols designed for specific use cases, defining message types, structures, and communication rules.

### 2. **Explore the Code Structure**

The project is organized into the following files:
- `/src/network_device.py`: Contains the base class `NetworkDevice`, which provides packet creation and parsing utilities.
- `/src/server.py`: Implements the server-side logic, including handling connections, messages, and the handshake process.
- `/src/client.py`: Implements the client-side logic, including connecting to the server, sending messages, and disconnecting.
- `/src/settings.py`: Defines constants for message types used in the protocol.

### 3. **Start with the `settings.py` File**

Open `/src/settings.py` to understand the constants used in the protocol:
- `SYN_TYPE`, `ACK_TYPE`, `DATA_TYPE`, and `DISCONNECT_TYPE` represent different message types.
- These constants are referenced throughout the code to identify the type of communication.

### 4. **Understand the `NetworkDevice` Base Class**

The `/src/network_device.py` file contains the `NetworkDevice` class, which provides:
- **Packet Creation (`create_packet`)**: Combines a header and payload into a complete packet.
- **Packet Parsing (`parse_packet`)**: Extracts and validates information from a received packet.

This class is inherited by both the `Server` and `Client` classes to handle low-level packet operations.

### 5. **Analyze the Server Implementation**

The `/src/server.py` file implements the `Server` class:
- **Initialization**: Sets up the server socket and prepares to accept client connections.
- **Handshake Process**: Implements the three-way handshake (SYN → SYN-ACK → ACK) to establish a connection.
- **Message Handling**: Processes data messages and sends acknowledgments.
- **Disconnection**: Handles client disconnect requests and cleans up resources.

Start by reading the `start` method, which is the entry point for the server, and follow the flow of connection handling.

### 6. **Analyze the Client Implementation**

The `/src/client.py` file implements the `Client` class:
- **Initialization**: Sets up the client socket and connection parameters.
- **Handshake Process**: Initiates the three-way handshake with the server.
- **Message Sending**: Sends data messages to the server and optionally waits for acknowledgments.
- **Disconnection**: Sends a disconnect request to the server and closes the connection.

Start by reading the `run_interactive_session` method, which provides an interactive way to send messages to the server.

### 7. **Run the Code**

To see the code in action:
1. Start the server:
   ```bash
   python /home/miguel/projeto_redes/src/server.py --host 127.0.0.1 --port 5000
   ```
2. Start the client:
   ```bash
   python /home/miguel/projeto_redes/src/client.py --server-addr 127.0.0.1 --server-port 5000
   ```
3. Follow the prompts in the client to send messages to the server.

### 8. **Experiment with the Protocol**

Modify the constants in `settings.py` or the parameters passed to the `Server` and `Client` classes to experiment with:
- Different maximum packet sizes.
- Step-by-step vs. burst operation modes.
- Custom message types or payloads.

### 9. **Debugging and Logs**

Use the print statements in the code to trace the flow of execution and understand how messages are processed. For example:
- Look for "Received SYN" in the server logs to see when a client initiates a connection.
- Look for "Handshake complete" in the client logs to confirm a successful connection.

### 10. **Extend the Protocol**

Once you understand the basics, consider extending the protocol by:
- Adding encryption for secure communication.
- Implementing error recovery mechanisms for lost or corrupted packets.
- Supporting additional message types or features.

## Message Types

Our protocol defines specific message types to distinguish between different kinds of communication:

- `SYN_TYPE (0x01)`: Used to initiate a connection (first step of handshake)
- `ACK_TYPE (0x02)`: Used for acknowledgments (server's response in handshake and message confirmations)
- `ACK_FINAL (0x03)`: Final acknowledgment from client to complete handshake
- `DATA_TYPE (0x04)`: Used for data exchange after the connection is established
- `DISCONNECT_TYPE (0x05)`: Used to request connection termination

## Packet Structure

Every packet in our protocol has the following structure:

```
+---------------+---------------+---------------+---------------+---------------+
| Payload Length| Message Type  | Sequence Num  | Checksum      | Payload       |
| (4 bytes)     | (1 byte)      | (2 bytes)     | (4 bytes)     | (variable)    |
+---------------+---------------+---------------+---------------+---------------+
```

- **Payload Length**: Size of the payload in bytes (allows dynamic message sizing)
- **Message Type**: Type of message (SYN, ACK, DATA, etc.)
- **Sequence Number**: Used for message ordering and reliability
- **Checksum**: MD5 hash of the payload for error detection
- **Payload**: The actual data being transmitted

## Connection Establishment (Three-Way Handshake)

### Step 1: Client SYN

The client initiates a connection by sending a SYN packet to the server:

```python
# Client creates a socket and connects to the server
self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
self.client_socket.connect((self.server_addr, self.server_port))

# Client sends SYN with connection parameters
syn_packet = self.create_packet(SYN_TYPE, json.dumps(self.connection_params))
self.client_socket.sendall(syn_packet)
```

The payload contains a JSON object with connection parameters:
- `operation_mode`: Step-by-step or burst mode
- `max_size`: Maximum packet size the client can handle

### Step 2: Server SYN-ACK

Upon receiving a SYN, the server:
1. Validates the client's parameters
2. Generates a session ID
3. Creates a session record
4. Sends a SYN-ACK response

```python
def handle_syn(self, client_socket, client_address, data):
    # Validate parameters
    operation_mode = data.get('operation_mode', self.operation_mode)
    requested_max_size = data.get('max_size', self.max_size)
    max_size = min(requested_max_size, self.max_size)
    
    # Generate session ID
    session_id = hashlib.md5(f"{client_address}{socket.gethostname()}".encode()).hexdigest()[:8]
    
    # Store session
    self.client_sessions[client_address] = {
        'operation_mode': operation_mode,
        'max_size': max_size,
        'session_id': session_id,
        'handshake_complete': False,
        'socket': client_socket
    }
    
    # Send SYN-ACK
    response = {
        'status': 'ok',
        'operation_mode': operation_mode,
        'max_size': max_size,
        'session_id': session_id,
        'message': 'SYN-ACK: Parameters accepted'
    }
    
    packet = self.create_packet(ACK_TYPE, json.dumps(response))
    client_socket.sendall(packet)
```

### Step 3: Client ACK

The client processes the SYN-ACK, stores the negotiated parameters, and sends the final ACK:

```python
# Client receives SYN-ACK
parsed = self.parse_packet(response_packet)
syn_ack_data = json.loads(parsed['payload'])

# Store negotiated parameters
self.session_id = syn_ack_data.get('session_id')
self.connection_params['max_size'] = syn_ack_data.get('max_size')
self.connection_params['operation_mode'] = syn_ack_data.get('operation_mode')

# Send final ACK
ack_data = {'session_id': self.session_id, 'message': 'Connection established'}
ack_packet = self.create_packet(0x03, json.dumps(ack_data))
self.client_socket.sendall(ack_packet)

# Connection is established
self.handshake_complete = True
```

## Data Exchange

After the handshake is complete, the client and server can exchange data messages:

### Client Sending Messages

```python
def send_message(self, message):
    # Create data packet
    data_packet = self.create_packet(DATA_TYPE, encoded_message)
    self.client_socket.sendall(data_packet)
    
    # Wait for acknowledgment in step-by-step mode
    if self.connection_params['operation_mode'] == 'step-by-step':
        response_packet = self.client_socket.recv(1024)
        parsed = self.parse_packet(response_packet)
        if parsed and parsed['type'] == ACK_TYPE:
            print("Message acknowledged by server")
```

### Server Handling Messages

The server continuously listens for messages from connected clients:

```python
def handle_client_messages(self, client_socket, client_address):
    while client_address in self.client_sessions:
        # Receive header
        header = client_socket.recv(11)
        
        # Parse header
        payload_length, message_type, sequence_num, checksum = struct.unpack('!IBH4s', header)
        
        # Receive payload
        payload = client_socket.recv(payload_length)
        
        # Handle based on message type
        if message_type == DATA_TYPE:
            self.handle_message(client_socket, client_address, payload)
        elif message_type == DISCONNECT_TYPE:
            self.handle_disconnect(client_socket, client_address)
            break
```

## Operation Modes

The protocol supports two operation modes:

### Step-by-Step Mode

In this mode, each message requires an acknowledgment before the next message can be sent:

1. Client sends a message
2. Server acknowledges the message
3. Client waits for acknowledgment before sending the next message

This provides higher reliability but lower throughput.

### Burst Mode

In burst mode, multiple messages can be sent without waiting for acknowledgments:

1. Client sends multiple messages in sequence
2. Server processes each message and may send bulk acknowledgments
3. Client can continue sending up to the window size limit

This provides higher throughput but potentially lower reliability.

## Connection Termination

Either the client or server can initiate connection termination:

### Client-Initiated Disconnect

```python
def disconnect(self):
    # Send disconnect request
    disconnect_packet = self.create_packet(DISCONNECT_TYPE, "Disconnect")
    self.client_socket.sendall(disconnect_packet)
    
    # Wait for acknowledgment
    response_packet = self.client_socket.recv(1024)
    
    # Close socket
    self.client_socket.close()
    self.handshake_complete = False
```

### Server Handling Disconnect

```python
def handle_disconnect(self, client_socket, client_address):
    # Send acknowledgment
    ack_packet = self.create_packet(ACK_TYPE, "ACK")
    client_socket.sendall(ack_packet)
    
    # Remove client session
    del self.client_sessions[client_address]
```

## Error Handling

The protocol includes multiple error handling mechanisms:

1. **Checksums**: Each message includes an MD5 checksum of the payload for error detection
2. **Timeouts**: Client and server can set timeouts for receiving responses
3. **Sequence Numbers**: Used to detect out-of-order or missing messages

## Packet Creation and Parsing

The core functionality of creating and parsing packets is implemented in the NetworkDevice base class:

### Packet Creation

```python
def create_packet(self, message_type, payload, sequence_num=0):
    # Convert string to bytes if needed
    if isinstance(payload, str):
        payload = payload.encode('utf-8')
        
    payload_length = len(payload)
    checksum = hashlib.md5(payload).digest()[:4]
    
    # Pack header
    header = struct.pack('!IBH4s', payload_length, message_type, sequence_num, checksum)
    
    # Return complete packet
    return header + payload
```

### Packet Parsing

```python
def parse_packet(self, packet):
    # Extract header
    header = packet[:11]
    payload_length, message_type, sequence_num, checksum = struct.unpack('!IBH4s', header)
    
    # Extract payload
    payload = packet[11:11+payload_length]
    
    # Verify checksum
    calculated_checksum = hashlib.md5(payload).digest()[:4]
    if calculated_checksum != checksum:
        print("Checksum error!")
        return None
        
    # Return parsed packet
    return {
        'type': message_type,
        'sequence': sequence_num,
        'payload': payload,
        'length': payload_length
    }
```

## Summary Flow of Communication

1. **Client connects to server**
2. **Three-way handshake**: SYN → SYN-ACK → ACK
3. **Data exchange**: Client sends DATA, server responds with ACK
4. **Connection termination**: Client sends DISCONNECT, server acknowledges
5. **Socket closure**: Both client and server close their sockets

This implementation provides a robust foundation for a custom protocol that can be extended with additional features like encryption, compression, or more sophisticated error recovery mechanisms.

## Function Reference

### NetworkDevice Class (network_device.py)

Base class for both client and server implementations:

- **__init__(server_addr, server_port, operation_mode, max_size)**: Initializes the device with connection parameters.
- **create_packet(message_type, payload, sequence_num, checksum)**: Creates a packet with the specified message type, payload data, sequence number, and checksum.
- **parse_packet(packet)**: Parses a received packet, extracting and validating its components (type, sequence, payload, length).
- **handle_packet(data_type, payload)**: Creates and sends a packet of the specified type with the given payload.
- **calculate_checksum(data)**: Calculates a simple checksum for data integrity verification.
- **simulate_channel(data)**: Simulates network conditions with packet loss and corruption for testing reliability features.

### Client Class (client.py)

Handles client-side communication with the server:

- **__init__(server_addr, server_port, operation_mode, max_size, protocol)**: Initializes the client with connection parameters and protocol type (GBN or SR).
- **connect()**: Establishes a connection with the server using the three-way handshake protocol.
- **send_message(message)**: Fragments messages into smaller chunks and sends them to the server with error handling and retry logic.
- **disconnect()**: Terminates the connection with the server gracefully.
- **run_interactive_session()**: Provides a command-line interface for user interaction with the protocol.

### Server Class (server.py)

Manages server-side communication and client connections:

- **__init__(host, port, max_size, operation_mode)**: Initializes the server with binding parameters.
- **handle_syn(client_socket, client_address, data)**: Processes SYN requests during the handshake, negotiating connection parameters.
- **handle_ack(client_address, data)**: Processes ACK messages to complete the handshake.
- **handle_message(client_socket, client_address, data_bytes)**: Processes data messages received from clients.
- **handle_disconnect(client_socket, client_address)**: Handles client disconnection requests.
- **process_handshake(client_socket, client_address)**: Manages the complete three-way handshake process.
- **start()**: Initializes the server, binds to the socket, and begins listening for connections.
- **handle_client_messages(client_socket, client_address)**: Continuously receives and processes messages from a connected client.

## Protocol Features and Implementation Status

[✅] Resolver erros ao rodar incialemnte o codigo
[✅] Colocar retornos com log no client
[✅] Checagem de ack esta mocada
[✅] Usuario poder escolher protocolo de comunicacao (repeticao seletiva e gobackn) /////// +
[✅] Ver diferencas no retorno dos acks a depender do protocolo
[✅] Usuario poder escoher tamanho da mensagem (limite
de 3 caracteres -> o de vcs ta 1024)
[✅] Caso exceda o limite, o client deve partir a mensagem em pacotes menores   /////// +
[] Fazer janela deslizante baseado no ack recebido


- notas

funcao simulate channel existe mas só ta sendo usada no server e não no client

não tiraram operation_mode do código, então ainda parece estar mockado a questão do step by step e do max_size = 1024