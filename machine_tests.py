import unittest
import pickle
from hashlib import sha1


from tracker import Tracker, TrackerEvent
from client import Client
from peer import Peer

class TrackerTests(unittest.TestCase):
    def test_it(self):
        c = Client()
        c.add_torrent('wishtorrent.torrent')
        c.start_torrent()

        # input(":")
        # # id = '-qB3370-S3JQ-V0CGp45'
        # id = '-DE13D0-2FGasdxJ7AE5'#input('id:')
        # # port = 8999
        # port = 8201 # int(input('port:'))
        # ip = '127.0.0.1' # input('ip:')
        #
        # p = Peer(id, ip, port, c._torrent)
        # c._connect_peer(p)
        #
        # # c._peers[0].start_listening()
        

    
if __name__ == '__main__':
    unittest.main()
    
        
