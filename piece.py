from hashlib import sha1

import constants
from message import Message, MessageType

"""Handles pieces, which divisions of the file being passed by the torrent."""


class PieceError(Exception):
    pass


def piece_factory(total_length, piece_length, hashes):
    """Creates the piece divisions for a given length and returns
    a generator object that will yield the pieces until they are all
    done."""
    num_pieces = (total_length // piece_length) + 1
    for i in range(num_pieces - 1):
        yield Piece(i, piece_length, hashes[i])
    yield Piece(num_pieces - 1, total_length % piece_length, hashes[num_pieces - 1])


class Piece:
    def __init__(self, piece_index, length, piece_hash):
        self.index = piece_index
        self.length = length
        self.hash = piece_hash
        self._downloaded_bytes = b''
        self.completed = False

    @property
    def bytes_downloaded(self):
        return len(self._downloaded_bytes)

    def download(self, offset, bytestring):
        """Pass this piece bytes which represent parts of it."""
        if offset != self.bytes_downloaded:
            raise PieceError("Offset Not Matching | {} {}".format(offset, self.bytes_downloaded))

        if len(bytestring) + self.bytes_downloaded > self.length:
            raise PieceError('Too Many Bytes for Piece | bytes_len: {} downloaded: {} limit: {}', len(bytestring),
                             self.bytes_downloaded, self.length)
        self._downloaded_bytes += bytestring
        if self.bytes_downloaded == self.length:
            self._complete()

    def get_next_request_message(self):
        """Get the request that will cover the next set of bytes that
        the piece requires

        Format of a request payload:
        <4-byte piece index><4-byte block offset><4-byte length>
        """
        if self.completed:
            raise PieceError("Piece Is Already Completed")

        request_length = min(constants.REQUEST_LENGTH, self.length - self.bytes_downloaded)
        index_bytes = int.to_bytes(self.index, length=4, byteorder='big')
        offset_bytes = int.to_bytes(self.bytes_downloaded, length=4, byteorder='big')
        length_bytes = int.to_bytes(request_length, length=4, byteorder='big')
        request_payload = index_bytes + offset_bytes + length_bytes

        return Message(MessageType.REQUEST, request_payload)

    def writeout(self, file):
        file.write(self._downloaded_bytes)

    def _complete(self):
        if not self._is_hash_valid():
            raise PieceError("Piece Has a Bad Hash")
            # TODO: When the client receives this error, it should recreate a piece
            #       and request it from a different peer.
        # TODO: Consider writing the bytes to a temp_file, which can be pulled back
        #       out via writeout. Then deleted.
        self.completed = True

    def _is_hash_valid(self):
        """Checks hash value for downloaded bytes vs the expected"""
        downloaded_hash = sha1(self._downloaded_bytes).digest()
        return downloaded_hash == self.hash

    def __repr__(self):
        return 'Piece With Index {}'.format(self.index)

    def __lt__(self, other):
        return self.index < other.index
