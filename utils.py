from transaction import Input, Output
from signed_blockchain import Block
from hash import hash
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
    block_hash, prev_block_hash, number_of_tx = payload[:64].decode('utf-8'), payload[64:128].decode('utf-8'), int.from_bytes(payload[128:], 'little')
    return block_hash, prev_block_hash, number_of_tx

def decode_tx_metadata(payload):
    txID, type, N_inputs, N_outputs, N_sigs = payload[:32], payload[32].decode('utf-8'), int.from_bytes(payload[33:37], 'little'), int.from_bytes(payload[37:41], 'little'), int.from_bytes(payload[41:], 'little')
    return txID, type, N_inputs, N_outputs, N_sigs

def decode_input(payload):
    where_created, value, owner = payload[:32], int.from_bytes(payload[32: 36], 'little'), payload[36:]
    return Input(where_created, value, owner)

def decode_output(payload):
    value, recipient = int.from_bytes(payload[:4], 'little'), payload[4:]
    return Output(vale, recipient)

def decode_signs(payload):
    addr, key = payload[:200], payload[200:]
    return addr, key

def create_block(transactions, prev_hash):
    return Block(transactions, prev_hash)

def decode_inv_block_hashes(payload, number_of_hashes):
    block_hashes = [payload[i * 64 : (i + 1) * 64] for i in range(number_of_hashes)]
    return block_hashes