import click
import re
import socket

from whaaaaat import prompt
from node import metadata, GUI_COMMAND, VERACK_COMMAND, TX_COMMAND

SELECTED_ACTION = 'selected_action'
TX_ID = 'tx_id'
TX_VALUE = 'tx_value'
CREATE_TX = 'Crear transacción'
CREATE_BLOCK = 'Crear bloque'
CLOSE_CLI = 'Cerrar GUI'

gui_metadata = lambda command: metadata(command, '.' * 15, b'.' * 4)


def validate_ip(ctx, param, value):
    found = re.search('^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$', value)
    if found:
        return value
    else:
        click.BadParameter('Invalid IP')


def connect_to_node(connection):
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client_socket.connect(connection)

    command_metadata = gui_metadata(GUI_COMMAND)
    client_socket.send(command_metadata)

    command_metadata = client_socket.recv(31)
    command = command_metadata[:12].decode('utf-8')
    if command != VERACK_COMMAND:
        # Message Received is not verack
        print('Did not receive verack')
        client_socket.close()
        raise Exception()

    print('Connected successfully to node')
    return client_socket


def create_tx(client_socket: socket.socket):
    questions = [{
        'type': 'input',
        'name': TX_ID,
        'message': 'Ingresa el ID de la transacción a agregar'
    }, {
        'type': 'input',
        'name': TX_VALUE,
        'message': 'Ingresa el valor de la transacción a agregar'
    }]

    answers = prompt(questions)
    tx_id = int(answers[TX_ID])
    tx_value = int(answers[TX_VALUE])

    command = gui_metadata(TX_COMMAND)
    client_socket.send(command)

    payload = tx_id.to_bytes(4, 'little')
    payload += tx_value.to_bytes(4, 'little')
    client_socket.send(payload)

    wasAddedByte = client_socket.recv(1)
    wasAdded = bool.from_bytes(wasAddedByte, 'little')

    if wasAdded:
        print('Transacción agregada con éxito')
    else:
        print('Transacción no pudo ser agregada')


@click.command()
@click.option(
    '-h', '--host',
    type=str,
    default='0.0.0.0',
    callback=validate_ip,
    help='Node\'s IP to connect',
)
@click.option(
    '-p', '--port',
    type=int,
    default=8080,
    help='Node\'s port to connect',
)
def main(host, port):
    try:
        client_socket = connect_to_node((host, port))
    except:
        print('It couldn\'t connect to node')
        return

    actions = [{
        'type': 'list',
        'name': SELECTED_ACTION,
        'message': '¿Qué deseas hacer?',
        'choices': [CREATE_TX, CREATE_BLOCK, CLOSE_CLI]
    }]

    answer = None
    while not answer:
        answer = prompt(actions).get(SELECTED_ACTION)

    if answer == CREATE_TX:
        create_tx(client_socket)
    elif answer == CREATE_BLOCK:
        pass

    client_socket.close()

if __name__ == '__main__':
    main()
