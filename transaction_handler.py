from transaction import *
import json


class Transaction_handler:
    def __init__(self):
        # contains pairs (hash of input, input -- saved as valid UTXOs)
        self.UTXO_pool = {}
        self.transaction_pool = {}

    def add_to_transaction_pool(self, transaction):
        if not transaction.CheckSignatures():
            return False

        if transaction.type == PAYCOINS_TYPE and not transaction.CheckValues():
            return False

        if transaction.txID in self.transaction_pool.keys():
            return False

        # to_hash = hash(transaction.serialize()).hexdigest()
        self.transaction_pool[transaction.txID] = transaction
        return True

    def validate_transactions(self, block):
        for tx in block.transactions:
            # All transactions are valid
            if not self.isValid(tx):
                return False
        return True

    def process_transactions(self, block):
        for tx in block.transactions:
            # If a transaction is not in the tx pool it is added
            if tx.txID not in self.transaction_pool.keys():
                self.add_to_transaction_pool(tx)

        # Update UTXO pool and remove from transaction pool
        for tx in block.transactions:
            self.updateUTXOpool(tx)
            self.transaction_pool.pop(tx.txID)

    def isValid(self, transaction):
        if transaction.type == CREATECOINS_TYPE:
            return True

        for x in transaction.inputs:
            to_hash = x.serialize()
            input_hash = hash(to_hash).hexdigest()
            if input_hash not in self.UTXO_pool.keys():
                return False
        return True

    def updateUTXOpool(self, transaction):
        for x in transaction.inputs:
            to_delete = hash(x.serialize()).hexdigest()
            self.UTXO_pool.pop(to_delete)

        for x in transaction.outputs:
            utxo = Input(
              transaction.txID,
              x.value,
              x.recipient
            )
            utxo_hash = hash(utxo.serialize()).hexdigest()
            self.UTXO_pool[utxo_hash] = utxo


if __name__ == '__main__':

    addressA = load_pk('publickeyAlice.pem')
    addressB = load_pk('publickeyBob.pem')
    addressC = load_pk('publickeyCharlie.pem')

    # initialize the system with scrooge giving out money
    outputs = [
        Output(10, addressA),
        Output(10, addressB),
        Output(10, addressC)
    ]
    unsigned = UnsignedTransaction(1, 'createCoins', [], outputs)
    to_sign = unsigned.DataForSigs()

    sigs = {}

    scrooge = load_pk('publickeyScrooge.pem')

    sigs[str(scrooge)] = sign(to_sign, 'privatekeyScrooge.pem')

    transaction = Transaction(unsigned, sigs)

    uUTXO_pool = Transaction_handler()
    uUTXO_pool.add_to_transaction_pool(transaction)

    uUTXO_pool.process_transactions()

    for x in uUTXO_pool.UTXO_pool:
        print('1->', uUTXO_pool.UTXO_pool[x])

    # add another transaction

    inputs = []

    input0 = Input(1, 0, 10, addressA)
    input1 = Input(1, 1, 10, addressB)
    input2 = Input(1, 2, 10, addressC)

    inputs.append(input0)
    inputs.append(input1)
    inputs.append(input2)

    outputs = []

    out0 = Output(15, addressB)
    outputs.append(out0)

    unsigned = UnsignedTransaction(2, PAYCOINS_TYPE, inputs, outputs)
    to_sign = unsigned.DataForSigs()

    sigs = {}

    sigs[str(addressA)] = sign(to_sign, 'privatekeyAlice.pem')
    sigs[str(addressB)] = sign(to_sign, 'privatekeyBob.pem')
    sigs[str(addressC)] = sign(to_sign, 'privatekeyCharlie.pem')

    transaction = Transaction(unsigned, sigs)
    uUTXO_pool.add_to_transaction_pool(transaction)

    # a competing transaction:
    out1 = Output(15, addressC)
    outputs[0] = out1

    unsigned = UnsignedTransaction(2, PAYCOINS_TYPE, inputs, outputs)
    to_sign = unsigned.DataForSigs()

    sigs = {}

    sigs[str(addressA)] = sign(to_sign, 'privatekeyAlice.pem')
    sigs[str(addressB)] = sign(to_sign, 'privatekeyBob.pem')
    sigs[str(addressC)] = sign(to_sign, 'privatekeyCharlie.pem')

    transaction = Transaction(unsigned, sigs)
    uUTXO_pool.add_to_transaction_pool(transaction)

    # process the two competing ones:

    uUTXO_pool.process_transactions()

    print('after second run')

    for x in uUTXO_pool.UTXO_pool:
        print('2->', uUTXO_pool.UTXO_pool[x])
