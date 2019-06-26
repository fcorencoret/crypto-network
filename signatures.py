from Crypto.PublicKey import ECC
from Crypto.Signature import DSS
from hash import hash


#  signing a message with the private key
def sign(message, key_storage='privatekey.pem'):
    # load the private key for signing:
    f = open(key_storage, 'rt')
    private_key = ECC.import_key(f.read())

    # hash the message
    h = hash(message)

    # sign with the private key
    signer = DSS.new(private_key, 'deterministic-rfc6979')
    signature = signer.sign(h)

    # reurn the signature
    return signature


# verify if the message is authentic
def verify(message, signature, public_key):
    # hash the message
    h = hash(message)

    # load the verification module
    verifier = DSS.new(public_key, 'deterministic-rfc6979')
    try:
        verifier.verify(h, signature)
        return True
    except ValueError:
        return False


def load_pk(file_name='publickey.pem'):
    # load the public key
    f = open(file_name, 'rt')
    public_key = ECC.import_key(f.read())
    return public_key
