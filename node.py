import socket
import threading
import sys

VERSION_COMMAND = b'version.....'
VERACK_COMMAND = b'verack......'
TRANSACTION_COMMAND = b'transaction.'
VERACK_COMMAND = b'block.......'

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
		self.version = version
		self.start_height = 0

		# Load and establish conexions 
		for conexion in conexions:
			self.send_conexion_handler(conexion)

	def listen(self):
		while True:
			client_socket, client_address = self.server_socket.accept()
			self.message_handler(client_socket)

	def message_handler(self, client_socket):
		command = client_socket.recv(12)
		if command == VERSION_COMMAND:
			self.receive_conexion_handler(client_socket)
		elif command == TRANSACTION_COMMAND:
			self.receive_transaction_hanlder(client_socket)
		elif command == BLOCK_COMMAND:
			self.receive_block_hanlder(client_socket)
		client_socket.close()
		return

	def receive_conexion_handler(self, client_socket):
		# Listen to rest of message
		payload = client_socket.recv(27)
		version, server_address, server_port, start_height = self.decode_version(payload)
		print(f'Received {version}, {server_address}, {server_port}, {start_height}')

		if version != self.version: 
			# Node with uncompatible version trying to connect
			client_socket.close()
			return

		self.send_verack(client_socket)
		client_socket.close()
		print('Received version send verack')

		# Check if node in peers, add to peers 
		if (server_address, server_port) not in self.peers: self.send_conexion_handler((server_address, server_port))
		return

	def receive_transaction_hanlder(self, client_socket):
		pass

	def receive_block_hanlder(self, client_socket):
		pass

	def send_conexion_handler(self, conexion):
		# Create client socket
		client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

		# Connect to conexion
		client_socket.connect(conexion)

		# Send version message
		self.send_version(client_socket)

		# Receive verack
		command = client_socket.recv(12)
		if command != VERACK_COMMAND:
			# Message Received is not verack
			client_socket.close()
			return

		# If verack Received, add conexion to peers
		self.peers.append(conexion)
		print('Received verack and node added to peer')

		# Close client socket
		client_socket.close()
		return



	def decode_version(self, payload):
		version = payload[:3].decode('utf-8')
		server_address = payload[3:18].decode('utf-8').strip()
		server_port = int.from_bytes(payload[18: 22], 'little')
		start_height = int.from_bytes(payload[22: 27], 'little')
		return version, server_address, server_port, start_height
		

	def send_version(self, client_socket):
		# Send command version
		command = VERSION_COMMAND
		client_socket.send(command)

		# Send command version
		payload = self.version.encode('utf-8') + self.ip.encode('utf-8') + self.port.to_bytes(4, 'little') +  self.start_height.to_bytes(4, 'little')
		client_socket.send(payload)		

	def send_verack(self, client_socket):
		# Send command version
		command = VERACK_COMMAND
		client_socket.send(command)


if __name__ == '__main__':
	ip, port = sys.argv[1], sys.argv[2]
	conexions = []
	for ind in range(0, len(sys.argv[3:]), 2):
		conexions.append((sys.argv[ind + 3], int(sys.argv[ind + 4])))

	print(conexions)
	n = Node(ip=ip, port=int(port), conexions=conexions)
	n.listen_thread.join()


