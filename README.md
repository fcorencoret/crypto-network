# Cripyocurrency Network

This project requires Python version >= 3.6.

## Installation

```bash
pip install -r requirements.txt
```

## Run a node:

```bash
python node.py <ip> <port> <version> <username>
```

**ip**: IPv4 host to bind server socket.
**port**: port to bind server socket.
**version**: node's version (string of length 3, eg. 1.0).
**username**: name's receiver when node generate a block (it can be Alice, Bob or Charlie).

## Create txs:

```bash
python cli.py <username>
```

**username**: signer of transaction's name.

This GUI have some options that can be seen with `--help` flag.


## Network manager

This tool allows to create a pool of nodes with different probabilities to generate a block simulating computational power of the network.

```bash
python mining_manager.py
```

> Implemented by Francisco Rencoret - Felipe Garrido
