# Custom Network Protocol Implementation

This project implements a custom client-server communication protocol built from scratch without relying on HTTP. The implementation uses raw sockets for communication and defines its own protocol rules for connection establishment, data transfer, and connection termination.

## Libraries for Custom Protocol Implementation

For a truly from-scratch implementation without HTTP, we'll use:

1. **socket** - Python's built-in socket library for low-level network communication
   - Provides direct access to the transport layer
   - Allows complete control over packet creation and handling
   - Example: `import socket`

2. **struct** - For binary data packing/unpacking to create custom packet formats
   - Used to pack headers and message metadata into binary format
   - Example: `import struct`

3. **threading/asyncio** - For handling multiple connections
   - Manages concurrent client connections
   - Example: `import threading` or `import asyncio`

4. **hashlib** - For generating checksums for error detection
   - Creates message digests to verify data integrity
   - Example: `import hashlib`

## Operation Modes

The protocol supports two primary operation modes:

### 1. Step-by-Step Mode
- Each message requires acknowledgment before the next message is sent
- Provides higher reliability with immediate confirmation
- Suitable for critical data where every packet must be confirmed
- Lower throughput but higher reliability
- Implementation example:
  ```python
  # Client sends message
  send_message(message)
  # Client waits for acknowledgment before sending next message
  ack = receive_acknowledgment()
  if ack.status == "OK":
      # Send next message
  ```

### 2. Burst Mode
- Multiple messages are sent in sequence without waiting for acknowledgments
- Higher throughput but potentially lower reliability
- Uses sliding window protocol with configurable window size
- Suitable for applications requiring higher data transfer rates
- Implementation example:
  ```python
  # Client sends multiple messages in sequence
  for message in messages:
      send_message(message)
  # Client then processes acknowledgments
  process_acknowledgments()
  ```

## Protocol Specification

### 1. Connection Establishment (Three-way Handshake)

Similar to TCP, our protocol uses a three-way handshake process:

1. **SYN**: Client sends connection request with parameters:
   - `operation_mode`: The type of data transmission ("step-by-step" or "burst")
   - `max_packet_size`: Maximum packet size the client can handle
   - `client_id`: Unique identifier for the client (optional)

2. **SYN-ACK**: Server responds with:
   - `status`: Indicates if connection parameters are accepted
   - `session_id`: Unique session identifier
   - `max_packet_size`: Server's maximum packet size (negotiated)
   - `operation_mode`: Confirmed operation mode
   - `window_size`: Number of messages in burst mode (if applicable)

3. **ACK**: Client acknowledges receipt of server parameters

### 2. Message Format

Each message consists of a header and payload:

```
+----------------+----------------+----------------+
| Message Length | Message Type   | Payload        |
| (4 bytes)      | (1 byte)       | (variable)     |
+----------------+----------------+----------------+
```

Message Types:
- `0x01`: Data message
- `0x02`: Acknowledgment
- `0x03`: Error
- `0x04`: Keep-alive
- `0x05`: Disconnect request

### 3. Error Handling

- Timeout: If no response is received within a defined timeout period, the message is resent
- Checksum: Messages include a checksum for error detection
- Sequence numbers: Messages include sequence numbers to detect lost messages

### 4. Connection Termination

1. Client sends disconnect request
2. Server acknowledges and closes the connection
3. Client confirms and closes the connection

## Implementation

### Client Implementation

The client implementation includes:
- Socket initialization
- Connection establishment through the handshake process
- Message sending with proper formatting
- Response handling
- Connection termination

### Server Implementation

The server implementation includes:
- Socket binding and listening
- Client connection acceptance
- Handshake process handling
- Message processing
- Multiple client management
- Connection termination handling

## Usage

### Starting the Server

```bash
python server.py [--host HOST] [--port PORT] [--max-size SIZE]
```

### Running the Client

```bash
python client.py [--server-addr ADDR] [--server-port PORT] [--operation-mode MODE]
```

## Example Communication Flow

1. Client initiates connection:
   ```
   CLIENT -> SERVER: SYN {operation_mode: "burst", max_packet_size: 1024, window_size: 5}
   ```

2. Server accepts and responds:
   ```
   SERVER -> CLIENT: SYN-ACK {status: "ok", session_id: "abc123", max_packet_size: 1024, operation_mode: "burst", window_size: 5}
   ```

3. Client acknowledges:
   ```
   CLIENT -> SERVER: ACK {session_id: "abc123"}
   ```

4. Data exchange:
   ```
   CLIENT -> SERVER: {type: 0x01, length: 11, payload: "Hello World"}
   SERVER -> CLIENT: {type: 0x02, sequence: 1}  # Acknowledgment
   ```

5. Connection termination:
   ```
   CLIENT -> SERVER: {type: 0x05}  # Disconnect request
   SERVER -> CLIENT: {type: 0x02}  # Acknowledgment
   ```

## Implementation Details

### Packet Structure Implementation

```python
def create_packet(message_type, payload, sequence_num=0):
    """
    Creates a packet with proper headers
    
    Args:
        message_type (int): Type of message (1=data, 2=ack, etc.)
        payload (bytes): Actual data
        sequence_num (int): Sequence number for ordering
        
    Returns:
        bytes: Complete packet
    """
    payload_length = len(payload)
    checksum = hashlib.md5(payload).digest()[:4]  # 4-byte checksum
    
    # Pack header: length (4 bytes) + type (1 byte) + seq (2 bytes) + checksum (4 bytes)
    header = struct.pack('!IBH4s', payload_length, message_type, sequence_num, checksum)
    
    # Complete packet = header + payload
    return header + payload
```

### Socket Implementation Example

```python
# Server socket creation
server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server_socket.bind((host, port))
server_socket.listen(5)

# Client socket creation
client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
client_socket.connect((server_host, server_port))
```

## Limitations and Future Improvements

- Current implementation doesn't handle network congestion
- No fragmentation/reassembly for large messages
- Limited error recovery mechanisms
- Could add encryption for secure communication
- Could implement reliability features like message reordering

## Contributing

Feel free to contribute to this project by implementing additional features or improving the existing protocol.
