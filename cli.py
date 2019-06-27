import click
import re
import socket
import os
import utils

from whaaaaat import prompt
from node import metadata, GUI_COMMAND, VERACK_COMMAND, TX_COMMAND,\
                    CREATE_BLOCK_COMMAND, BLOCK_COMMAND, CREATE_CONNECTION, \
                    GUICLOSE_COMMAND, DEFAULT_DATA_COMMAND
from transaction import Output, Transaction, UnsignedTransaction, PAYCOINS_TYPE
from signatures import load_pk, sign

SELECTED_ACTION = 'selected_action'
TX_ID = 'tx_id'
INPUT_INDEX = 'input_idx'
TX_VALUE = 'tx_value'
IP_INPUT = 'ip'
PORT_INPUT = 'port'

CREATE_CONNECTION_ACTION = 'Crear conexión'
CREATE_TX_ACTION = 'Crear transacción'
CREATE_BLOCK_ACTION = 'Crear bloque'
CREATE_DEFAULT_DATA_ACTION = 'Crear 5 bloques'
CLOSE_CLI_ACTION = 'Cerrar GUI'

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


def create_and_send_tx(client_socket: socket.socket, user):
    sender = utils.get_public_key(user)
    command = gui_metadata(TX_COMMAND)
    client_socket.send(command)

    inputs = []
    N_inputs = int.from_bytes(client_socket.recv(4), 'little')
    for _ in range(N_inputs):
        input_data = client_socket.recv(159)
        inputs.append(utils.decode_input(input_data))

    input_choices = [
        {
            'name': f'txID: {input.where_created} value: {input.value}',
        }
        for index, input in enumerate(inputs)
    ]

    recipient_choices = [
        {
            'name': 'Alice',
        }, {
            'name': 'Bob',
        }, {
            'name': 'Charlie',
        }, {
            'name': 'No more pays',
        },
    ]

    actions = [{
        'type': 'checkbox',
        'name': INPUT_INDEX,
        'message': 'Selecciona los inputs a ingresar en la transacción',
        'choices': input_choices,
    }]

    recipient_actions = [{
        'type': 'list',
        'name': 'recipient',
        'message': 'Selecciona a la persona que le pagarás',
        'choices': recipient_choices,
    }]

    value_actions = [{
        'type': 'input',
        'name': 'value',
        'message': '¿Cuánto le vas a pagar?',
    }]

    answers = prompt(actions)
    inputs_selected = answers.get(INPUT_INDEX)
    inputs_to_pay = []
    for inputs_selected in inputs_selected:
        index = input_choices.index({'name': inputs_selected})
        inputs_to_pay.append(inputs[index])

    outputs = []
    while True:
        answers = prompt(recipient_actions)
        answer = answers['recipient']
        if answer == 'No more pays':
            break

        recipient = utils.get_public_key(answer)
        answers = prompt(value_actions)
        value = int(answers['value'])
        output = Output(value, recipient)
        outputs.append(output)

    unsigned = UnsignedTransaction(PAYCOINS_TYPE, inputs_to_pay, outputs)
    to_sign = unsigned.DataForSigs()
    signs = {}
    signs[sender.export_key(format='DER')] = sign(to_sign, utils.get_private_key(user))
    transaction = Transaction(unsigned, signs)
    client_socket.send(transaction.serialize())


def create_and_send_block(client_socket: socket.socket):
    # command = gui_metadata(CREATE_BLOCK_COMMAND)
    # client_socket.send(command)

    # number_of_txs = int.from_bytes(client_socket.recv(4), 'little')

    # if number_of_txs == 0:
    #     print('There are no transactions to create block')
    #     return

    # txs = []
    # for _ in range(number_of_txs):
    #     tx_id = int.from_bytes(client_socket.recv(4), 'little')
    #     tx_value = int.from_bytes(client_socket.recv(4), 'little')
    #     txs.append((tx_id, tx_value))

    # choices = [{
    #         'name': f'Tx ID: {tx_id}, Value: {tx_value}',
    #         'value': (tx_id, tx_value)
    #     }
    #     for tx_id, tx_value in txs
    # ]

    # actions = [{
    #     'type': 'checkbox',
    #     'name': INPUT_INDEX,
    #     'message': 'Selecciona las transacciones a ingresar en el bloque',
    #     'choices': choices,
    # }]

    # answers = prompt(actions)
    # txs_selected = answers.get(INPUT_INDEX)

    # command = gui_metadata(BLOCK_COMMAND)
    command = gui_metadata(CREATE_BLOCK_COMMAND)
    client_socket.send(command)

    # paylaod = len(txs_selected).to_bytes(4, 'little')  # Number of txs in block
    # for tx_selected in txs_selected:
    #     tx_id, tx_value = list(filter(lambda tx: tx['name'] == tx_selected, choices))[0]['value']
    #     paylaod += tx_id.to_bytes(4, 'little')
    #     paylaod += tx_value.to_bytes(4, 'little')
    # client_socket.send(paylaod)


def create_and_send_connection(client_socket: socket.socket):
    command = gui_metadata(CREATE_CONNECTION)
    client_socket.send(command)

    questions = [{
        'type': 'input',
        'name': IP_INPUT,
        'message': 'Ingresa la IP del nodo a agregar'
    }, {
        'type': 'input',
        'name': PORT_INPUT,
        'message': 'Ingresa el puerto del nodo a agregar'
    }]

    answers = prompt(questions)
    ip = answers[IP_INPUT]
    port = int(answers[PORT_INPUT])

    while len(ip) < 15:
        ip += ' '

    payload = ip.encode('utf-8')
    payload += port.to_bytes(4, 'little')
    client_socket.send(payload)


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
@click.option(
    '-u', '--user',
    type=click.Choice(['Alice', 'Bob', 'Charlie']),
    default='Alice',
    help='Node\'s user key file to sign transactions'
)
def main(host, port, user):
    try:
        client_socket = connect_to_node((host, port))
    except:
        print('It couldn\'t connect to node')
        return

    keep_open = True
    while keep_open:
        actions = [{
            'type': 'list',
            'name': SELECTED_ACTION,
            'message': '¿Qué deseas hacer?',
            'choices': [
                CREATE_CONNECTION_ACTION,
                CREATE_TX_ACTION,
                CREATE_BLOCK_ACTION,
                CREATE_DEFAULT_DATA_ACTION,
                CLOSE_CLI_ACTION,
            ],
        }]

        answer = None
        while not answer:
            os.system('cls' if os.name == 'nt' else 'clear')
            answer = prompt(actions).get(SELECTED_ACTION)

        if answer == CREATE_TX_ACTION:
            create_and_send_tx(client_socket, user)
        elif answer == CREATE_BLOCK_ACTION:
            create_and_send_block(client_socket)
        elif answer == CREATE_CONNECTION_ACTION:
            create_and_send_connection(client_socket)
        elif answer == CREATE_DEFAULT_DATA_ACTION:
            command = gui_metadata(DEFAULT_DATA_COMMAND)
            client_socket.send(command)
        else:
            command = gui_metadata(GUICLOSE_COMMAND)
            client_socket.send(command)
            keep_open = False

    client_socket.close()

if __name__ == '__main__':
    main()
