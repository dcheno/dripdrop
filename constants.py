"""Module holds constant values for use throughout the program."""

# Network Configuration
LISTENING_PORT = 6881
LISTENING_HOST = '127.0.0.1'  # '' will default to all interfaces

# Handshake Configuration
PSTR = b"BitTorrent protocol"
RESERVED = b"\x00\x00\x00\x00\x00\x00\x00\x00"
INFO_HASH_LEN = 20
PEER_ID_LEN = 20

# Request Configuration
REQUEST_LENGTH = 2 ** 14