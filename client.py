import socketio
import requests

# handshake

# modo de operação: http
# tamanho maximo

#bloquear se passar do tamanho maximo

socketIo = socketio.Client()

#SYN # manda mensagem
#SYN-ACK # rebeci a mensagem e estou esperando a resposta
#ACK # resposta do cliente

# Parâmetros do handshake
handshake_data = {
    "operation_mode": "texto",  # Exemplo: 'texto' ou 'binário'
    "max_size": 1024        # Tamanho máximo em bytes
}

@socketIo.event('handshake_response')
def connect():
    print('connection established')
    socketIo.emit('handshake', handshake_data)

@socketIo.on('handshake_response')
def handshake_response(data):
    print('Resposta do handshake recebida:', data)
    
    if data.get('status') != 'ok':
        print('Handshake rejeitado ou parâmetros alterados. Verifique a configuração.')
    else:
        print('Handshake confirmado. Comunicação estabelecida com as regras definidas.')

@socketIo.event
def my_message(data):
    print('message received with ', data)
    socketIo.emit('my response', {'response': 'my response'})

@socketIo.event
def disconnect():
    print('disconnected from server')


if __name__ =='__main__':
    socketIo.connect('http://localhost:5000')
    
    try:
        while True:
            message = input('message: ')
            if len(message.encode()) > handshake_data["max_size"]:
                print("Erro: A mensagem excede o tamanho máximo permitido!")
                continue
            socketIo.emit('SYN', message)
    except KeyboardInterrupt:
        print("Exiting...")
    finally:
        socketIo.disconnect()

