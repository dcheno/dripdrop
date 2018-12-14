from queue import Queue
from threading import Thread
from math import ceil
from struct import unpack

from twisted.internet.protocol import Protocol, ClientFactory
from twisted.internet import reactor

from message import Message, MessageParser, MessageType, get_handshake, parse_handshake, is_handshake, message_queue_worker

"""Represent a BitTorrent peer to exchange pieces with."""


class PeerError(Exception):
    pass

class PeerConnectionError(PeerError):
    pass


class HandshakeException(Exception):
    def __init__(self, message):
        super().__init__('Peer Returned Bad Handshake | {}'.format(message))


class Peer:
    def __init__(self, peer_id, ip, port, torrent):
        self.peer_id = peer_id
        self.ip = ip
        self.port = port
        self.info_hash = torrent.info_hash
        self.torrent = torrent
        self.hands_shook = False
        self.choked = False
        self.is_choking = True
        self.interested = False
        self.is_interested = False
        self.pieces = set()
        self.messages_from_peer = Queue()
        self.messages_to_peer = Queue()
        self.working_on_piece = False

        self._connection_thread = None
        self._peer_listener_thread = None
        self._client_listener_thread = None
        self._message_parser = MessageParser()

    def connect(self, client_id):
        """Forms a connection to the peer across TCP. Also creates
        an initial handshake message and schedules it for delivery.

        The connection for this peer is run on it's own thread. Which will
        hopefully allow this to easily be made concurrent.

        Args:
            client_id: String representing the 20 byte client Id that
                is making the connection to the peer.
        Raises:
            A peer exception if the connection has already been made.
        """
        self.shake_hands(client_id)
        # Create a new thread and start a Peer TCP Connection of it.
        if self._connection_thread:
            raise PeerError("This Peer is already connected.")

        reactor.connectTCP(self.ip, self.port, PeerConnectionFactory(self))
        self._connection_thread = Thread(target=reactor.run, kwargs={'installSignalHandlers': 0})
        self._connection_thread.start()
        # TODO: Handle disconnection.

    def shake_hands(self, client_id):
        # First we shake hands. So Queue that up.
        print("shaking hands")
        handshake_message = get_handshake(client_id, self.info_hash)
        print('Handshake:', handshake_message)
        self.message_peer(handshake_message)

    def has_piece(self, piece_num):
        return piece_num in self.pieces

    def message_peer(self, message):
        """Places a message which will be passed to the peer connection"""
        self.messages_to_peer.put(message)
        print("added message")

    def handle_messages(self, data):
        """Interprets incoming messages and responds or notifies the client
        as necessary"""
        print('Trying to handle some messages')
        if is_handshake(data):
            print('This is a Handshake')
            handshake = parse_handshake(data)

            if handshake['peer_id'] != self.peer_id:
                print(handshake['peer_id'], self.peer_id)
                raise HandshakeException('Bad Peer Id')

            self.hands_shook = True
            self.messages_from_peer.put(Message.factory(MessageType.HANDSHAKE, data))

            if 'extra' in handshake:
                self.handle_messages(handshake['extra'])

        else:
            messages = self._message_parser(data)
            for message in messages:
                handler_method = self._message_dispatch(message)
                handler_method(message.payload)
                # print('Placing message:', message)
                self.messages_from_peer.put(message)

    def subscribe_for_messages_to_peer(self, callback):
        """Assigns a callback for all messages that are intended for the peer"""
        print('Subscribing for Peer')
        if self._peer_listener_thread:
            raise PeerError("This peer already has a connection listening to it.")
        thread = Thread(target=message_queue_worker, args=(self.messages_to_peer, callback))
        self._peer_listener_thread = thread
        print('Starting Thread')
        thread.start()

    def subscribe_for_messages_to_client(self, callback):
        """Assigns a callback for all messages that are intended for the client"""
        print('Subscribing for Client')
        if self._client_listener_thread:
            raise PeerError("This peer already has a client listening to it.")
        thread = Thread(target=message_queue_worker, args=(self.messages_from_peer, callback))
        self._client_listener_thread = thread
        thread.start()

    def _message_dispatch(self, message):
        if not isinstance(message, Message):
            raise ValueError("Dispatch is only valid on Message")
        name = message.type.name.lower()
        method_name = '_handle_' + name
        return getattr(self, method_name)

    def _handle_keep_alive(self, payload):
        print("Don't let me die!")

    def _handle_choke(self, payload):
        print("Peer is choking us.")
        self.is_choking = True

    def _handle_unchoke(self, payload):
        print("Peer is unchoking us.")
        self.is_choking = False

    def _handle_interested(self, payload):
        self.is_interested = True

    def _handle_uninterested(self, payload):
        self.is_interested = False

    def _handle_have(self, payload):
        # TODO: interpret message and adjust pieces[]
        # Format: Payload is an integer which represents the 0 based
        # index of the piece that it is saying it has.
        # FIXME: This has not been tested with an actual message!
        piece_index = unpack('!I', payload)[0]
        self.pieces.add(piece_index)

    def _handle_bitfield(self, payload):
        """Update the peer's pieces based on the bitfield representation.

        The bitfield payload is a series of bytes, where each bit in
        each byte represents whether the peer has the piece or not. The leftmost
        bit of the leftmost byte is piece 0.

        Assert: (pieces//8) <= len(bitfield payload) <= ((pieces//8) + 1)
        """
        print('handling bitfield')

        # Double check the length of the payload vs the expected length of the file.
        if len(payload) != ceil(self.torrent.num_pieces/8):
            raise PeerError('Peer Bitfield Does not Match Expected Length')
            # TODO: Handle this exception in caller and drop the connection.

        piece_number = 0
        for byte in payload:
            bits = bin(byte).lstrip('0b')

            # Make up for missing leading zeros.
            piece_number += 8 - len(bits)
            for bit in bits:
                if bit == '1':
                    self.pieces.add(piece_number)
                piece_number += 1
                if piece_number >= self.torrent.num_pieces:
                    break

    def _handle_request(self, payload):
        # TODO: handle request from other peer
        #    (might be more for the client than the peer)
        pass

    def _handle_piece(self, payload):
        # TODO: Handle incoming pieces!
        pass

class PeerConnection(Protocol):
    def __init__(self, factory):
        self.peer = factory.peer

    def connectionMade(self):
        """Function to be called whenever a connection is established
        for the protocol."""
        print('Connection Made')
        #handshake_message = get_handshake('-DD0001-123456789013', self.peer.info_hash)
        #self.transport.write(handshake_message)
        self.peer.subscribe_for_messages_to_peer(self.send_message)
        print("subscribed")
        print(self.peer.messages_to_peer.queue)

    def dataReceived(self, data):
        """Function to be called whenever data is received over the connection

        Should examine type of message and parse. If initial handshake, should
        examine for authenticity, and prepare for response.
        """
        print('Data Recieved')
        # print(data)
        self.peer.handle_messages(data)

    def send_message(self, message):
        print('sending message:', message)
        self.transport.write(message.to_bytes())

class PeerConnectionFactory(ClientFactory):
    def __init__(self, peer):
        self.peer = peer

    def startedConnecting(self, connector):
        print('Started to connect Peer')

    def buildProtocol(self, addr):
        return PeerConnection(self)

    def clientConnectionLost(self, connector, reason):
        print('Lost connection:', reason)

    def clientConnectionFailed(self, connector, reason):
        print('Failed connection:', reason)
        raise PeerConnectionError(reason)