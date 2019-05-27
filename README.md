# Cripyocurrency Network

This project requires Python version > 3.6.

## Installation

```bash
pip install -r requirements.txt
```

## Run a node:

```bash
python node.py <ip> <port> <version>
```

**ip**: IPv4 host to bind server socket.
**port**: port to bind server socket.
**version**: node's version (string of length 3, eg. 1.0).

## Create txs or blocks:

```bash
python cli.py
```

This GUI have some options that can be seen with `--help` flag.

> Implemented by Francisco Rencoret - Felipe Garrido
