from enum import Enum
from struct import unpack

import requests
from bencode3 import bdecode, bencode

import constants


class TrackerEvent(Enum):
    STARTED = 'started'
    STOPPED = 'stopped'
    COMPLETED = 'completed'
    
    
class Tracker:
    """Represents a HTTP Torrent Tracker, which is the service that 
       connects the client to peers for download"""
    def __init__(self, announce, info_hash):
        self.announce = announce
        self.info_hash = info_hash
        # self.info_hash = bencode_and_hash(info)

    def request(self, event, peer_id, port):
        """Request information from the tracker.
        
        Args:
            event (tracker even enum): tells the tracker what kind
                of event is happening.
            peer_id (20-byte string): id of the client requesting.
            port: port number that the client is listening on.
        Returns:
            A decoded dictionary of the response.
        """
        if event == TrackerEvent.STARTED:
            left = 0
        else:
            left = 0
        params = self._prepare_params(event, peer_id, port, left)
        r = requests.get(self.announce, params=params)

        handled_response = self._handle_response(r.content)
        return handled_response
    
    def _prepare_params(self, event, peer_id, port, left):
        """Organize params for HTTP Tracker request

        Returns:
            A dictionary with key value pairs that represent
            HTTPs URL parameters.
        """
        params = {
            'info_hash': self.info_hash,
            'peer_id': peer_id,
            'event': event.value,
            'port': port,
            'left': left
        }

        return params

    def _handle_response(self, response):
        """Parse the tracker response and return decoded dictionary
        and make necessary state changes to tracker"""
        # TODO: Implement Updating the Tracker on our status.

        # Decode the response
        response_dict = bdecode(response)

        # Check if tracker_id should be updated.
        if response_dict.get('tracker id'):
            self.tracker_id = response_dict['tracker id']

        self.interval = response_dict.get('interval', 1800)
        self.min_interval = response_dict.get('min interval', self.interval)
            
        # Handle list of peers
        peers = response_dict['peers']
        if isinstance(peers, list):
            self.peers = peers
        else:
            response_dict['peers'] = self._parse_binary_peers(peers)
        return response_dict

    @staticmethod
    def _parse_binary_peers(peers):
        """Handle compact binary peer data. Return as a list
        of dictionaries."""
        peer_list = []
        
        if len(peers) % constants.PEER_BYTE_LENGTH:
            raise ValueError('Bad Peer Length')

        num_peers = len(peers)//constants.PEER_BYTE_LENGTH

        for i in range(num_peers):
            start_index = i * constants.PEER_BYTE_LENGTH
            end_index = start_index + constants.PEER_BYTE_LENGTH
            peer_bytes = peers[start_index:end_index]
            ip_bytes = peer_bytes[:constants.PEER_IP_LENGTH]

            addr_parts = []
            for byte in ip_bytes:
                addr_parts.append(int(byte))

            ip = '.'.join([str(b) for b in addr_parts])

            port_bytes = peer_bytes[constants.PEER_IP_LENGTH:]
            port = unpack('!H', port_bytes)[0]
    
            peer_list.append({'ip': ip, 'port': port})

        return peer_list
    
    """
    info_hash: urlencoded 20-byte SHA1 hash of the value of the info
        key from the Metainfo file (.torrent file), value will
        be a bencoded dictionary

    peer_id: urlencoded 20-byte string, can be anything, but should
        at least be unique to the machine.

    port: port number that the client is listening on. Typically
        between 6881-6889

    uploaded: total amount uploaded since client sent 'started'
        event to the tracker (base ten ASCII). Should be total
        number of bytes.

    downloaded: total amount downloaded since the client sent
        the 'started' event to the tracker (base ten ASCII).
        Total number of bytes.

    left: The number of bytes the client still has to download.
        (Base ten ASCII)
    
    compact: 1 means that the client accepts a compact response.
        The peer list is replaced by a peer string with 6 bytes
        per peer. The first 4 bytes are the host (in network byte
        order). Some trackers only support compact responses!

    no_peer_id: indicates that the tracker can omit peer id field in
        peers dictionary.

    event: if specified, then must be started, completed, or stopped.
        If not specified, is a regular request.
            started: the first request to the tracker.
            stopped: sent to the tracker if client is shutting down
                gracefully.
            completed: sent when the download completes. Should not
                be sent if the download was already 100% when the
                client started.
    ip: (optional) The true IP address of the client machine.

    numwant: (optional) Number of peers the client wants.

    key: (optional) additional id that is not shared with other peers
        could be used to reidentify the tracker if IP changes.

    trackerid: (optional) If a previous announce contained a tracker
        id it should be set here.
    
    """
