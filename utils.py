from transaction import Input, Output
from signed_blockchain import Block
from hash import hash
from Crypto.PublicKey import ECC
import socket


def create_socket(conexion):
    # Create client socket
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    # Connect to conexion
    client_socket.connect(conexion)
    return client_socket


def decode_version(payload):
    version = payload[:3].decode('utf-8')
    server_address = payload[3:18].decode('utf-8').strip()
    server_port = int.from_bytes(payload[18: 22], 'little')
    return version, server_address, server_port


def decode_inv_metadata(payload):
    heigth = int.from_bytes(payload[:4], 'little')
    number_of_hashes = int.from_bytes(payload[4:8], 'little')
    return heigth, number_of_hashes


def decode_block_metadata(payload):
    block_hash = payload[:64].decode('utf-8')
    prev_block_hash = payload[64:128].decode('utf-8')
    number_of_tx = int.from_bytes(payload[128:], 'little')
    return block_hash, prev_block_hash, number_of_tx


def decode_tx_metadata(payload):
    txID = payload[:64].decode('utf-8')
    type = payload[64:65].decode('utf-8')
    N_inputs = int.from_bytes(payload[65:69], 'little')
    N_outputs = int.from_bytes(payload[69:73], 'little')
    N_sigs = int.from_bytes(payload[73:], 'little')
    return txID, type, N_inputs, N_outputs, N_sigs


def decode_input(payload):
    where_created = payload[:64].decode('utf-8')
    value = int.from_bytes(payload[64: 68], 'little')
    owner = ECC.import_key(payload[68:])
    return Input(where_created, value, owner)


def decode_output(payload):
    value = int.from_bytes(payload[:4], 'little')
    recipient = ECC.import_key(payload[4:])
    return Output(value, recipient)


def decode_signs(payload):
    addr = payload[:91]
    key = payload[91:]
    return addr, key


def create_block(transactions, prev_hash):
    return Block(transactions, prev_hash)


def decode_inv_block_hashes(payload, number_of_hashes):
    block_hashes = [payload[i * 64 : (i + 1) * 64] for i in range(number_of_hashes)]
    return block_hashes
