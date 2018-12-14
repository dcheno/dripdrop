from queue import Queue
from threading import Thread

from twisted.internet import reactor

from tracker import Tracker, TrackerEvent
from peer import PeerConnectionFactory
from torrent import Torrent
from message import MessageType, Message
from piece import Piece, piece_factory
import constants

"""Represent a client to connect to the bittorrent swarm"""


class ClientException(Exception):
    pass


class Client:
    """Represents a client connected to a single tracker for
    a single bittorrent file
    """

    def __init__(self):
        self.peer_id = '-DD0001-123456789013'
        self._peers = []
        self.pieces = []
        self.unrequested_pieces = None

    def add_torrent(self, tor_file_path):
        """Give the Client at Torrent to use.

        TODO: Test Normal Functionality
        TODO: Test if called where Client already has Torrent
        """
        if hasattr(self, '_torrent'):
            raise ClientException('Client already has a Torrent')
        else:
            self._torrent = Torrent(tor_file_path)
            self.unrequested_pieces = piece_factory(self._torrent.length, self._torrent.piece_length)

    def start_torrent(self):
        """Begin the torrent process by contacting the Tracker and
        waiting for the response.

        TODO: Test Normal Functionality
        TODO: Test if called without Torrent
        """
        if not hasattr(self, '_torrent'):
            raise ClientException('Client Has Not Been Assigned Torrent')
        self._connect_tracker(self._torrent.announce, self._torrent.info_hash)

    def _connect_tracker(self, announce, info_hash):
        """Establish initial contact with the HTTP Tracker."""
        event = TrackerEvent.STARTED
        self._tracker = Tracker(announce, info_hash)
        response = self._tracker.request(event, self.peer_id, constants.LISTENING_PORT)
        self._handle_tracker_contact(response)

    def _handle_tracker_contact(self, response):
        """Handle the initial HTTP response from the tracker.

        Args:
            response: a decoded dictionary holding the tracker response
                items (could be a class TrackerResponse?)

        TODO: Actually implement this.
              1. store potential peers
              2. iterate through peers for connection
              3. possibly connect more than one peer
              4. communicate with peer and download files!

        """
        print('HTC:', response)  # FIXME

    def _connect_peer(self, peer):
        """Creates a connection with a potential peer"""
        # FIXME: This isn't currently called anywhere. Should probably call peers
        #        in order and see if it can get a handshake back.
        peer.connect(self.peer_id)
        peer.subscribe_for_messages_to_client(self.peer_message_receiver(peer))

    def peer_message_receiver(self, peer):
        def handle_peer_message(message):
            print('Client Handling Message')
            # 1. First we wait for the handshake. Then we express interest.
            if not peer.hands_shook:
                # We don't do anything with someone who hasn't shaken our hand.
                # Potential FIXME: Raise exception.
                print("Peer has not shaken our hand")
                return

            if peer.is_choking:
                peer.message_peer(Message(MessageType.INTERESTED)) # Possibly this
                # message passing should be replaced by method calls. But that could
                # happen later.
                # It is impolite to do anything before the peer has unchoked us.
                print("Expressing interest. Requesting an unchoke.")
                return

            if not peer.working_on_piece and peer.pieces and len(self.pieces) < self._torrent.num_pieces:
                self._request_next_piece(peer)
                return

            # If the message is a piece message find the appropriate piece and add to it.
            if message.type == MessageType.PIECE:
                complete = self._handle_piece_message(message)
                if complete:
                    peer.working_on_piece = False
                    print(len(self.pieces), self._torrent.num_pieces)
                    if len(self.pieces) < self._torrent.num_pieces:
                        self._request_next_piece(peer)
                        return
                    else:
                        print("All Pieces are Complete")
                        # TODO: Implement complete method which consolidates pieces into a file.
                        with open('torrented_file.jpg', 'wb+') as f:
                            for piece in self.pieces:
                                f.write(piece._downloaded_bytes)
                        print('File written')

        return handle_peer_message

    def _request_next_piece(self, peer):
        print('Requesting piece')
        next_piece = next(self.unrequested_pieces)
        print('Num:', next_piece.index)
        peer.message_peer(next_piece.get_next_request_message())
        self.pieces.append(next_piece)
        print('piece list:', self.pieces)
        peer.working_on_piece = True
        print('Added:', next_piece)


    def _handle_piece_message(self, message):
        """Take in a Piece Message and route the data to the
        appropriate Piece Object

        Returns:
            True if the piece is now completed.
            False if not.
        """
        print("Client Handling Piece")

        # TODO: Reimplement piece message as inherited class
        #       and move this work to message.py
        piece_index_bytes = message.payload[:4]
        piece_index = int.from_bytes(piece_index_bytes, byteorder='big')

        piece_offset_bytes = message.payload[4:8]
        piece_offset = int.from_bytes(piece_offset_bytes, byteorder='big')

        piece = None
        for p in self.pieces:
            if p.index == piece_index:
                piece = p

        if not piece:
            raise ClientException("Peer sending unrequested piece")
        # TODO: Get Exception and Error naming figured out.
        piece.download(piece_offset, message.payload[8:])
        return piece.completed

