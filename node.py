import socket
import threading
import sys
import time
from blockchain import Blockchain

VERSION_COMMAND = 'version.....'
VERACK_COMMAND = 'verack......'
TRANSACTION_COMMAND = 'transaction.'
BLOCK_COMMAND = 'block.......'
GETBLOCKS_COMMAND = 'getblocks...'
INV_COMMAND = 'inv.........'
GETDATA_COMMAND = 'getdata.....'
GETTXS_COMMAND = 'gettxs......'
NEWBLOCK_COMMAND = 'newblock....'

# TODO
MAX_BLOCKS_TO_SEND = 100
SECONDS_TO_ASK = 5

metadata = lambda command, ip, port: f'{command}{ip}'.encode('utf-8') + port

class Node():
	def __init__(self, ip='0.0.0.0', port=8080, max_connections=5, conexions=[], version='1.0'):
		# Create server socket
		self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		self.server_socket.bind((ip, port))
		self.server_socket.listen(max_connections)
		print('Server socket created and listening')
		self.listen_thread = threading.Thread(target=self.listen)
		self.listen_thread.start()

		self.peers = []
		self.outstanding_txs_pool = []
		self.ip = ip
		while len(self.ip) < 15: self.ip += " "
		self.port = port
		self.metadata = lambda command: metadata(command, self.ip, self.port.to_bytes(4, 'little'))
		self.max_connections = max_connections
		self.version = version

		self.blockchain = Blockchain()
		# Test for syncing blockchain
		if len(conexions) == 0:
			self.add_block([(100, 0), (100, 1)])
			self.add_block([(200, 0), (200, 1)])
			self.add_block([(300, 0), (300, 1)])
			self.add_block([(400, 0), (400, 1)])
			self.add_block([(500, 0), (500, 1)])

		print(f'Initial Blockchain \n {self.blockchain}')

		# Load and establish conexions 
		for conexion in conexions:
			self.send_conexion_handler(conexion)
			if conexion in self.peers: 
				self.send_getblocks_handler(conexion)
				# self.send_gettxs_handler(conexion)

		# Test for adding future blocks to network
		if len(conexions) > 0:
			self.add_block([(600, 0), (600, 1)])
			self.add_block([(700, 0), (700, 1)])
			self.add_block([(800, 0), (800, 1)])

	def listen(self):
		while True:
			client_socket, client_address = self.server_socket.accept()
			self.message_handler(client_socket)

	def message_handler(self, client_socket):
		command_metadata = client_socket.recv(31)
		command, ip, port = command_metadata[:12].decode('utf-8'), command_metadata[12: 27].decode('utf-8').strip(), int.from_bytes(command_metadata[27:], 'little')
		if command == VERSION_COMMAND:
			self.receive_conexion_handler(client_socket)
		if (ip, port) not in self.peers:
			print('Unknown node trying to send message')
			client_socket.close()
			return
		if command == GETBLOCKS_COMMAND:
			self.send_inv_handler(client_socket)
		elif command == GETDATA_COMMAND:
			self.send_block_handler(client_socket)
		elif command == TRANSACTION_COMMAND:
			self.receive_transaction_hanlder(client_socket)
		elif command == BLOCK_COMMAND:
			self.receive_block_hanlder(client_socket)
		else:
			client_socket.close()


	def receive_conexion_handler(self, client_socket):
		# Listen to rest of message
		payload = client_socket.recv(22)
		version, server_address, server_port, = self.decode_version(payload)
		print(f'Node trying to connect with version {version}, ip {server_address}, port {server_port}')

		if version != self.version: 
			# Node with uncompatible version trying to connect
			print('Node with uncompatible version. Rejected connection')
			client_socket.close()
			return

		if len(self.peers) == self.max_connections:
			# Node connected with max connections
			print('Node with maximun connections limit. Rejected connection')
			client_socket.close()
			return

		self.send_verack_handler(client_socket)
		client_socket.close()
		print('Compatible version, sending verack')

		# Check if node in peers, add to peers 
		if (server_address, server_port) not in self.peers: 
			self.send_conexion_handler((server_address, server_port))
			self.send_getblocks_handler((server_address, server_port))
		return

	def send_conexion_handler(self, conexion):
		client_socket = self.create_socket(conexion)

		# Send version message
		self.send_version_handler(client_socket)

		# Receive verack
		command_metadata = client_socket.recv(31)
		command = command_metadata[:12].decode('utf-8')
		if command != VERACK_COMMAND:
			# Message Received is not verack
			print('Did not receive verack')
			client_socket.close()
			return

		# If verack Received, add conexion to peers
		self.peers.append(conexion)
		print('Received verack and node added to peer')

		# Close client socket
		client_socket.close()
		return

	def send_getblocks_handler(self, conexion):
		client_socket = self.create_socket(conexion)

		command = self.metadata(GETBLOCKS_COMMAND)
		client_socket.send(command)
		print('Send getblocks command')
		client_socket.send(self.current_height.to_bytes(4, 'little'))

		# Receive command
		command_metadata = client_socket.recv(31)
		command = command_metadata[:12].decode('utf-8')
		if command != INV_COMMAND:
			# Did not receive inventory
			print('Did not receive inventory')
			client_socket.close()
			return
		print('Received inv command')

		# Receive inv metadata
		inv_metadata = client_socket.recv(8)
		heigth, number_blocks_hashes = self.decode_inv_metadata(inv_metadata)
		print(f'Blockchain out of sync. Node height {self.current_height} and received heigth {heigth}. Receiving {number_blocks_hashes} blocks')
		
		# Receive inv blocks hashes
		block_hashes = []
		for _ in range(number_blocks_hashes):
			block_hash = client_socket.recv(4)
			block_hashes.append(block_hash)
		client_socket.close()

		for block_hash in block_hashes:
			self.send_getdata_handler(conexion, block_hash)
		print(f'Updated blockchain \n {self.blockchain}')

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
		print('Send inv command')
		payload = self.current_height.to_bytes(4, 'little')
		number_blocks_hashes = min(self.current_height - heigth,  MAX_BLOCKS_TO_SEND)
		payload += number_blocks_hashes.to_bytes(4, 'little')
		print(f'Peer Blockchain out of sync. Sending {number_blocks_hashes} blocks')

		# Iterate over blockchain to obtain desired block
		sent_blocks = 0
		while sent_blocks < number_blocks_hashes:
			current_block_hash = self.blockchain.head_block_hash
			current_block = self.blockchain.blocks[current_block_hash]
			while current_block_hash > heigth + 2:
				current_block_hash = current_block.data['prev_block_hash']
				current_block = self.blockchain.blocks[current_block_hash]
			# Stop iterating on the next block of the one to send, to obtain prev_block_hash
			# Special case for the head node
			if heigth + 1 == self.current_height: 
				block_hash_to_send = current_block_hash
			else:
				block_hash_to_send = current_block.data['prev_block_hash']
			payload += block_hash_to_send.to_bytes(4, 'little')
			heigth += 1
			sent_blocks += 1

		client_socket.send(payload)
		client_socket.close()

	def send_getdata_handler(self, conexion, block_hash):
		command = self.metadata(GETDATA_COMMAND)
		# Send getdata command
		client_socket = self.create_socket(conexion)
		client_socket.send(command)
		payload = block_hash
		client_socket.send(payload)
		print(f'Sent getdata for block {int.from_bytes(block_hash, "little")}')

		# Check if Receive block command
		command_metadata = client_socket.recv(31)
		command = command_metadata[:12].decode('utf-8')
		if command != BLOCK_COMMAND:
			client_socket.close()
			return

		self.receive_block_hanlder(client_socket)
			
	def receive_block_hanlder(self, client_socket):
		block_metadata = client_socket.recv(12)
		block_hash, prev_block_hash, number_of_txs = self.decode_block_metadata(block_metadata)
		print(f'Received block {block_hash} with prev_block_hash {prev_block_hash} and number_of_txs {number_of_txs}')
		block_txs = []
		for _ in range(number_of_txs):
			tx_metadata = client_socket.recv(8)
			value, uniqueID = self.decode_tx_metadata(tx_metadata)
			block_txs.append((value, uniqueID))

		# Add block to blockchain
		if self.add_block(block_txs, block_hash):
			print(f'Added block {block_hash} with prev_block_hash {prev_block_hash} and txs {block_txs}')
		print(f'Updated blockchain \n {self.blockchain}')
		client_socket.close()

	def send_block_handler(self, client_socket, block_hash=False):
		# Get block data from hash
		if not block_hash: block_hash = int.from_bytes(client_socket.recv(4), 'little')
		prev_block_hash, number_of_txs, block_txs = self.get_block_data(block_hash)

		command = self.metadata(BLOCK_COMMAND)
		client_socket.send(command)
		payload = block_hash.to_bytes(4, 'little') + prev_block_hash.to_bytes(4, 'little') + number_of_txs.to_bytes(4, 'little')
		client_socket.send(payload)
		print(f'Sent block {block_hash} with prev_block_hash {prev_block_hash} and {number_of_txs} txs')
		for tx in block_txs:
			# Send 4 bytes with the value of the tx
			payload = tx.data['value'].to_bytes(4, 'little')
			# Send 4 bytes with the uniqueID of the tx
			payload += tx.data['uniqueID'].to_bytes(4, 'little')
			client_socket.send(payload)
		client_socket.close()

	def new_block_handler(self, conexion, block_hash):
		# Create socket to send block to conexion
		client_socket = self.create_socket(conexion)
		self.send_block_handler(client_socket, block_hash)

	# def send_gettxs_handler(self, conexion):
	# 	client_socket = self.create_socket(conexion)

	# 	command = self.metadata(GETTXS_COMMAND)
	# 	client_socket.send(command)
	# 	print('Send gettxs command')
	# 	client_socket.send(self.current_height.to_bytes(4, 'little'))

	# 	# Receive command
	# 	command_metadata = client_socket.recv(31)
	# 	command = command_metadata[:12].decode('utf-8')
	# 	if command != INV_COMMAND:
	# 		# Did not receive inventory
	# 		print('Did not receive inventory')
	# 		client_socket.close()
	# 		return
	# 	print('Received inv command')

	# 	# Receive inv metadata
	# 	inv_metadata = client_socket.recv(8)
	# 	heigth, number_blocks_hashes = self.decode_inv_metadata(inv_metadata)
	# 	print(f'Blockchain out of sync. Node height {self.current_height} and received heigth {heigth}. Receiving {number_blocks_hashes} blocks')
		
	# 	# Receive inv blocks hashes
	# 	block_hashes = []
	# 	for _ in range(number_blocks_hashes):
	# 		block_hash = client_socket.recv(4)
	# 		block_hashes.append(block_hash)
	# 	client_socket.close()

	# 	for block_hash in block_hashes:
	# 		self.send_getdata_handler(conexion, block_hash)
	# 	print(f'Updated blockchain \n {self.blockchain}')

	def receive_transaction_hanlder(self, client_socket):
		pass

	def get_block_data(self, block_hash):
		# Get prev_block_hash as 4 bytes
		block = self.blockchain.blocks[block_hash]
		prev_block_hash = block.data['prev_block_hash']
		# Get amount of tx to send as 4 bytes
		number_of_txs = len(block.data['transactions'])
		# Get transactions to send
		block_txs = block.data['transactions']
		return prev_block_hash, number_of_txs, block_txs

	def add_block(self, block_txs, block_hash=False):

		# Try to add block to blockchain. If block already in blockchain, block_hash is False
		block_hash = self.blockchain.add_block(block_txs, block_hash=block_hash)

		if block_hash:
			# Propagate block to peers
			for conexion in self.peers:
				self.new_block_handler(conexion, block_hash)
			return True


	@property
	def current_height(self):
		return self.blockchain.head_block_hash
	# @property
	# def current_height(self):
		# return len(self.blockchain)

	def create_socket(self, conexion):
		# Create client socket
		client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		# Connect to conexion
		client_socket.connect(conexion)
		return client_socket

	def decode_version(self, payload):
		version = payload[:3].decode('utf-8')
		server_address = payload[3:18].decode('utf-8').strip()
		server_port = int.from_bytes(payload[18: 22], 'little')
		return version, server_address, server_port

	def decode_inv_metadata(self, payload):
		heigth = int.from_bytes(payload[:4], 'little')
		number_of_hashes = int.from_bytes(payload[4:8], 'little')
		return heigth, number_of_hashes

	def decode_block_metadata(self, payload):
		block_hash, prev_block_hash, number_of_tx = int.from_bytes(payload[:4], 'little'), int.from_bytes(payload[4:8], 'little'), int.from_bytes(payload[8:], 'little')
		return block_hash, prev_block_hash, number_of_tx

	def decode_tx_metadata(self, payload):
		value, uniqueID = int.from_bytes(payload[:4], 'little'), int.from_bytes(payload[4:], 'little')
		return value, uniqueID

	def decode_inv_block_hashes(self, payload, number_of_hashes):
		block_hashes = [payload[i * 64 : (i + 1) * 64] for i in range(number_of_hashes)]
		return block_hashes

	def send_version_handler(self, client_socket):
		# Send command version
		command = self.metadata(VERSION_COMMAND)
		client_socket.send(command)
		print('Send version command')

		# Send command version
		payload = self.version.encode('utf-8') + self.ip.encode('utf-8') + self.port.to_bytes(4, 'little')
		client_socket.send(payload)		

	def send_verack_handler(self, client_socket):
		# Send command version
		command = self.metadata(VERACK_COMMAND)
		client_socket.send(command)


if __name__ == '__main__':
	ip, port, version = sys.argv[1], sys.argv[2], sys.argv[3]
	conexions = []
	for ind in range(0, len(sys.argv[4:]), 2):
		conexions.append((sys.argv[ind + 4], int(sys.argv[ind + 5])))

	n = Node(ip=ip, port=int(port), conexions=conexions, version=version)
	n.listen_thread.join()


