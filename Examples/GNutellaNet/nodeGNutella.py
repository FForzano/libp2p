from multiprocessing.dummy import connection
from nodeP2P import nodeP2P
from pktTracker import pktTracker
from utils import recvall
import os
from pktTracker import pktTracker

class nodeGNutella(nodeP2P):
    shared_files = {} # {md5:file_name}
    near_peer = [] # [addr1,addr2,...] --> addr=(IP,Port:int)
    pktid_track = pktTracker(listen_time=300)

    def __init__(self,IPP2P_v4,IPP2P_v6,PP2P):
        super().__init__(IPP2P_v4,IPP2P_v6,PP2P)
    
    def server_function(self, connection, address):

        # modify address
        #

        while not self.quitEvent.isSet():
            try:
                instruction = recvall(connection,4).decode()

                if instruction == "":
                    continue

                elif instruction == "RETR":
                    self._function_RETR_server(connection)

                elif instruction == "QUER":
                    self.near_peer = self.NEAR_research()
                    self._function_QUER_server(connection, address)

                elif instruction == "NEAR":
                    self.near_peer = self.NEAR_research()
                    self._function_NEAR_server(connection, address)

                # elif instruction == "AQUE":
                #     self._function_AQUE_server(connection)

                # elif instruction == "ANEA":
                #     self._function_ANEA_server(connection)
            
            except Exception:
                pass
            finally:
                if not connection is None:
                    connection.close()
            

    def client_function(self):
        pass


    def _function_RETR_server(self, connection):
        max_chunk_size = 1024
        f = None
        try:
            md5 = recvall(connection,32).decode()

            name = self.shared_files[md5]

            f = open(name,"rb")
            f.seek(0)
            
            fsize = os.path.getsize(name)
            out = "ARET" + ('%06d' %(int(fsize/max_chunk_size)+1))
            connection.sendall(out.encode())

            chunk = f.read(max_chunk_size)
            
            while chunk:
                out = '%05d' %(len(chunk))
                out = out.encode() + chunk
                connection.sendall(out.encode())
                chunk = f.read(max_chunk_size)

        except Exception as e:
            print("\n")
            print(e)
            print("Aborting download...")
        finally:
            if not f is None:
                f.close()
            connection.close()

    def _function_QUER_server(self, connection, mit_address):
        rensponse_socket = None
        try:
            pktid = recvall(connection, 16).decode()
            IPP2P = recvall(connection,55).decode()
            PP2P = recvall(connection, 5).decode()
            TTL = int(recvall(connection, 2))
            research = recvall(connection,20).decode()
            research = research.strip()
            connection.close()

            # pkt forward
            if TTL != 1:
                self._forward_pkt(pktid,(IPP2P,int(PP2P)),TTL-1,research, mit_address) # dovrò probabilmente passare anche da chi ho ricevuto il pacchetto
            
            # check for file and send the answer
            for md5,file_name in self.shared_files:
                if research in file_name:
                    rensponse_socket = self.connect2peer((IPP2P,int(PP2P)))
                    rensponse_socket.send(b'AQUE')
                    rensponse_socket.send(pktid.encode())
                    IP = self.IPP2P_v4 + self.IPP2P_v6
                    rensponse_socket.send(IP.encode())
                    rensponse_socket.send(self.PP2P)
                    rensponse_socket.send(md5)
                    rensponse_socket.sendall(file_name.ljust(100))

                    rensponse_socket.close()

        except Exception as e:
            print("Error occurs during file query.")
            print(e)
        finally:
            if not connection is None:
                connection.close()
            if not rensponse_socket is None:
                rensponse_socket.close()

    def _function_NEAR_server(self, connection, mit_address):
        rensponse_socket = None
        try:
            pktid = recvall(connection, 16).decode()
            IPP2P = recvall(connection,55).decode()
            PP2P = recvall(connection, 5).decode()
            TTL = int(recvall(connection, 2))

            # pkt forward
            if TTL != 1:
                self._forward_pkt(pktid,(IPP2P,int(PP2P)),TTL-1, mit_address)
            
            # answer
            rensponse_socket = self.connect2peer((IPP2P,int(PP2P)))
            rensponse_socket.send(b'ANEA')
            rensponse_socket.send(pktid.encode())
            IP = self.IPP2P_v4 + self.IPP2P_v6
            rensponse_socket.send(IP.encode())
            rensponse_socket.send(self.PP2P)

        except Exception as e:
            print("Error occurs during file query.")
            print(e)
        finally:
            if not connection is None:
                connection.close()
            if not rensponse_socket is None:
                rensponse_socket.close()

    def _forward_pkt(self, pktid, addr, TTL, research, mittent):
        connection_socket = None

        if research != "":
            research = research.ljust(20)
            

            # BISOGNERÀ FARE IN MODO CHE NON REINVII AL MITTENTE
            for near in self.near_peer:
                if not self.is_same_peer(near,mittent):
                    try:
                        if self.pktid_track.check_pkt(pktid,near):
                            connection_socket = self.connect2peer(near)
                            connection_socket.send(b'QUER')
                            connection_socket.send(pktid.encode())
                            connection_socket.send(addr[0].encode())
                            connection_socket.send(addr[1].encode())
                            TTL_string = '%02d' %TTL
                            connection_socket.send(TTL_string.encode())
                            connection_socket.sendall(research)

                    except Exception:
                        pass
                    finally:
                        if not connection_socket is None:
                            connection_socket.close()
        
        else: 
            for near in self.near_peer:
                if not self.is_same_peer(near,mittent):
                    try:
                        if self.pktid_track.check_pkt(pktid,near):
                            connection_socket = self.connect2peer(near)
                            connection_socket.send(b'NEAR')
                            connection_socket.send(pktid.encode())
                            connection_socket.send(addr[0].encode())
                            connection_socket.send(addr[1].encode())
                            TTL_string = '%02d' %TTL
                            connection_socket.sendall(TTL_string.encode())

                    except Exception:
                        pass
                    finally:
                        if not connection_socket is None:
                            connection_socket.close()

    def NEAR_research():
        pass

    def is_same_peer(mittent, addr):
        [addr4,addr6] = addr[0].split('|')
        port = addr[1]

        if mittent[0] == addr4 or mittent[0] == addr6:
            if mittent[1] == port:
                return True
        
        return False