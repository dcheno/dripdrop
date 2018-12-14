import os
from hashlib import sha1

from bencode3 import bdecode, bencode

"""Handle data related to a torrent and its torrent file"""
class TorrentException(Exception):
    pass

class Torrent:
    """Hold information coming from a torrent file."""
    def __init__(self, tor_file_path):
        self.path = tor_file_path
        self.file_name = os.path.basename(tor_file_path)
        self.name = os.path.splitext(self.file_name)[0]
        self._handle_file(self.path)

    def _handle_file(self, tor_file_path):
        with open(tor_file_path, 'rb') as tor_file:
            metainfo = tor_file.read()

        metadict = bdecode(metainfo)
        self.info = metadict['info']
        self.info_hash = self._hash_info(self.info)
        self.announce = metadict['announce']
        self.length = self.info['length']
        self.piece_length = self.info['piece length']
        # The pieces entry consists of 20 byte hash values for each pieces.
        # TODO: Store hash values of pieces so that we can check against them.
        self.num_pieces = len(self.info['pieces'])//20

    @staticmethod
    def _hash_info(info):
        info_bencode = bencode(info)
        info_hash = sha1(info_bencode).digest()
        return info_hash
