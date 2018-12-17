from twisted.internet import reactor

from tracker import Tracker, TrackerEvent
from torrent import Torrent
from message import MessageType, Message
from piece import piece_factory
from peer import Peer, PeerError, PeerConnectionError
import constants

"""Represent a client to connect to the BitTorrent swarm"""


class ClientError(Exception):
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
        self._torrent = None
        self.complete = False

    def add_torrent(self, tor_file_path):
        """Give the Client at Torrent to use."""
        if self._torrent:
            raise ClientError('Client already has a Torrent')
        else:
            self._torrent = Torrent(tor_file_path)
            self.unrequested_pieces = piece_factory(self._torrent.length, self._torrent.piece_length, self._torrent.piece_hashes)

    def start_torrent(self):
        """Begin the torrent process by contacting the Tracker and
        waiting for the response."""
        if not self._torrent:
            raise ClientError('Client Has Not Been Assigned Torrent')
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
        """
        peers = response['peers']
        self._try_peers(peers)

    def _try_peers(self, peers):
        """Loops through the list of peers and tries to connect to them (only
        one at a time right now).

        TODO: We're currently connecting to multiple peers, but not coordinating the work we send
              well.
        """
        for peer_entry in peers:
            if peer_entry['id'] == self.peer_id:
                continue

            print('Trying peer: {}'.format(peer_entry))
            peer = Peer(peer_entry['id'], peer_entry['ip'], peer_entry['port'], self._torrent)
            try:
                peer.connect(self.peer_id)
            except PeerConnectionError:
                continue
            else:
                self._peers.append(peer)
                peer.subscribe_for_messages_to_client(self.peer_message_receiver(peer))

    def peer_message_receiver(self, peer):
        def handle_peer_message(message):
            # 1. First we wait for the handshake. Then we express interest.
            if not peer.hands_shook:
                # We don't do anything with someone who hasn't shaken our hand.
                msg = "Peer is sending messages without shaking our hand."
                raise PeerError(msg)

            if peer.is_choking:
                peer.message_peer(Message.factory(MessageType.INTERESTED))  # Possibly this
                # message passing should be replaced by method calls (ie, peer.show_interest()).
                # But that could happen later.
                # It is impolite to do anything before the peer has unchoked us.
                return

            if not peer.working_on_piece and peer.pieces and len(self.pieces) < self._torrent.num_pieces:
                self._request_next_piece(peer)
                return

            # If the message is a piece message find the appropriate piece and add to it.
            if message.type == MessageType.PIECE:
                complete = self._handle_piece_message(message)
                if complete:
                    peer.working_on_piece = False
                    if len(self.pieces) < self._torrent.num_pieces:
                        self._request_next_piece(peer)
                        return
                    else:
                        self._complete()

        return handle_peer_message

    def _request_next_piece(self, peer):
        next_piece = next(self.unrequested_pieces)
        peer.message_peer(next_piece.get_next_request_message())
        self.pieces.append(next_piece)
        peer.working_on_piece = True

    def _handle_piece_message(self, piece_message):
        """Take in a Piece Message and route the data to the
        appropriate Piece Object

        Returns:
            True if the piece is now completed.
            False if not.
        """
        piece = None
        for p in self.pieces:
            if p.index == piece_message.index:
                piece = p

        if not piece:
            raise ClientError("Peer sending unrequested piece")
        piece.download(piece_message.offset, piece_message.payload)
        return piece.completed

    def _complete(self):

        for peer in self._peers:
            peer.close_connection()

        self.pieces.sort()
        with open(self._torrent.target_file_name, 'wb') as target_file:
            for piece in self.pieces:
                piece.writeout(target_file)
        self.complete = True
        reactor.stop()
        print('File Has Completed Downloading')
