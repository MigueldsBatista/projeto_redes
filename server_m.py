import eventlet
import socketio

# Default parameters
DEFAULT_MAX_SIZE = 1024

DEFAULT_MODE = "text"

# Client connection tracking
client_sessions = {}

sio = socketio.Server()
app = socketio.WSGIApp(sio, static_files={
    '/': {'content_type': 'text/html', 'filename': 'index.html'}
})

@sio.event
def connect(sid, environ):
    print(f'Client connected: {sid}')
    client_sessions[sid] = {
        'connected': True,
        'handshake_complete': False
    }

@sio.event
def SYN(sid, data):
    # Step 2: SYN-ACK - Server receives SYN and responds with SYN-ACK
    print(f'Received SYN from {sid}: {data}')
    
    # Validate connection parameters
    operation_mode = data.get('operation_mode', DEFAULT_MODE)

    if operation_mode != 'text':
        print(f'Invalid operation mode from {sid}: {operation_mode}')
        return {
            'status': 'error',
            'message': 'Invalid operation mode'
        }

    requested_max_size = data.get('max_size', DEFAULT_MAX_SIZE)
    
    # Apply server-side limits if needed
    max_size = min(requested_max_size, DEFAULT_MAX_SIZE)
    
    # Store session parameters
    client_sessions[sid].update({
        'operation_mode': operation_mode,
        'max_size': max_size
    })
    
    # Return SYN-ACK with negotiated parameters
    return {
        'status': 'ok',
        'operation_mode': operation_mode,
        'max_size': max_size,
        'message': 'SYN-ACK: Parameters accepted'
    }

@sio.event
def handshake_response(sid, data):
    # Step 3: Server receives final ACK
    print(f'Received ACK from {sid}: {data}')
    client_sessions[sid]['handshake_complete'] = True
    print(f'Handshake completed for client {sid}')

@sio.event
def message(sid, data):
    # Check if handshake is complete
    if not client_sessions.get(sid, {}).get('handshake_complete', False):
        print(f'Rejected message from {sid}: Handshake not complete')
        return

    # Check message size
    max_size = client_sessions[sid].get('max_size', DEFAULT_MAX_SIZE)
    if isinstance(data, str) and len(data.encode()) > max_size:
        print(f'Rejected message from {sid}: Size exceeds limit of {max_size} bytes')
        return
    
    print(f'Received message from {sid}: {data}')
    # Process message...

@sio.event
def disconnect(sid):
    print(f'Client disconnected: {sid}')
    if sid in client_sessions:
        del client_sessions[sid]

if __name__ == '__main__':
    print('Server starting on port 5000...')

    eventlet.wsgi.server(eventlet.listen(('', 5000)), app)