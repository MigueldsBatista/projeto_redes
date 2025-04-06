import socketio
import requests
import time


class Client:
    def __init__(self, server_url='http://127.0.0.1:5000', operation_mode='text', max_size=1024):
        # Connection parameters
        self.connection_params = {
            "operation_mode": operation_mode,
            "max_size": max_size
        }
        
        self.server_url = server_url
        self.sio = socketio.Client()
        self.handshake_complete = False
        
        # Set up event handlers
        self.sio.on('connect', self.on_connect)
        self.sio.on('disconnect', self.on_disconnect)
        self.sio.on('server_message', self.on_server_message)
    
    def on_connect(self):
        print('Connected to server')
        # Step 1: SYN - Send initial connection request with parameters
        print('Sending SYN...')
        self.sio.emit('SYN', self.connection_params, callback=self.handle_syn_ack)
    
    def handle_syn_ack(self, data):
        # Step 2: Process SYN-ACK from server
        print(f'Received SYN-ACK: {data}')
        
        if data.get('status') != 'ok':
            print(f'Handshake failed: {data.get("message", "Unknown error")}')
            return

        # Step 3: ACK - Send final acknowledgment
        print('Sending ACK...')
        self.sio.emit('handshake_response', {'message': 'Connection established'})
        
        self.handshake_complete = True
        print('Handshake complete!')
    
    def on_server_message(self, data):
        print(f'Received message from server: {data}')
    
    def on_disconnect(self):
        print('Disconnected from server')
    
    def connect(self):
        self.sio.connect(self.server_url)
        
        # Wait for handshake to complete
        retry_count = 0
        while not self.handshake_complete and retry_count < 5:
            time.sleep(0.5)
            retry_count += 1
        
        if not self.handshake_complete:
            print("Handshake failed to complete in time")
            self.sio.disconnect()
            return False
            
        return True
    
    def send_message(self, message):
        if len(message.encode()) > self.connection_params["max_size"]:
            print(f"Message exceeds maximum size of {self.connection_params['max_size']} bytes")
            return False
            
        # 'message' is the event name that the server will listen for
        self.sio.emit('message', message)
        
        # Short delay to prevent flooding
        time.sleep(0.1)
        return True
    
    def disconnect(self):
        print("Disconnecting from server...")
        self.sio.disconnect()
    
    def run_interactive_session(self):
        if not self.connect():
            return
            
        # Continuous message sending loop
        print("Enter messages (type 'exit' to quit):")
        while True:
            message = input('Message: ')
            
            if message.lower() == 'exit':
                break
                    
            self.send_message(message)
        
        self.disconnect()


if __name__ == '__main__':
    client = Client()
    client.run_interactive_session()