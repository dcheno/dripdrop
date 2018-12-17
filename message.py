from queue import Queue
from enum import Enum
from struct import unpack, pack
import constants

"""Handle BitTorrent Protocol message parsing duties"""


class MessageException(Exception):
    pass


class MessageParser:
    """Takes in bytestrings from a peer and interprets them
    into messages.

    Messages arrive in bytestrings. Each message begins with
    a 4 byte prefix which describes its length.

    We need to check the length prefix, then use that length to
    retrieve the rest of the message.

    A complication is that a bytestring coming from the peer can
    contain multiple messages or can end in a partial message. In
    the latter case we will need to check the next bytestring
    """
    def __init__(self):
        self.incomplete_message = b''
        self.counter = 0

    def __call__(self, bytestring):
        """Take in raw bytestring and returns generator that yields messages"""

        # Waiting on message?
        if self.incomplete_message:
            bytestring = self.incomplete_message + bytestring
            self.incomplete_message = b''

        while bytestring:
            try:
                length_bytes, bytestring = _strip_message(bytestring, 4)
                length = unpack('!I', length_bytes)[0]
            except ValueError:
                raise MessageException('Bad Length Bits | {}'.format(bytestring))
            # NOTE: If this is breaking... it might be because we're getting incomplete length bits.

            # Is this a complete message?
            if len(bytestring) < length:
                self.incomplete_message = length_bytes + bytestring
                break
            else:
                message_bytes, bytestring = _strip_message(bytestring, length)
                yield self._parse_message(message_bytes)

    @staticmethod
    def _parse_message(bytestring):
        """Returns an appropriate Message object"""
        if not bytestring:
            return Message.factory(MessageType.KEEP_ALIVE)
        else:
            id_byte, payload = _strip_message(bytestring, 1)
            type_id = int.from_bytes(id_byte, byteorder='big')
            message_type = MessageType(type_id)

            if payload:
                return Message.factory(message_type, payload)
            else:
                return Message.factory(message_type)


class MessageType(Enum):
    CLOSE = -3
    HANDSHAKE = -2
    KEEP_ALIVE = -1
    CHOKE = 0
    UNCHOKE = 1
    INTERESTED = 2
    UNINTERESTED = 3
    HAVE = 4
    BITFIELD = 5
    REQUEST = 6
    PIECE = 7


class Message:
    @staticmethod
    def factory(message_type, raw_payload=None):
        if message_type == MessageType.PIECE:
            return PieceMessage(raw_payload)
        elif message_type == MessageType.HANDSHAKE:
            return HandShakeMessage(raw_payload)
        else:
            return Message(message_type, raw_payload)

    def __init__(self, message_type, payload=None):
        self.type = message_type
        self.payload = payload

    def to_bytes(self):
        # form the length prefix.
        if self.payload:
            length = len(self.payload) + 1
        else:
            length = 1

        length_bytes = pack('!I', length)
        id_byte = int.to_bytes(self.type.value, length=1, byteorder='big')
        bytestring = length_bytes + id_byte

        if self.payload:
            bytestring += self.payload

        return bytestring

    def __repr__(self):
        return 'Message [ type: {} | payload: {} ]'.format(self.type.name, self.payload or 'No Payload')


class HandShakeMessage(Message):
    def __init__(self, payload):
        super().__init__(MessageType.HANDSHAKE, payload)

    def to_bytes(self):
            return self.payload


class PieceMessage(Message):
    def __init__(self, raw_payload):
        index_bytes = raw_payload[:4]
        self.index = int.from_bytes(index_bytes, byteorder='big')
        offset_bytes = raw_payload[4:8]
        self.offset = int.from_bytes(offset_bytes, byteorder='big')
        super().__init__(MessageType.PIECE, raw_payload[8:])

    def __repr__(self):
        return 'Message [ type: {} | index: {} ]'.format(self.type.name, self.index)


def _strip_message(message, index):
    """Splits an array at the given index"""
    if index > len(message):
        raise ValueError('Index Not Applicable | {} {}'.format(message, index))
    strip = message[:index]
    leftover = message[index:]

    return strip, leftover


def is_handshake(data):
    """Tests if a message is a handshake message. Currently this is done by comparing
    the first 20 bytes and making sure they match the initial 20 bytes of a
    a handshake message (19BitTorrentProtocol)"""
    pstrlen = len(constants.PSTR)
    i = pstrlen + 1
    return data[:i] == bytes([pstrlen]) + constants.PSTR


def get_handshake(client_id, info_hash):
    """Return a bytestring that represents our handshake to
    a peer

    Message format:
        <pstrlen><pstr><reserved><info_hash><peer_id>
    """

    pstrlen = bytes([len(constants.PSTR)])
    payload = b"".join([pstrlen, constants.PSTR, constants.RESERVED, info_hash, client_id.encode()])
    message = Message.factory(MessageType.HANDSHAKE, payload)
    return message


def parse_handshake(data):
    """Interpret a handshake received from a peer.

    Remember that there could be extra info at the end!"""
    handshake = {}
    pstrlen = len(constants.PSTR)
    i = pstrlen + len(constants.RESERVED) + 1  # 1 for the leading byte
    j = i + constants.INFO_HASH_LEN
    handshake['info_hash'] = data[i:j]

    k = j + constants.PEER_ID_LEN
    handshake['peer_id'] = data[j:k].decode('utf-8')

    handshake['extra'] = data[k:]

    return handshake


class MessageQueue(Queue):
    STOP = object()

    def close(self):
        self.put(self.STOP)

    def __iter__(self):
        while True:
            message = self.get()
            try:
                if message is self.STOP:
                    return
                yield message
            finally:
                self.task_done()


def message_queue_worker(message_queue, callback):
    """This little guy will keep trying to pull from
    the queue until it's told not to.

    Will call the the callback function then alert the
    queue that work is done"""
    for message in message_queue:
        callback(message)
