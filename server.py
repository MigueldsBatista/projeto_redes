# Apply eventlet monkey patch before any other imports
import eventlet

eventlet.monkey_patch()

import socketio


class Server:
    # Default parameters

    def __init__(self, host='', max_size=1024, operation_mode='text', port=5000):
        # Server setup
        self.host = host
        self.port = port
        self.operation_mode = operation_mode
        self.max_size = max_size

        # Client connection tracking
        self.client_sessions = {}
        
        # SocketIO setup
        self.sio = socketio.Server(cors_allowed_origins='*')  # Add CORS support
        self.app = socketio.WSGIApp(self.sio, static_files={
            '/': {'content_type': 'text/html', 'filename': 'index.html'}
        })
        
        # Register event handlers
        self.register_handlers()
    
    def register_handlers(self):
        """Register all event handlers with the SocketIO server"""
        self.sio.on('connect', self.on_connect)
        self.sio.on('disconnect', self.on_disconnect)
        self.sio.on('SYN', self.on_syn)
        self.sio.on('handshake_response', self.on_handshake_response)
        self.sio.on('message', self.on_message)
    
    def on_connect(self, sid, environ):
        """Handle client connection"""
        print(f'Client connected: {sid}')
        self.client_sessions[sid] = {
            'connected': True,
            'handshake_complete': False
        }
    
    def on_syn(self, sid, data):
        """Handle SYN request from client (Step 2 of handshake)"""
        print(f'Received SYN from {sid}: {data}')
        
        # Validate connection parameters
        operation_mode = data.get('operation_mode', self.operation_mode)

        if operation_mode != 'text':
            print(f'Invalid operation mode from {sid}: {operation_mode}')
            return {
                'status': 'error',
                'message': 'Invalid operation mode'
            }

        requested_max_size = data.get('max_size', self.max_size)
        
        # Apply server-side limits if needed
        max_size = min(requested_max_size, self.max_size)
        
        # Store session parameters
        self.client_sessions[sid].update({
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
    
    def on_handshake_response(self, sid, data):
        """Handle final ACK from client (Step 3 of handshake)"""
        print(f'Received ACK from {sid}: {data}')
        self.client_sessions[sid]['handshake_complete'] = True
        print(f'Handshake completed for client {sid}')
    
    def on_message(self, sid, data):
        # Check if handshake is complete
        if not self.client_sessions.get(sid, {}).get('handshake_complete', False):
            print(f'Rejected message from {sid}: Handshake not complete')
            return

        # Check message size
        max_size = self.client_sessions[sid].get('max_size', self.max_size)
        if isinstance(data, str) and len(data.encode()) > max_size:
            print(f'Rejected message from {sid}: Size exceeds limit of {max_size} bytes')
            return
        
        print(f'Received message from {sid}: {data}')
        # Process message...
    
    def on_disconnect(self, sid):
        print(f'Client disconnected: {sid}')
        if sid in self.client_sessions:
            del self.client_sessions[sid]
    
    def start(self):
        print(f'Server starting on port {self.port}...')
        eventlet.wsgi.server(eventlet.listen((self.host, self.port)), self.app)


if __name__ == '__main__':
    server = Server()
    server.start()