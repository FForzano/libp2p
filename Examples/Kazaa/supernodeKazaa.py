from nodeKazaa import nodeKazaa
from pktTracker import pktTracker
from utils import recvall
import os
from pktTracker import pktTracker
import ipaddress, hashlib, threading, random, socket, time, sys
from string import ascii_uppercase, digits
from portFinder import portFinder

class supernodeKazaa(nodeKazaa):
    def __init__(self,IPP2P_v4,IPP2P_v6, near_file):
        super().__init__(IPP2P_v4,IPP2P_v6,'03000', near_file)
        self.logged_peers = {}
        self.peer4files = {}
        self.file_names = {}
    
    def _function_SUPE_server(self, connection, mit_address):
        try:
            pktid = recvall(connection, 16).decode()
            ip = recvall(connection, 55).decode()
            port = recvall(connection, 5).decode()
            ttl = recvall(connection, 2).decode()

            self._forward_pkt(pktid, (ip, int(port)), int(ttl)-1, "_supe_research", mit_address)

            response_socket = self.connect2peer( (ip.split('|')[random.choice([0,1])], int(port)) )
            response_socket.sendall( b'ASUP' + pktid.encode() + self.IPP2P_v4.encode() + b'|' + self.IPP2P_v6.encode() + self.PP2P.encode() )
            response_socket.close()
        except Exception as e:
            print("Error occurs during supe server elaboration.")
            print("$>", end='')
            sys.stdout.flush()
        finally:
            if not connection is None:
                connection.close()

    def _function_LOGI_server(self, connection):
        try:
            ip = recvall(connection,55).decode()
            port = int(recvall(connection,5).decode())

            if (ip,'%05d' %port) in self.logged_peers.values():
                # return SessionId
                for key,value in self.logged_peers.items():
                    if value == (ip,'%05d' %port):
                        msg=b'ALGI' + key.encode()
                        break

            else:
                # If is not logged jet
                letters = ascii_uppercase + digits
                SessionId = ''.join(random.choice(letters) for i in range(16))
                # SessionId must be unique:
                while SessionId in self.logged_peers.keys():
                    SessionId = ''.join(random.choice(letters) for i in range(16))
                
                with self.lock:
                    self.logged_peers[SessionId] = (ip,'%05d' %port)
                msg=b'ALGI' + SessionId.encode()
                #return SessionId
            
            connection.sendall(msg)

        except Exception:
            msg = b'ALGI' + '0000000000000000'.encode()
            connection.sendall(msg)

        finally:
            if not connection is None:
                connection.close()

    def _function_ADFF_server(self, connection):
        try:
            sessionid = recvall(connection, 16).decode()
            filemd5 = recvall(connection, 32).decode()
            filename = recvall(connection, 100).decode()

            # loggin control
            if sessionid not in self.logged_peers.keys():
                connection.close()
                return

            else:
                # Actions for logged users

                if filemd5 in self.peer4files.keys():
                    # if the file is in the directory jet
                    if sessionid in self.peer4files[filemd5]:
                        # if the user is not listed jet
                        with self.lock:
                            self.file_names[filemd5] = filename
                    else:
                        with self.lock:
                            self.peer4files[filemd5].append(sessionid)
                            self.file_names[filemd5] = filename
                else:
                    # if the file in not in the directory jet
                    with self.lock:
                        self.peer4files[filemd5] = [sessionid]
                        self.file_names[filemd5] = filename
        except Exception as e:
            print("Error occurs during add file operations")
            print("$>", end='')
            sys.stdout.flush()
        finally:
            if not connection is None:
                connection.close()

    def _function_DEFF_server(self, connection):
        try:
            sessionid = recvall(connection, 16).decode()
            filemd5 = recvall(connection, 32).decode()

            # loggin control
            if sessionid not in self.logged_peers.keys():
                connection.close()
                return

            else:
                if filemd5 not in self.peer4files.keys():
                    connection.close()
                    return
                
                elif sessionid not in self.peer4files[filemd5]:
                    connection.close()
                    return

                else:
                    # It is possible to remove the file
                    with self.lock:
                        self.peer4files[filemd5].remove(sessionid)
                        if not self.peer4files[filemd5]:
                            print("deleting dictionary record...")
                            print("$>", end='')
                            sys.stdout.flush()

                            del self.peer4files[filemd5]
                            del self.file_names[filemd5]

        except Exception as e:
            print("Error occurs during add file operations")
            print("$>", end='')
            sys.stdout.flush()
        finally:
            if not connection is None:
                connection.close()

    def _function_LOGO_server(self, connection):
        try:
            sessionid = recvall(connection, 16).decode()

            # login control
            if sessionid not in self.logged_peers.keys():
                # If peer is not logged, the null answer is sent.
                resp = b'ALGO' + b'000'
                connection.sendall(resp)

            else:
                deleted = self._logout(sessionid)
                deleted_string = '%03d' %deleted
                connection.sendall(b'ALGO' + deleted_string.encode())
            
            # print("logged peer: ", self.logged_peer)
            # print("peers for file: ", self.peer4files)
        except Exception:
            print("Error occurs in logout operations.")
            print("$> ", end='')
            sys.stdout.flush()
        finally:
            if not connection is None:
                connection.close()

    def _function_FIND_server(self, connection):
        try:
            sessionid = recvall(connection, 16).decode()
            research_string = recvall(connection, 20).decode()

            # loggin control
            if sessionid not in self.logged_peers.keys():
                # If peer is not logged, the null answer is sent.
                connection.sendall(b'AFIN' + b'000')

            # The finded files from other supernodes
            self.finded_files = {} # md5:[file_name, [(ip,port), (ip,port), ...] ]
            
            # Send the query at every supernode
            letters = ascii_uppercase + digits
            pktid = ''.join(random.choice(letters) for i in range(16))
            port = '%05d' %self.port_generator.give_port()
            self.pktid_track.check_pkt(pktid) # serve solo per evitare reinvii da parte mia
            
            research_thread = threading.Thread(target=self._quer_research_thread, args=(port,))
            research_thread.start()

            pkt = b'QUER' + pktid.encode() + self.IPP2P_v4.encode() + "|".encode() + self.IPP2P_v6.encode() + port.encode() + "10".encode() + research_string.ljust(20).encode()
            for peer in self.supernodes:
                try:
                    connection = self.connect2peer( (peer[0].split('|')[random.choice([0,1])], peer[1]) )
                    connection.sendall(pkt)
                except Exception:
                    pass
                finally:
                    connection.close()

            research_thread.join()

            # Here i have self.finded_files of the other peer's files

            for file_md5,file_n in self.file_names.items():
                if research_string.lower().strip() in file_n.lower().strip():

                    # add the md5 file, the relative name and the number of copy to the answer
                    if file_md5 not in self.finded_files.keys():
                        self.finded_files[file_md5] = [file_n.ljust(100), []]
                        for peer_SID in self.peer4files[file_md5]:
                            self.finded_files[file_md5][1].append( (self.logged_peers[peer_SID][0], self.logged_peers[peer_SID][1]) )

                    else:
                        self.finded_files[file_md5][0] = file_n.ljust(100)
                        for peer_SID in self.peer4files[file_md5]:
                            self.finded_files[file_md5][1].append( (self.logged_peers[peer_SID][0], self.logged_peers[peer_SID][1]) )

            # invio tutto
            
            connection.send(b'AFIN')

            # self.finded_files = {} --> {md5:[file_name, [(ip,port), (ip,port), ...] ]}
            idmd5 = len( self.finded_files.keys() )
            idmd5_string = '%03d' %idmd5
            connection.send( idmd5_string.encode() )

            for md5, info in self.finded_files.items():
                connection.send( md5.encode() )
                connection.send( info[0].encode() )
                n_copy = '%03d' %len(info[1])
                connection.send( n_copy.encode() )

                for peer in info[1]:
                    connection.send( peer[0].encode() )
                    pp = '%05d' %int(peer[1])
                    connection.sendall( pp.encode() )
        
        except Exception:
            print("Error in find server elaboration.")
            print("$> ", end='')
            sys.stdout.flush()
        finally:
            if not connection is None:
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

            if self.pktid_track.check_pkt(pktid):
                # pkt forward
                if TTL != 1:
                    self._forward_pkt(pktid,(IPP2P,int(PP2P)),TTL-1,research, mit_address) 
                
                # check for file and send the answer
                for md5 in self.shared_files.keys():
                    if research in self.shared_files[md5].strip():
                        rensponse_socket = self.connect2peer((IPP2P.split('|')[random.choice([0,1])],int(PP2P)))
                        rensponse_socket.send(b'AQUE')
                        rensponse_socket.send(pktid.encode())
                        IP = self.IPP2P_v4 + "|" + self.IPP2P_v6
                        rensponse_socket.send(IP.encode())
                        rensponse_socket.send(self.PP2P.encode())
                        rensponse_socket.send(md5.encode())
                        rensponse_socket.sendall(self.shared_files[md5].ljust(100).encode())

                        rensponse_socket.close()

        except Exception as e:
            print("Error occurs during query server elaboration.")
            print("$>", end='')
            sys.stdout.flush()
        finally:
            if not connection is None:
                connection.close()
            if not rensponse_socket is None:
                rensponse_socket.close()


    def select_supernode(self):
        letters = ascii_uppercase + digits
        pktid = ''.join(random.choice(letters) for i in range(16))
        self.pktid_track.check_pkt(pktid) # serve solo per evitare reinvii da parte mia

        self.supernodes = []

        pkt = b'SUPE' + pktid.encode() + self.IPP2P_v4.encode() + "|".encode() + self.IPP2P_v6.encode() + self.PP2P.encode() + "4".encode()
        for peer in self.near_peer:
            try:
                connection = self.connect2peer( (peer[0].split('|')[random.choice([0,1])], peer[1]) )
                connection.sendall(pkt)
            except Exception:
                pass
            finally:
                connection.close()
        
        for i in range(10):
            print("#", end='')
            sys.stdout.flush()
            time.sleep(2)
        print("")

        self.my_supernode = (self.IPP2P_v4 + '|' + self.IPP2P_v6, int(self.PP2P))
        print("Selected supernode is:")
        print("\tIPv4|IPv6:", self.my_supernode[0], "\tPort:", self.my_supernode[1])

    def _logout(self, sessionid):
        '''
        logout(sessionid)
        logout execute the logout of the sessionid peer. All its files are removed and the 
        number of deleted file is returned.
        '''

        del_num = 0
        with self.lock:
            del self.logged_peers[sessionid]
            temp_peer4files = {}
            temp_file_names = {}

            for file,peers in self.peer4files.items():
                if sessionid in peers:
                    self.peer4files[file].remove(sessionid)
                    del_num += 1
                    if self.peer4files[file]:
                        temp_peer4files[file] = self.peer4files[file]
                        temp_file_names[file] = self.file_names[file]
                else:
                    temp_peer4files[file] = self.peer4files[file]
                    temp_file_names[file] = self.file_names[file]
            self.peer4files = temp_peer4files
            self.file_names = temp_file_names

        return del_num


    def _quer_research_thread(self, port):
        try:
            if socket.has_dualstack_ipv6():
                server_sock = socket.create_server(("", int(port)), family=socket.AF_INET6, dualstack_ipv6=True)
            else:
                print("Dual stack not avaible.")
                print("$> ", end='')
                sys.stdout.flush()
                server_sock = socket.create_server(("", int(port)))
        except Exception:
            pass
        
        start_time = int(time.time())
        received_peer = []

        server_sock.settimeout(3)
        conn = None
        while((int(time.time()) - self.pktid_track.get_listen_time()) < start_time):
            try:
                conn,addr = server_sock.accept()

                recvall(conn,4)
                recvall(conn,16)
                ip_complete = recvall(conn,55).decode()

                port = int(recvall(conn,5).decode())
                file_md5 = recvall(conn,32).decode()
                file_name = recvall(conn,100).decode().strip()
                received_peer.append( (ip_complete, port, file_md5, file_name) )
            except:
                pass
            finally:
                if conn:
                    conn.close()
        
        for response in received_peer:
            if response[2] not in self.finded_files.keys():
                self.finded_files[response[2]] = [response[3].ljust(100), [ (response[0], response[1]) ]]
            else:
                self.finded_files[response[2]][0] = response[3].ljust(100)
                self.finded_files[response[2]][1].append( (response[0], response[1]) )