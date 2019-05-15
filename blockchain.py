import json
from Crypto.Hash import SHA256

class Blockchain():
	def __init__(self):
		self.blocks = {}
		self.head_block_hash = b''

	def create_block(self, type, transactions):
		block_data = {
			'type' : type,
			'transactions' : transactions,
			'prev_block_hash' : self.head_block_hash
		}
		serialized_block = json.dumps(block_data, sort_keys=True).enconde('utf-8')
		block_hash = self.hash_block(serialized_block)
		self.blocks[block_hash] = block_data

	def hash_block(self, serialized_block):
		sha = SHA256.new()
		sha.update(serialized_block)
		return sha.hexdigest()

	def add_block(self, block):
		pass