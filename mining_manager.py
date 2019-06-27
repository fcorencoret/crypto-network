import os
import click

from whaaaaat import prompt
from cli import connect_to_node, gui_metadata,\
    create_and_send_block, GUICLOSE_COMMAND
from random import uniform
from time import sleep

MAIN_ACTION = 'main'

ADD_NODE = 'Agregar nodo'
MINE = 'Realizar mineo'


def add_node():
    actions = [{
        'type': 'input',
        'name': 'node_port',
        'message': 'Ingresa el puerto del nodo'
    }, {
        'type': 'input',
        'name': 'node_prob',
        'message': 'Ingresa el poder computaciónal del nodo (entre 0 y 1)'
    }]

    answers = prompt(actions)
    port = int(answers.get('node_port'))
    prob = float(answers.get('node_prob'))
    return port, prob


def mine(tuples):
    max_prob = sum(prob for _, prob in tuples)
    random_num = uniform(0, max_prob)

    acc = 0
    for port, prob in tuples:
        acc += prob
        if random_num < acc:
            send_mine_message(('0.0.0.0', port))
            return


def send_mine_message(connexion):
    try:
        client_socket = connect_to_node(connexion)
    except:
        print('It couldn\'t connect to node')
        return

    create_and_send_block(client_socket)
    command = gui_metadata(GUICLOSE_COMMAND)
    client_socket.send(command)
    client_socket.close()


@click.command()
def main():
    ports = []
    actions = [{
        'type': 'list',
        'name': MAIN_ACTION,
        'message': '¿Qué deseas hacer?',
        'choices': [
            ADD_NODE,
            MINE,
            'Mostrar nodos',
            'Cerrar'
        ],
    }]

    keep_open = True
    while keep_open:
        answer = None
        while not answer:
            os.system('cls' if os.name == 'nt' else 'clear')
            answer = prompt(actions).get(MAIN_ACTION)

        if answer == ADD_NODE:
            port, prob = add_node()
            ports.append((port, prob))
        elif answer == MINE:
            mine(ports)
        elif answer == 'Mostrar nodos':
            for port, prob in ports:
                click.echo(f'Port: {port} Prob: {prob}')
            sleep(5)
        else:
            keep_open = False


if __name__ == '__main__':
    main()
