from Crypto.Hash import SHA256

def hash(message):
	tmp = SHA256.new()
	tmp.update(message)
	return(tmp)
