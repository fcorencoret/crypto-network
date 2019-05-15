import socket
import threading
import sys

VERSION_COMMAND = 'version.....'
VERACK_COMMAND = 'verack......'
TRANSACTION_COMMAND = 'transaction.'
BLOCK_COMMAND = 'block.......'
GETBLOCKS_COMMAND = 'getblocks...'
INV_COMMAND = 'inv.........'
GETDATA_COMMAND = 'getdata.....'

MAX_BLOCKS_TO_SEND = 100

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
		self.ip = ip
		while len(self.ip) < 15: self.ip += " "
		self.port = port
		self.metadata = lambda command: metadata(command, self.ip, self.port.to_bytes(4, 'little'))
		self.max_connections = max_connections
		self.version = version

		self.blockchain = {
			(b'0' * 64) : b'0' * 4
		}

		if len(conexions) == 0:
			
			self.blockchain[b'1' * 64] = b'1' * 4
			self.blockchain[b'2' * 64] = b'2' * 4

		# Load and establish conexions 
		for conexion in conexions:
			self.send_conexion_handler(conexion)
			if conexion in self.peers: self.send_getblocks_handler(conexion)
		print(self.blockchain)

	def listen(self):
		while True:
			client_socket, client_address = self.server_socket.accept()
			self.message_handler(client_socket)

	def message_handler(self, client_socket):
		command_metadata = client_socket.recv(31)
		command, ip, port = command_metadata[:12].decode('utf-8'), command_metadata[12: 27].decode('utf-8').strip(), int.from_bytes(command_metadata[27:], 'little')
		print(f'{command} {ip} {port}')
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
		print(f'Received version {version}, ip {server_address}, port {server_port}')

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
		print('Received version, sending verack')

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

	def send_inv_handler(self, client_socket):
		# Height received from GETBLOCKS
		heigth = client_socket.recv(4)
		heigth = int.from_bytes(heigth, 'little')
		current_height = self.current_height

		if heigth >= current_height:
			# Received a geater or equal blockchain heigth
			client_socket.close()
			return

		command = self.metadata(INV_COMMAND)
		client_socket.send(command)
		payload = self.current_height.to_bytes(4, 'little')
		payload += min(current_height - heigth,  MAX_BLOCKS_TO_SEND).to_bytes(4, 'little')
		print(f'Peer Blockchain out of sync. Sending {min(current_height - heigth,  MAX_BLOCKS_TO_SEND)} blocks')
		# for i in range(min(current_height - heigth,  MAX_BLOCKS_TO_SEND)):
		# 	payload += (str(i) * 64).encode('utf-8')
		for k in self.blockchain.keys():
			payload += k

		client_socket.send(payload)
		client_socket.close()

	def send_getblocks_handler(self, conexion):
		client_socket = self.create_socket(conexion)

		command = self.metadata(GETBLOCKS_COMMAND)
		client_socket.send(command)
		client_socket.send(self.current_height.to_bytes(4, 'little'))

		# Receive command
		command_metadata = client_socket.recv(31)
		command = command_metadata[:12].decode('utf-8')
		if command != INV_COMMAND:
			# Did not receive inventory
			print('Did not receive inventory')
			client_socket.close()
			return
		print('Received inventory')

		# Receive inv
		inv_metadata = client_socket.recv(8)
		heigth, number_of_hashes = self.decode_inv_metadata(inv_metadata)
		print(f'Blockchain out of sync. Node height {self.current_height} and received heigth {heigth}. Receiving {number_of_hashes} blocks')
		inv_block_hashes = client_socket.recv(number_of_hashes * 64)
		block_hashes = self.decode_inv_block_hashes(inv_block_hashes, number_of_hashes)
		client_socket.close()

		for block_hash in block_hashes:
			self.getdata_handler(conexion, block_hash)

	def getdata_handler(self, conexion, block_hash):
		command = self.metadata(GETDATA_COMMAND)
		# Send getdata command
		client_socket = self.create_socket(conexion)
		client_socket.send(command)
		payload = block_hash
		client_socket.send(payload)
		self.receive_block_hanlder(client_socket)
			
	def receive_block_hanlder(self, client_socket):
		command_metadata = client_socket.recv(31)
		command = command_metadata[:12].decode('utf-8')
		if command != BLOCK_COMMAND:
			client_socket.close()
			return
		block_size = client_socket.recv(4)
		block_size = int.from_bytes(block_size, 'little')
		block_data = client_socket.recv(block_size)
		self.add_block(block_data)
		client_socket.close()

	def send_block_handler(self, client_socket):
		block_hash = client_socket.recv(64)
		block_data, block_size = self.get_block_data(block_hash)

		command = self.metadata(BLOCK_COMMAND)
		client_socket.send(command)
		client_socket.send(block_size)
		client_socket.send(block_data)
		client_socket.close()

	def receive_transaction_hanlder(self, client_socket):
		pass

	def get_block_data(self, block_hash):
		return self.blockchain[block_hash], (4).to_bytes(4, 'little')

	def add_block(self, block_data):
		self.blockchain[(str(len(self.blockchain)) * 64).encode('utf-8')] = block_data
		print(f'Added block {block_data}')

	@property
	def current_height(self):
		# TODO: Change for blockchain heigth
		return len(self.blockchain)

	

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

	def decode_inv_block_hashes(self, payload, number_of_hashes):
		block_hashes = [payload[i * 64 : (i + 1) * 64] for i in range(number_of_hashes)]
		return block_hashes

	def send_version_handler(self, client_socket):
		# Send command version
		command = self.metadata(VERSION_COMMAND)
		client_socket.send(command)

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


