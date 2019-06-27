import socket
import threading
import sys
import time
import os
from signed_blockchain import Blockchain
from transaction import Transaction, UnsignedTransaction, Input, Output
import utils
from signatures import *
from transaction_handler import Transaction_handler

# -> Enviar un mensaje
# <- Recibir un mensaje

VERSION_COMMAND = 'version.....'
VERACK_COMMAND = 'verack......'
TRANSACTION_COMMAND = 'transaction.'
BLOCK_COMMAND = 'block.......'
CREATE_BLOCK_COMMAND = 'create_block'
GETBLOCKS_COMMAND = 'getblocks...'
INV_COMMAND = 'inv.........'
GETDATA_COMMAND = 'getdata.....'
GETTXS_COMMAND = 'gettxs......'
NEWBLOCK_COMMAND = 'newblock....'
TX_COMMAND = 'tx..........'
GUI_COMMAND = 'gui.........'
CREATE_CONNECTION = 'connection..'
GUICLOSE_COMMAND = 'guiclose....'
DEFAULT_DATA_COMMAND = 'defaultdata.'
PAYCOINS_TYPE = 'p'
CREATECOINS_TYPE = 'c'


# TODO
MAX_BLOCKS_TO_SEND = 100
SECONDS_TO_ASK = 5
MAX_EVENTS_PRINTED = 50

metadata = lambda command, ip, port: f'{command}{ip}'.encode('utf-8') + port


class Node():
    def __init__(self, ip='0.0.0.0', port=8080, max_connections=5, conexions=[], version='1.0', user=''):
        # Create server socket
        self.keep_active = True
        self.user = user
        self.scrooge = load_pk('publickeyScrooge.pem')
        self.__events = []
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_socket.bind((ip, port))
        self.server_socket.listen(max_connections)
        self.listen_thread = threading.Thread(target=self.listen)
        self.listen_thread.start()

        self.peers = []
        self.txs_handler = Transaction_handler()
        self.ip = ip
        while len(self.ip) < 15:
            self.ip += ' '
        self.port = port
        self.metadata = lambda command: metadata(command, self.ip, self.port.to_bytes(4, 'little'))
        self.max_connections = max_connections
        self.version = version

        self.blockchain = Blockchain()

        self.__update_events(f'Server socket created and listening {ip}:{port}')

        # Load and establish conexions
        for conexion in conexions:
            self.send_conexion_handler(conexion)
            if conexion in self.peers:
                self.send_getblocks_handler(conexion)
                # self.send_gettxs_handler(conexion)

    def listen(self):
        while True:
            client_socket, client_address = self.server_socket.accept()
            self.message_handler(client_socket)

    def message_handler(self, client_socket):
        command_metadata = client_socket.recv(31)
        command, ip, port = command_metadata[:12].decode('utf-8'), command_metadata[12: 27].decode('utf-8').strip(), int.from_bytes(command_metadata[27:], 'little')
        self.__update_events(f'<- {command.strip(".").upper()} from node {ip, port}')
        if command == VERSION_COMMAND:
            self.receive_conexion_handler(client_socket)
        elif command == GUI_COMMAND:
            threading.Thread(target=self.gui_handler, args=(client_socket,)).start()
            return

        if (ip, port) not in self.peers:
            self.__update_events('Unknown node trying to send message')
            client_socket.close()
            return

        if command == GETBLOCKS_COMMAND:
            self.send_inv_handler(client_socket)
        elif command == GETDATA_COMMAND:
            self.send_block_handler(client_socket)
        elif command == BLOCK_COMMAND:
            self.receive_block_handler(client_socket)
        elif command == TX_COMMAND:
            self.receive_tx_handler(client_socket)
        else:
            client_socket.close()

    def receive_conexion_handler(self, client_socket):
        # Listen to rest of message
        payload = client_socket.recv(22)
        version, server_address, server_port, = utils.decode_version(payload)
        self.__update_events(f'Node trying to connect with version {version}, ip {server_address}, port {server_port}')

        if version != self.version:
            # Node with uncompatible version trying to connect
            self.__update_events(f'Node ({server_address}, {server_port}) with uncompatible version {version}. Rejected connection')
            client_socket.close()
            return

        if len(self.peers) == self.max_connections:
            # Node connected with max connections
            self.__update_events('Node with maximun connections limit. Rejected connection')
            client_socket.close()
            return

        self.send_verack_handler(client_socket)
        client_socket.close()
        self.__update_events(f'Node ({server_address}, {server_port}) compatible. Sending verack')

        # Check if node in peers, add to peers
        if (server_address, server_port) not in self.peers:
            self.send_conexion_handler((server_address, server_port))
            self.send_getblocks_handler((server_address, server_port))

    def send_conexion_handler(self, conexion):
        client_socket = utils.create_socket(conexion)

        # Send version message
        self.send_version_handler(client_socket)

        # Receive verack
        command_metadata = client_socket.recv(31)
        command = command_metadata[:12].decode('utf-8')
        if command != VERACK_COMMAND:
            # Message Received is not verack
            self.__update_events('Did not receive verack')
            client_socket.close()
            return

        # If verack Received, add conexion to peers
        self.peers.append(conexion)
        self.__update_events(f'<- {VERACK_COMMAND.strip(".").upper()} node {conexion} added to peers')

        # Close client socket
        client_socket.close()

    def send_getblocks_handler(self, conexion):
        client_socket = utils.create_socket(conexion)

        command = self.metadata(GETBLOCKS_COMMAND)
        client_socket.send(command)
        self.__update_events(f'-> {GETBLOCKS_COMMAND.strip(".").upper()} height: {self.current_height}')

        client_socket.send(self.current_height.to_bytes(4, 'little'))

        # Receive command
        command_metadata = client_socket.recv(31)
        command = command_metadata[:12].decode('utf-8')
        if command != INV_COMMAND:
            # Did not receive inventory
            self.__update_events('Did not receive inventory')
            client_socket.close()
            return
        self.__update_events(f'<- {INV_COMMAND.strip(".").upper()}')

        # Receive inv metadata
        inv_metadata = client_socket.recv(8)
        heigth, number_blocks_hashes = utils.decode_inv_metadata(inv_metadata)
        self.__update_events(f'Blockchain out of sync. Node height {self.current_height} and received heigth {heigth}. Receiving {number_blocks_hashes} blocks')

        # Receive inv blocks hashes
        block_hashes = []
        for _ in range(number_blocks_hashes):
            block_hash = client_socket.recv(64).decode('utf-8')
            block_hashes.append(block_hash)
        client_socket.close()

        for block_hash in block_hashes:
            self.send_getdata_handler(conexion, block_hash)

    def send_inv_handler(self, client_socket):
        # Height received from GETBLOCKS
        heigth = client_socket.recv(4)
        heigth = int.from_bytes(heigth, 'little')

        if heigth >= self.current_height:
            # Received a geater or equal blockchain heigth
            client_socket.close()
            return

        command = self.metadata(INV_COMMAND)
        client_socket.send(command)
        self.__update_events(f'-> {INV_COMMAND.strip(".").upper()}')
        payload = self.current_height.to_bytes(4, 'little')
        number_blocks_hashes = min(self.current_height - heigth, MAX_BLOCKS_TO_SEND)
        payload += number_blocks_hashes.to_bytes(4, 'little')
        self.__update_events(f'Peer Blockchain out of sync. Sending {number_blocks_hashes} blocks')

        # Iterate over blockchain to obtain desired block
        sent_blocks = 0
        while sent_blocks < number_blocks_hashes:
            current_block_hash = self.blockchain.head_block_hash
            current_block = self.blockchain.blocks[current_block_hash]
            for _ in range(self.current_height - sent_blocks - 2):
                current_block_hash = current_block.prev_hash
                current_block = self.blockchain.blocks[current_block_hash]
            # Stop iterating on the next block of the one to send, to obtain
            # prev_block_hash
            # Special case for the head node
            block_hash_to_send = current_block_hash
            payload += block_hash_to_send.encode('utf-8')
            sent_blocks += 1
            heigth += 1

        client_socket.send(payload)
        client_socket.close()

    def send_getdata_handler(self, conexion, block_hash):
        command = self.metadata(GETDATA_COMMAND)
        # Send getdata command
        client_socket = utils.create_socket(conexion)
        client_socket.send(command)
        self.__update_events(f'-> {GETDATA_COMMAND.strip(".").upper()} for block {block_hash}')
        payload = block_hash.encode('utf-8')
        client_socket.send(payload)

        # Check if Receive block command
        command_metadata = client_socket.recv(31)
        command = command_metadata[:12].decode('utf-8')
        if command != BLOCK_COMMAND:
            client_socket.close()
            return
        self.__update_events(f'<- {BLOCK_COMMAND.strip(".").upper()}')
        self.receive_block_handler(client_socket)

    def receive_block_handler(self, client_socket):
        block_metadata = client_socket.recv(132)
        block_hash, prev_block_hash, number_of_txs = utils.decode_block_metadata(block_metadata)
        self.__update_events(f'Received block {block_hash} with prev_block_hash {prev_block_hash} and number_of_txs {number_of_txs}')
        block_txs = []
        for _ in range(number_of_txs):
            transaction = utils.receive_tx_data(client_socket)
            block_txs.append(transaction)

        block = utils.create_block(block_txs, prev_block_hash)

        # Add block to blockchain
        self.add_block(block)
        client_socket.close()

    def send_block_handler(self, client_socket, block_hash=False):
        # Get block data from hash
        if not block_hash: block_hash = client_socket.recv(64).decode('utf-8')
        prev_block_hash, number_of_txs, block_txs = self.get_block_data(block_hash)

        command = self.metadata(BLOCK_COMMAND)
        client_socket.send(command)
        self.__update_events(f'-> {BLOCK_COMMAND.strip(".").upper()}')
        payload = block_hash.encode('utf-8') + prev_block_hash.encode('utf-8') + number_of_txs.to_bytes(4, 'little')
        client_socket.send(payload)
        self.__update_events(f'Sent block {block_hash} with prev_block_hash {prev_block_hash} and {number_of_txs} txs')
        for tx in block_txs:
            payload = tx
            client_socket.send(payload)
        client_socket.close()

    def new_block_handler(self, conexion, block_hash):
        # Create socket to send block to conexion
        client_socket = utils.create_socket(conexion)
        self.send_block_handler(client_socket, block_hash)

    def send_tx_handler(self, conexion, tx):
        client_socket = utils.create_socket(conexion)
        # Send tx command
        command = self.metadata(TX_COMMAND)
        client_socket.send(command)
        self.__update_events(f'-> {TX_COMMAND.strip(".").upper()} {{ id: {tx.txID} }}')
        payload = tx.serialize()
        client_socket.send(payload)
        client_socket.close()

    def receive_tx_handler(self, client_socket, tx_uniqueID=False):
        tx = utils.receive_tx_data(client_socket)
        self.add_tx(tx)
        client_socket.close()

    def get_block_data(self, block_hash):
        # Get prev_block_hash as 4 bytes
        block = self.blockchain.blocks[block_hash]
        prev_block_hash = block.prev_hash
        # Get amount of tx to send as 4 bytes
        number_of_txs = len(block.transactions)
        # Get transactions to send
        block_txs = block.serialize_transactions()
        return prev_block_hash, number_of_txs, block_txs

    def add_block(self, block):
        if not block.is_valid():
            self.__update_events('Trying to add invalid block')
            return

        if not self.txs_handler.validate_transactions(block):
            self.__update_events('Trying to add block with invalid txs')
            return

        # Try to add block to blockchain. If block already in blockchain,
        # block_hash is None
        added_block = self.blockchain.add_block(block)
        if added_block:
            self.txs_handler.process_transactions(block)
            self.__update_events(f'Block {added_block} added to blockchain')

            if self.peers:
                self.__update_events(f'Propagating block {added_block} to peers')
            # Propagate block to peers
            for conexion in self.peers:
                self.new_block_handler(conexion, added_block)
        else:
            self.__update_events(f'Block already in Blockchain')

    def add_tx(self, tx):
        was_added = self.txs_handler.add_to_transaction_pool(tx)
        if not was_added:
            self.__update_events(f'Transaction {tx.txID} already in outstanding_txs_pool')
            return False

        self.__update_events(f'Added tx {{ id: {tx.txID} }}')

        if self.peers:
            self.__update_events(f'Propagating tx {tx.txID} to peers')
        for conexion in self.peers:
            self.send_tx_handler(conexion, tx)

        return True

    def __create_create_coin(self):
        # Create coin transaction
        inputs = []
        outputs = [
            Output(50, utils.get_public_key(self.user)),
        ]
        unsigned = UnsignedTransaction(CREATECOINS_TYPE, inputs, outputs)
        to_sign = unsigned.DataForSigs()
        sigs = {}
        sigs[self.scrooge.export_key(format='DER')] = sign(to_sign, 'privatekeyScrooge.pem')
        transaction = Transaction(unsigned, sigs)
        return transaction

    def generate_new_block(self):
        txs = self.txs_handler.transaction_pool.copy()
        txs = [self.__create_create_coin()] + list(txs.values())

        block = utils.create_block(txs, self.blockchain.head_block_hash)
        self.add_block(block)

    @property
    def current_height(self):
        return len(self.blockchain.blocks)

    def send_version_handler(self, client_socket):
        # Send command version
        command = self.metadata(VERSION_COMMAND)
        client_socket.send(command)
        self.__update_events(f'-> {VERSION_COMMAND.strip(".").upper()}')

        # Send command version
        payload = self.version.encode('utf-8') + self.ip.encode('utf-8') + self.port.to_bytes(4, 'little')
        client_socket.send(payload)

    def send_verack_handler(self, client_socket):
        # Send command version
        command = self.metadata(VERACK_COMMAND)
        client_socket.send(command)
        self.__update_events(f'-> {VERACK_COMMAND.strip(".").upper()}')

    def print_outstanding_txs_pool(self):
        outstanding_txs_strings = [str(tx) for tx in self.txs_handler.transaction_pool.values()]
        return outstanding_txs_strings

    def gui_handler(self, client_socket: socket.socket):
        self.send_verack_handler(client_socket)

        keep_open = True
        while keep_open:
            command_metadata = client_socket.recv(31)
            command = command_metadata[:12].decode('utf-8')

            if command == TX_COMMAND:
                payload = len(self.txs_handler.UTXO_pool).to_bytes(4, 'little')
                for input_inst in self.txs_handler.UTXO_pool.values():
                    payload += input_inst.serialize()

                client_socket.send(payload)
                tx = utils.receive_tx_data(client_socket)
                self.add_tx(tx)

            elif command == CREATE_BLOCK_COMMAND:
                self.generate_new_block()

            elif command == CREATE_CONNECTION:
                connection_metadata = client_socket.recv(19)
                connection = connection_metadata[:15].decode('utf-8').strip(), int.from_bytes(connection_metadata[15:], 'little')
                self.send_conexion_handler(connection)
                if connection in self.peers:
                    self.send_getblocks_handler(connection)

            elif command == DEFAULT_DATA_COMMAND:
                addressA = load_pk('publickeyAlice.pem')
                addressB = load_pk('publickeyBob.pem')
                addressC = load_pk('publickeyCharlie.pem')
                scrooge = load_pk('publickeyScrooge.pem')

                transactions = []

                # Create coin transaction
                inputs = []
                outputs = [
                    Output(11, addressA),  # Alice has 10 scrooge coins
                    Output(10, addressB),  # Alice has 10 scrooge coins
                ]
                unsigned = UnsignedTransaction(CREATECOINS_TYPE, inputs, outputs)
                to_sign = unsigned.DataForSigs()
                sigs = {}
                sigs[scrooge.export_key(format='DER')] = sign(to_sign, 'privatekeyScrooge.pem')
                transaction = Transaction(unsigned, sigs)
                self.add_tx(transaction)
                transactions.append(transaction)

                # Create block
                block = utils.create_block(
                    transactions,
                    self.blockchain.head_block_hash,
                )
                time.sleep(1)
                self.add_block(block)
                continue
                transactions = []

                # Pay coins transaction
                inputs = [
                    Input(transaction.txID, 10, addressA),
                    Input(transaction.txID, 10, addressB),  # Both spend their 10 scrooge coins
                ]
                outputs = [
                    Output(5, addressA),  # Alice has 5 scrooge coins
                    Output(15, addressB),  # Bob has 15 scrooge coins
                ]
                unsigned = UnsignedTransaction(PAYCOINS_TYPE, inputs, outputs)
                to_sign = unsigned.DataForSigs()
                sigs = {}
                sigs[addressA.export_key(format='DER')] = sign(to_sign, 'privatekeyAlice.pem')
                sigs[addressB.export_key(format='DER')] = sign(to_sign, 'privatekeyBob.pem')
                transaction = Transaction(unsigned, sigs)
                self.add_tx(transaction)
                transactions.append(transaction)

                # Create block
                block = utils.create_block(
                    transactions,
                    self.blockchain.head_block_hash,
                )
                self.add_block(block)

            elif command == GUICLOSE_COMMAND:
                keep_open = False

        client_socket.close()

    def __update_events(self, event=None):
        os.system('cls' if os.name == 'nt' else 'clear')
        _, columns = os.popen('stty size', 'r').read().split()

        print('=' * int(columns))
        if event:
            self.__events.append(event)

        print('Events')
        print('\t' + self.__events[0])
        if len(self.__events) > MAX_EVENTS_PRINTED:
            print('\t...')
        for event in self.__events[1:][-MAX_EVENTS_PRINTED:]:
            print('\t' + event)
        print('\n')

        self.blockchain.print_blockchain()
        print('\n')

        otxp = self.print_outstanding_txs_pool()
        print('Outstanding Txs Pool')
        for otx in otxp:
            print('\t' + otx)
        if not otxp:
            print('\tEmpty')

if __name__ == '__main__':
    ip = sys.argv[1]
    port = sys.argv[2]
    version = sys.argv[3]
    user = sys.argv[4]
    conexions = []
    for ind in range(0, len(sys.argv[5:]), 2):
        conexions.append((sys.argv[ind + 5], int(sys.argv[ind + 6])))

    n = Node(
        ip=ip,
        port=int(port),
        conexions=conexions,
        version=version,
        user=user,
    )
