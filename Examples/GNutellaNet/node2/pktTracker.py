import time

class pktTracker:
    '''
    An object of the pktTracker class track the pkt send for all address of the near peer.
    It is useful for check if send a pkt at one peer.
    '''

    def __init__(self, listen_time=300):
        self.pkt4peer = {} # {(IPP2P,PP2P): [(pktid_1,timestamp), (pktid_2,timestamp), ...]}
        self.listen_time = listen_time

    def check_pkt(self, pktid, addr):
        '''
        check_pkt(pktid, addr)
        pktid is a string with the pkt id.
        addr is a 2-tuple with (IPP2P,PP2P).
        IPP2P must be a string with IP_v6|IP_v4
        '''
        
        self._refresh()

        if addr not in self.pkt4peer.keys():
            self.pkt4peer[addr] = [ (pktid,int(time.time())) ]
            return True

        for pkt in self.pkt4peer[addr]:
            if pkt[0] == pktid:
                return False
        
        self.pkt4peer[addr].append( (pktid,int(time.time())) )
        return True

    def get_listen_time(self):
        return self.listen_time

    def _refresh(self):
        current_time = int(time.time())
        temp_pkt4peer = {}

        for key in self.pkt4peer.keys():
            for pkt in self.pkt4peer[key]:
                if (pkt[1]-current_time) < self.listen_time:
                    if key in temp_pkt4peer.keys():
                        temp_pkt4peer[key] = temp_pkt4peer[key].append(pkt)
                    else:
                        temp_pkt4peer[key] = [pkt]
        
        self.pkt4peer = temp_pkt4peer
