from struct import pack

import constants
from message import Message, MessageType

"""Handles pieces, which divisions of the file being passed by the torrent."""

class PieceError(Exception):
    pass

def piece_factory(total_length, piece_length):
    """Creates the piece divisions for a given length and returns
    a generator object that will yield the pieces until they are all
    done."""
    print('piece_factory', total_length, piece_length)
    num_pieces = (total_length // piece_length) + 1
    print('piece_factory, num_pieces:', num_pieces)
    for i in range(num_pieces - 1):
        print('piece_factory, yield', i)
        yield Piece(i, piece_length)
    print('piece_factory, yield, t/p:', total_length % piece_length)
    yield Piece(num_pieces - 1, total_length % piece_length)


class Piece:
    def __init__(self, piece_index, length):
        self.index = piece_index
        self.length = length
        self._downloaded_bytes = b''
        self.completed = False

    @property
    def bytes_downloaded(self):
        return len(self._downloaded_bytes)

    def download(self, offset, bytestring):
        """Pass this piece bytes which represent parts of it."""
        print('"Downloading" piece.')
        if offset != self.bytes_downloaded:
            raise PieceError("Offset Not Matching | {} {}".format(offset, self.bytes_downloaded))

        if len(bytestring) + self.bytes_downloaded > self.length:
            raise PieceError('Too Many Bytes for Piece | bytes_len: {} downloaded: {} limit: {}', len(bytestring),
                             self.bytes_downloaded, self.length)
        self._downloaded_bytes += bytestring
        if self.bytes_downloaded == self.length:
            # FIXME: Change this to have a complete method, which checks the hash, does stuff with the file etc.
            self.completed = True

    def get_next_request_message(self):
        """Get the request that will cover the next set of bytes that
        the piece requires

        Format of a request payload:
        <4-byte piece index><4-byte block offset><4-byte length>
        """
        if self.completed:
            raise PieceError("Piece Is Already Completed")

        request_length = min(constants.REQUEST_LENGTH, self.length - self.bytes_downloaded)
        print('req length:', request_length)
        index_bytes = int.to_bytes(self.index, length=4, byteorder='big')
        offset_bytes = int.to_bytes(self.bytes_downloaded, length=4, byteorder='big')
        length_bytes = int.to_bytes(request_length, length=4, byteorder='big')
        request_payload = index_bytes + offset_bytes + length_bytes

        return Message(MessageType.REQUEST, request_payload)

    def check_hash(self):
        # TODO: This should check the validity of the sent data by
        #       comparing the hash of the piece to the provided hash
        #       from the torrent file.
        pass

    def __repr__(self):
        return 'Piece With Index {}'.format(self.index)



