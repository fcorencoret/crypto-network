import json
from Crypto.Hash import SHA256


def hash(self, serialized_data):
    sha = SHA256.new()
    sha.update(serialized_data)
    return sha.hexdigest()


class Blockchain():
    def __init__(self):
        self.blocks = {}
        self.head_block_hash = -1
        self.genesis_block_hash = 0
        self.add_block([], type='genesis')

    def create_block(self):
        # Method for creating block upon on own Transactions
        # Create Block instance
        # block = Block(transactions, self.head_block_hash)
        # Serialize and hash bock
        # block_hash = self.hash_block(block.serialize())
        # self.blocks[block_hash] = block
        pass

    def add_block(self, transactions, type='block', block_hash=False):
        # Method for adding block to blockchain
        if block_hash and block_hash in self.blocks:
            return False, block_hash

        # Create Block instance with information received
        prev_block_hash = self.head_block_hash if type == 'block' else None
        block = Block(type, prev_block_hash, transactions)
        # TODO: Serialize and hash bock
        # block_hash = self.hash_block(block.serialize())
        # self.blocks[block_hash] = block

        if not block_hash:
            block_hash = self.head_block_hash + 1
        self.blocks[block_hash] = block
        self.head_block_hash = block_hash
        return True, self.head_block_hash

    def __str__(self):
        tmp = ''
        tmp += 'Blockchain\n'
        for i in range(self.head_block_hash + 1):
            current_block = str(self.blocks[i])
            tmp += f'\tBlock {i} | {current_block} \n'
        return tmp

    def __len__(self):
        return len(self.blocks) - 1


class Block():
    def __init__(self, type, prev_block_hash, transactions):
        self.data = {
            'type': type,
            'prev_block_hash': prev_block_hash,
            'transactions': self.generate_transactions(transactions),
        }

    def generate_transactions(self, received_transactions):
        generated_transactions = []
        for transaction in received_transactions:
            uniqueID = transaction[0]
            value = transaction[1]
            generated_transactions.append(Transaction(uniqueID, value))
        return generated_transactions

    def serialize(self):
        serialized_block = json.dumps(
            self.data,
            sort_keys=True
        ).enconde('utf-8')
        return serialized_block

    def __str__(self):
        str_transactions = [
            str(transaction) for transaction in self.data['transactions']
        ]
        return 'type: {} - prev_block: {} - txs: {}'\
            .format(
                self.data['type'],
                self.data['prev_block_hash'],
                str_transactions
            )


class Transaction():
    def __init__(self, uniqueID, value):
        self.data = {
            'type': 'transaction',
            'uniqueID': uniqueID,
            'value': value,
        }

    def __str__(self):
        return f'Tx ID {self.data["uniqueID"]} | Value {self.data["value"]}'
