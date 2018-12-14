import unittest
import pickle

from tracker import Tracker, TrackerEvent
from client import Client
from message import MessageParser, MessageType, _strip_message
from peer import Peer
from torrent import Torrent

class TrackerTests(unittest.TestCase):
    def setUp(self):
        c = Client()
        c.add_torrent('test.torrent')
        self.t = Tracker(c._torrent.announce, c._torrent.info_hash)
        with open('saved_init_response.p', 'rb') as f:
            self.start_response = pickle.load(f)

    def test_handle_response(self):
        attempt = self.t._handle_response(TrackerEvent.STARTED, self.start_response)
        
        self.assertEqual(self.t.interval, 1800, 'Bad Interval')
        self.assertEqual(self.t.min_interval, 1800, 'Bad Min Interval')

        complete = attempt['complete']
        self.assertEqual(complete, 13, 'Bad Complete')
        incomplete = attempt['incomplete']
        self.assertEqual(incomplete, 2, 'Bad Incomplete')
        peers = attempt['peers']
        self.assertEqual(len(peers), 15, peers)

class MessageTests(unittest.TestCase):
    def test_message_parser(self):

        # Tests in case of two messages
        bytestring = b'\x00\x00\x00\x03\x05\xff\x80\x00\x00\x00\x01\x01'
        m = MessageParser()
        messages = m(bytestring)

        message1 = next(messages)
        message2 = next(messages)

        print(message1)
        self.assertEqual(message1.type, MessageType.BITFIELD)
        self.assertEqual(message1.payload, b'\xff\x80')
        self.assertEqual(message2.type, MessageType.UNCHOKE)

        # Test in case of Keep Alive
        ka = m(b'\x00\x00\x00\x00')
        self.assertEqual(next(ka).type, MessageType.KEEP_ALIVE)

        # Test in case of incomplete message and later fulfillment
        message_half1 = b'\x00\x00\x00\x03'
        message_half2 = b'\x05\xff\x80'

        inc = MessageParser()
        attempt1 = inc(message_half1)

        answers = []
        for m in attempt1:
            answers.append(m)

        self.assertFalse(answers, "Shouldn't be any answers.")

        attempt2 = inc(message_half2)

        for m in attempt2:
            answers.append(m)

        self.assertTrue(len(answers) == 1, "Should be one complete message.")
        self.assertEqual(answers[0].type, MessageType.BITFIELD)
        self.assertEqual(answers[0].payload, b'\xff\x80')

    def test_strip_message(self):
        a = b'12345678910'
        b, c = _strip_message(a, 4)
        self.assertEqual(b, b'1234')
        self.assertEqual(c, b'5678910')

        with self.assertRaises(ValueError):
            _strip_message(a, 12)

        print("I did it?")

class PeerTests(unittest.TestCase):
    def setUp(self):
        t = Torrent('portrait.torrent')
        self.peer = Peer('-DD00011234567891234', '127.0.0.1', 8201, t)

    def test_bitfield_handle(self):
        self.peer._handle_bitfield(b'\xc0')
        self.assertEqual(self.peer.pieces, {0,1}, 'We should have pieces 1 and 2')

        self.peer.torrent.num_pieces = 23
        self.peer.pieces = set()
        """
        01000001 11000000 0010010 0
        65 = b'A'
        192 = b'\xc0'
        36 = b'$'
        """
        self.peer._handle_bitfield(b'A\xc0$')
        self.assertEqual(self.peer.pieces, {1,7,8,9,18,21}, 'Should render these pieces')
        self.peer.torrent.num_pieces = 2

        self.peer.torrent.num_pieces = 8
        self.peer.pieces = set()
        self.peer._handle_bitfield(b'\x01')
        self.assertEqual(self.peer.pieces, {7}, 'Should just be the one')
        self.peer.torrent.num_pieces = 2

if __name__ == '__main__':
    unittest.main()
    
        
"""
\x00\x00\x00\x03\x05\xff\x80\x00\x00\x00\x01\x01

length: \x00\x00\x00\x03
x05\xff\x80\x00\x00\x00\x01\x01

payload: x05\xff\x80\
\x00\x00\x00\x01\x01

length: \x00\x00\x00\x01\
payload: \x01
"""