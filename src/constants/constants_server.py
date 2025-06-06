# constants_server.py

# Server log and error messages
class SERVER_LOGS:
    START = '[LOG] Server started on {host}:{port}'
    PROTOCOL = '[LOG] Protocol: {protocol}, Max fragment size: {max_fragment_size} characters'
    WINDOW = '[LOG] Window size: {window_size} packets'
    NEW_CONNECTION = '[LOG] New connection from: {client_address}'
    HANDSHAKE_COMPLETE = '[LOG] Handshake completed with {client_address}'
    HANDSHAKE_FAILED = '[ERROR] Handshake failed with {client_address}'
    SOCKET_CLOSED = '[LOG] Server socket closed'
    CLIENT_DISCONNECTED = '[LOG] Client {client_address} disconnected successfully.'
    CONNECTION_CLOSED = '[LOG] Connection with {client_address} closed.'
    CHANNEL_CONFIG = '[CONFIG] Channel conditions updated on server.'
    WINDOW_GBN = '[WINDOW] GBN Window: [{start}-{end}]'
    WINDOW_SR = '[WINDOW] SR Window: [{start}-{end}]'
    WINDOW_BUFFERED = '[WINDOW] Buffered packets: {buffered}'
    RECONSTRUCTED = '[RECONSTRUCTED] Full message from {client_address}: {full_message}'
    RECONSTRUCTED_BIN = '[RECONSTRUCTED] Received binary fragments from {client_address} (not shown as text)'

class SERVER_ERRORS:
    INVALID_HEADER = '[ERROR] Invalid header received from {client_address}'
    PARSE_PACKET = '[ERROR] Failed to parse packet from {client_address}'
    EXPECTED_SYN = '[ERROR] Expected SYN but got message type {msg_type}'
    EXPECTED_ACK = '[ERROR] Expected HANDSHAKE_ACK but got message type {msg_type}'
    FAILED_ACK = '[ERROR] Failed to receive ACK from {client_address}'
    ERROR_HANDSHAKE = '[ERROR] Error in handshake with {client_address}: {error}'
    SERVER_ERROR = '[ERROR] Server error: {error}'
    INCOMPLETE_HEADER = '[ERROR] Incomplete or missing header from {client_address}'
    UNPACK_HEADER = '[ERROR] Failed to unpack header from {client_address}: {error}'
    INCOMPLETE_PAYLOAD = '[ERROR] Incomplete payload received from {client_address}'
    PARSE_CONFIG = '[ERROR] Failed to parse channel config: {error}'
    CHECKSUM_MISMATCH = '[ERROR] Checksum mismatch for packet {sequence_num} from {client_address}'
    UNKNOWN_TYPE = '[ERROR] Unknown message type {message_type} from {client_address}'
    ERROR_HANDLING = '[ERROR] Error handling messages from {client_address}: {error}'
    FAILED_CLOSE = '[ERROR] Failed to close connection with {client_address}: {error}'
    CHECKSUM_VERIFICATION = '[ERROR] Checksum verification failed!'
