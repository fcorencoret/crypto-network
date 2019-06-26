from signatures import *
import json

class Block:
	def __init__(self, transactions, prev_hash=None):
		self.transactions = transactions
		self.prev_hash = prev_hash

	def serialize(self):
		d = { 'transactions': self.serialize_transactions(),
		  		'prev_block_hash': self.prev_hash }
		return json.dumps(d, sort_keys=True).encode('utf-8')

	def serialize_transactions(self):
		return [tx.serialize() for tx in self.transactions]

	def __str__(self):
		tmp = ''
		for tx in self.transactions:
			tmp += '\t\t' + str(tx) + '\n'
		return tmp

class Blockchain:
	def __init__(self):
		self.blocks = {}
		self.head_block_hash = None
		self.generate_genesis()

	def generate_genesis(self):
		self.add_block(Block([], None))

	def add_block(self, block):
		
		if ( (block.prev_hash in self.blocks.keys()) or 
			 (len(self.blocks.keys()) == 0)):

			serialize_to_hash = self.hash_block(block)
			self.blocks[serialize_to_hash] = block
			self.head_block_hash = serialize_to_hash
			return self.head_block_hash

		else:
			return None

	def hash_block(self, block):
		payload = b''
		for tx in block.transactions:
			payload += tx.serialize()
		return hash(payload).hexdigest()

	def get_head(self):
		return self.head_block_hash

	def check(self, block_hash):
		if (block_hash not in self.blocks.keys()):
			return False

		serialize_to_hash = hash(bytes(self.blocks[block_hash].serialize())).hexdigest()
		if ( (block_hash != serialize_to_hash) or \
			(verify(self.blocks[block_hash].data,self.blocks[block_hash].signature,self.blocks[block_hash].public_key)) == False):
			return False

		current = self.blocks[block_hash]
		while (current.prev_hash):
			if (current.prev_hash not in self.blocks.keys()):
				return False

			serialize_to_hash = hash(bytes(self.blocks[current.prev_hash].serialize())).hexdigest()
			if ((current.prev_hash != serialize_to_hash) or \
				(verify(self.blocks[serialize_to_hash].data,\
					self.blocks[serialize_to_hash].signature,self.blocks[serialize_to_hash].public_key) == False)):
				return False

			current = self.blocks[current.prev_hash]

		return True

	def print_blockchain(self):
		print('Blockchain')
		for key in self.blocks.keys():
			print('\tBlock hash: {}'.format(key))
			print('\tPrev Block hash: {}'.format(self.blocks[key].prev_hash))
			print('\tTransactions:')
			print(self.blocks[key])
			print('-' * 30)

if __name__ == '__main__':
	blockchain = Blockchain()

	public = load_pk()

	data1 = b'1'
	sig1 = sign(data1)
	genesis = Block(data1, sig1, public, None)

	head = blockchain.add_block(genesis)


	data2 = b'2'
	sig2 = sign(data2)
	bl2 = Block(data2, sig2, public, head)

	head = blockchain.add_block(bl2)	

	data3 = b'3'
	sig3 = sign(data3)
	bl3 = Block(data3, sig3, public, head)

	head = blockchain.add_block(bl3)		

	for key in blockchain.elements.keys():
		print(key)
		print(blockchain.elements[key])

	print(blockchain.check(head))
