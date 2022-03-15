import time

class pktTracker:

    def __init__(self):
        self.pkt4peer = {} # {(IPP2P,PP2P): [(pktid_1,timestamp), (pktid_2,timestamp), ...]}

    def add_pkt(self, pktid, addr):
        '''
        add_pkt(pktid, addr)
        pktid is a string with the pkt id.
        addr is a 2-tuple with (IPP2P,PP2P).
        IPP2P must be a string with IP_v6|IP_v4
        '''

        # self.pkt4peer[addr] = 

    def _refresh(self):
        current_time = int(time.time())
        temp_pkt4peer = {}

        for key, pkt_list in self.pkt4peer:
            for pkt in pkt_list:
                if (pkt[1]-current_time) < 200:
                    if key in temp_pkt4peer.keys():
                        temp_pkt4peer[key] = temp_pkt4peer[key].append(pkt)
                    else:
                        temp_pkt4peer[key] = [pkt]
        
        self.pkt4peer = temp_pkt4peer
