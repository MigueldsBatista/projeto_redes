import socketio
import requests
import time

# Connection parameters
connection_params = {
    "operation_mode": "text",
    "max_size": 1024
}

sio = socketio.Client()
handshake_complete = False

@sio.event
def connect():
    print('Connected to server')
    # Step 1: SYN - Send initial connection request with parameters
    print('Sending SYN...')
    sio.emit('SYN', connection_params, callback=handle_syn_ack)

def handle_syn_ack(data):
    # Step 2: Process SYN-ACK from server
    print(f'Received SYN-ACK: {data}')
    
    if data.get('status') != 'ok':
        print(f'Handshake failed: {data.get("message", "Unknown error")}')
        return

    # Step 3: ACK - Send final acknowledgment
    print('Sending ACK...')
    sio.emit('handshake_response', {'message': 'Connection established'})
    
    global handshake_complete
    handshake_complete = True
    print('Handshake complete!')

# Example of listening for a specific event from the server
@sio.on('server_message')
def on_server_message(data):
    print(f'Received message from server: {data}')

@sio.event
def disconnect():
    print('Disconnected from server')

if __name__ == '__main__':
    sio.connect('http://localhost:5000')
    
    # Wait for handshake to complete
    retry_count = 0
    while not handshake_complete and retry_count < 5:
        time.sleep(0.5)
        retry_count += 1
    
    if not handshake_complete:
        print("Handshake failed to complete in time")
        sio.disconnect()
        exit(1)
    
    # Continuous message sending loop
    print("Enter messages (type 'exit' to quit):")
    while True:
        message = input('Message: ')
        
        if message.lower() == 'exit':
            break
                
        if len(message.encode()) > connection_params["max_size"]:
            print(f"Message exceeds maximum size of {connection_params['max_size']} bytes")
            continue

        # 'message' is the event name that the server will listen for
        sio.emit('message', message)
        
        # Short delay to prevent flooding
        time.sleep(0.1)
    
    print("Disconnecting from server...")
    sio.disconnect()