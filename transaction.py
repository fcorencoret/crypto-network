from signatures import *
import json

PAYCOINS_TYPE = 'p'
CREATECOINS_TYPE = 'c'


class Input:
    def __init__(self, txID, amount, address):
        self.where_created = txID
        self.value = amount
        self.owner = address  # raw public key (as imported from the storage)

    # for hashing an input
    # def serialize(self):
    #     d = {
    #         'where_created': self.where_created,
    #         'value': self.value,
    #         'owner': str(self.owner)
    #     }
    #     return json.dumps(d, sort_keys=True).encode('utf-8')

    def serialize(self):
        payload = self.where_created.encode('utf-8')
        payload += self.value.to_bytes(4, 'little')
        payload += self.owner.export_key(format='DER')
        return payload

    def __str__(self):
        return '(Origin tx: {} - Value: {} - Owner: {})'.\
            format(self.where_created, self.value, str(self.owner))


class Output:
    def __init__(self, amount, address):
        self.value = amount
        self.recipient = address  # raw public key

    # for hashing an output
    # def serialize(self):
    #     d = {
    #         'value': self.value,
    #         'recipient': str(self.recipient)
    #     }
    #     return json.dumps(d, sort_keys=True).encode('utf-8')

    def serialize(self):
        payload = self.value.to_bytes(4, 'little')
        payload += self.recipient.export_key(format='DER')
        return payload

    def __str__(self):
        return '(Value: {} - Recipient: {})'.format(
            self.value,
            str(self.recipient)
        )


class UnsignedTransaction:
    def __init__(self, txType, input_coins, output_coins, txID=None):
        self.type = txType
        self.inputs = input_coins
        self.outputs = output_coins
        if txID:
            self.txID = txID
        else:
            self.txID = self.generate_txID()

    def DataForSigs(self):
        raw_inputs = []
        for coin in self.inputs:
            raw_inputs.append(str(coin.serialize()))

        raw_outputs = []
        for coin in self.outputs:
            raw_outputs.append(str(coin.serialize()))

        raw_data = {
            'txID': self.txID,
            'type': str(self.type),
            'inputs': raw_inputs,
            'outputs': raw_outputs
        }
        return json.dumps(raw_data, sort_keys=True).encode('utf-8')

    def generate_txID(self):
        payload = b''
        for input in self.inputs:
            payload += input.serialize()
        for output in self.outputs:
            payload += output.serialize()
        return hash(payload).hexdigest()


class Transaction:
    def __init__(self, unsigned, signatures):
        self.txID = unsigned.txID
        self.type = unsigned.type
        self.inputs = unsigned.inputs
        self.outputs = unsigned.outputs
        self.signatures = signatures

    def DataForSigs(self):
        raw_inputs = []
        for coin in self.inputs:
            raw_inputs.append(str(coin.serialize()))

        raw_outputs = []
        for coin in self.outputs:
            raw_outputs.append(str(coin.serialize()))

        raw_data = {
            'txID': self.txID,
            'type': str(self.type),
            'inputs': raw_inputs,
            'outputs': raw_outputs
        }
        return json.dumps(raw_data, sort_keys=True).encode('utf-8')

    # checks that all the signatures match up
    def CheckSignatures(self):
        to_sign = self.DataForSigs()

        if (self.type == PAYCOINS_TYPE):
            input_owners = []

            if len(self.inputs) == 0:
                return False

            if len(self.inputs) != len(self.signatures.keys()):
                return False

            for x in self.inputs:
                owner_key = x.owner.export_key(format='DER')
                if owner_key not in self.signatures.keys():
                    return False
                else:
                    if not verify(to_sign, self.signatures[owner_key], x.owner):
                        return False

            return True

        if self.type == CREATECOINS_TYPE:
            if len(self.signatures) > 1:
                return False

            pubk_scrooge = load_pk('publickeyScrooge.pem')

            scrooge_key = pubk_scrooge.export_key(format='DER')
            if scrooge_key not in self.signatures.keys():
                return False

            if not verify(to_sign, self.signatures[scrooge_key], pubk_scrooge):
                return False

            return True

        return False

    # checks that all the input values < output values -- tp be replaced by the UTXO pool functionalities
    def CheckValues(self):
        if self.type == CREATECOINS_TYPE and sum(output.value for output in self.outputs):
            return True
        in_value = 0
        for x in self.inputs:
            if (x.value < 0):
                return False
            else:
                in_value += x.value

        out_value = 0
        for x in self.outputs:
            if (x.value < 0):
                return False
            else:
                out_value += x.value

        return (in_value >= out_value)

    def serialize(self):
        payload = self.txID.encode('utf-8')
        payload += self.type.encode('utf-8')
        payload += len(self.inputs).to_bytes(4, 'little')
        payload += len(self.outputs).to_bytes(4, 'little')
        payload += len(self.signatures).to_bytes(4, 'little')
        for input in self.inputs:
            payload += input.serialize()
        for output in self.outputs:
            payload += output.serialize()
        for sign in self.signatures:
            payload += sign
            payload += self.signatures[sign]
        return payload

    def __str__(self):
        tmp = 'Transaction {}\n'.format(self.txID)
        tmp += '\t\t\t' + 'Inputs: \n'
        for input in self.inputs:
            tmp += '\t\t\t\t- ' + str(input) + '\n'
        tmp += '\t\t\tOutputs: \n'
        for output in self.outputs:
            tmp += '\t\t\t\t- ' + str(output) + '\n'
        return tmp

if __name__ == '__main__':

    addressA = load_pk('publickeyAlice.pem')
    addressB = load_pk('publickeyBob.pem')
    addressC = load_pk('publickeyCharlie.pem')

    inputs = []

    input0 = Input(1, 0, 7.35, addressA)
    input1 = Input(22, 1, 4.12, addressB)

    inputs.append(input0)
    inputs.append(input1)

    outputs = []

    out0 = Output(1.47, addressA)
    outputs.append(out0)

    unsigned = UnsignedTransaction(1, PAYCOINS_TYPE, inputs, outputs)
    to_sign = unsigned.DataForSigs()

    sigs = {}

    sigs[str(addressA)] = sign(to_sign, 'privatekeyAlice.pem')
    sigs[str(addressB)] = sign(to_sign, 'privatekeyBob.pem')
    # sigs[str(addressC)] = sign(to_sign,'privatekeyCharlie.pem')

    transaction = Transaction(unsigned, sigs)
    print(transaction.CheckSignatures())
    print(transaction.CheckValues())

    unsigned = UnsignedTransaction(1, CREATECOINS_TYPE, inputs, outputs)
    to_sign = unsigned.DataForSigs()

    sigs = {}

    scrooge = load_pk('publickeyScrooge.pem')

    sigs[str(scrooge)] = sign(to_sign, 'privatekeyScrooge.pem')

    transaction = Transaction(unsigned, sigs)
    print(transaction.CheckSignatures())
    print(transaction.CheckValues())
