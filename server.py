import eventlet
import socketio

MAX_SIZE = 1024

socketIo = socketio.Server()
app = socketio.WSGIApp(socketIo, static_files={
    '/': {'content_type': 'text/html', 'filename': 'index.html'}
})

@socketIo.event
def connect(client_id, env):#client_id é o id do cliente
    print('connect ', client_id)
    print(f"PROTOCOL: {env['SERVER_PROTOCOL']}")

@socketIo.event
def handshake(client_id, data):
    """
    Evento para processar o handshake inicial.
    O cliente deve enviar um dicionário contendo:
        - operation_mode: Ex.: 'texto' ou 'binário'
        - max_size: Tamanho máximo em bytes que deseja utilizar
    """
    print(f"Handshake recebido do cliente {client_id}: {data}")
    # Verifica se o parâmetro 'max_size' enviado pelo cliente não excede o permitido pelo servidor
    client_max_size = data.get('max_size', MAX_SIZE)
    if client_max_size > MAX_SIZE:
        # Se exceder, envia resposta de erro
        socketIo.emit('handshake_response',
                      {'status': 'error', 'message': 'Tamanho máximo excedido'},
                      room=client_id)
        print(f"Handshake rejeitado para o cliente {client_id}: Tamanho máximo excedido")
    else:
        # Se os parâmetros estiverem corretos, envia confirmação
        socketIo.emit('handshake_response',
                      {'status': 'ok', 'message': 'SYN + ACK'},
                      room=client_id)
        print(f"Handshake aceito para o cliente {client_id}")

@socketIo.event
def my_message(client_id, data):

    if len(data) > MAX_SIZE:
        print('message too big')
        socketIo.emit('error_message',
                      {'status': 'error', 'message': 'Mensagem excede o tamanho máximo'},
                      room=client_id)
        return

@socketIo.event
def disconnect(client_id):
    print('disconnect ', client_id)

if __name__ == '__main__':
    eventlet.wsgi.server(eventlet.listen(('', 5000)), app)