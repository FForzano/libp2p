from nodeP2P import nodeP2P
from pktTracker import pktTracker
from utils import recvall
import os
from pktTracker import pktTracker
import ipaddress, hashlib, threading, random, socket, time, sys
from string import ascii_uppercase, digits
from portFinder import portFinder

class nodeGNutella(nodeP2P):
    shared_files = {} # {md5:file_name}
    near_peer = [('127.016.000.022|fc00:0000:0000:0000:0000:0000:0000:1004', 9001)] # [addr1,addr2,...] --> addr=(IP,Port:int)
    pktid_track = pktTracker(listen_time=10)

    def __init__(self,IPP2P_v4,IPP2P_v6,PP2P):
        super().__init__(IPP2P_v4,IPP2P_v6,PP2P)
        self.lock = threading.Lock()
        self.port_generator = portFinder(min_port=50000, max_port=60000)
    
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
                    # self.near_peer = self.NEAR_research()
                    self._function_QUER_server(connection, address)

                elif instruction == "NEAR":
                    # self.near_peer = self.NEAR_research()
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
        try:
            while True:
                try:
                    print("Avaible commands:")
                    print("\tSHARE: share new file;\n\tNEAR: find near peer;\n\tFIND: find a file;\n\tRETR: download a file.")

                    command = input("$> ")

                    if command == "SHARE":
                        file_name = input("Insert the file name: ")
                        file_md5 = ""
                        if len(file_name) > 100:
                            print("Please insert a name with length less then 100 characters")
                            continue
                        file = 0
                        try:
                            file = open(file_name,"rb")
                            file_md5 = hashlib.md5(file.read()).hexdigest()
                            file.close()
                        except FileNotFoundError:
                            print(file_name + " not found.")
                            continue
                        except Exception as e:
                            file.close()
                            print(e)
                            continue
                        self.shared_files[file_md5] = file_name
                                               

                    elif command == "NEAR":
                        self.NEAR_research()

                    elif command == "FIND":
                        pass

                    elif command == "RETR":
                        pass

                    else:
                        print("Invalid command.")

                except Exception as error:
                    print("Error occurs: ", error)
                    print("$> ", end='')
                    sys.stdout.flush()

        except KeyboardInterrupt:
            print("Bye!")


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
            print("$> ", end='')
            sys.stdout.flush()
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
                    IP = self.IPP2P_v4 + "|" + self.IPP2P_v6
                    rensponse_socket.send(IP.encode())
                    rensponse_socket.send(self.PP2P)
                    rensponse_socket.send(md5)
                    rensponse_socket.sendall(file_name.ljust(100))

                    rensponse_socket.close()

        except Exception as e:
            print("Error occurs during file query.")
            print("$> ", end='')
            sys.stdout.flush()
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
                self._forward_pkt(pktid,(IPP2P,int(PP2P)),TTL-1, "", mit_address)
            
            # answer
            IPP2P = IPP2P.split('|')
            rensponse_socket = self.connect2peer((IPP2P[random.choice([0,1])],int(PP2P)))
            rensponse_socket.send(b'ANEA')
            rensponse_socket.send(pktid.encode())
            IP = self.IPP2P_v4 + "|" + self.IPP2P_v6
            rensponse_socket.send(IP.encode())
            rensponse_socket.send(self.PP2P.encode())

        except Exception as e:
            print("Error occurs during near peer research.")
            print(e)
            print("$> ", end='')
            sys.stdout.flush()
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
                if not self.is_same_peer( mittent, (near[0].split('|')[0], near[1]) ) and not self.is_same_peer( mittent, (near[0].split('|')[1], near[1]) ):
                    try:
                        if self.pktid_track.check_pkt(pktid,near):
                            connection_socket = self.connect2peer( (near[0].split('|')[random.choice([0,1])], near[1]) )
                            connection_socket.send(b'QUER')
                            connection_socket.send(pktid.encode())
                            connection_socket.send(addr[0].encode())
                            #connection_socket.send("|".encode())
                            port_string = '%05d' %addr[1]
                            connection_socket.send(port_string.encode())
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
                if not self.is_same_peer( mittent, (near[0].split('|')[0], near[1]) ) and not self.is_same_peer( mittent, (near[0].split('|')[1], near[1]) ):
                    try:
                        if self.pktid_track.check_pkt(pktid,near):
                            connection_socket = self.connect2peer( (near[0].split('|')[random.choice([0,1])], near[1]) )
                            connection_socket.send(b'NEAR')
                            connection_socket.send(pktid.encode())
                            connection_socket.send(addr[0].encode())
                            #connection_socket.send("|".encode())
                            port_string = '%05d' %addr[1]
                            connection_socket.send(port_string.encode())
                            TTL_string = '%02d' %TTL
                            connection_socket.sendall(TTL_string.encode())

                    except Exception:
                        pass
                    finally:
                        if not connection_socket is None:
                            connection_socket.close()

    def NEAR_research(self):
        letters = ascii_uppercase + digits
        pktid = ''.join(random.choice(letters) for i in range(16))
        port = '%05d' %self.port_generator.give_port()
        self.pktid_track.check_pkt(pktid,(self.IPP2P_v4 + "|" + self.IPP2P_v6, port)) # serve solo per evitare reinvii da parte mia
        pkt = b'NEAR' + pktid.encode() + self.IPP2P_v4.encode() + "|".encode() + self.IPP2P_v6.encode() + port.encode() + "02".encode()
        for peer in self.near_peer:
            try:
                connection = self.connect2peer( (peer[0].split('|')[random.choice([0,1])], peer[1]) )
                connection.send(pkt)
            except Exception:
                pass
            finally:
                connection.close()

        research_thread = threading.Thread(target=self._near_research_thread, args=(port,))
        research_thread.start()

    def _near_research_thread(self, port):
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
        received_near = []

        server_sock.settimeout(1)
        conn = None
        while((int(time.time()) - self.pktid_track.get_listen_time()) < start_time):
            try:
                conn,addr = server_sock.accept()

                recvall(conn,4)
                recvall(conn,16)
                ip_near = recvall(conn,55).decode()
                # ip_near = ip_near_complete.split('|')[random.choice([0,1])]
                port_near = int(recvall(conn,5).decode())
                received_near.append((ip_near,port_near))
            except:
                pass
            finally:
                if conn:
                    conn.close()
        
        with self.lock:
            set_near = set(self.near_peer)
            set_received_near = set(received_near)

            set_new_near = set_received_near - set_near
            self.near_peer += list(set_new_near)

        print("Finded near peer:")
        for near in self.near_peer:
            print("\tIP: ", near[0], "\tPORT: ",near[1])
        print("$> ", end='')
        sys.stdout.flush()
            

    def QUER_research(self):
        letters = ascii_uppercase + digits
        pktid = ''.join(random.choice(letters) for i in range(16))
        port = '%05d' %self.port_generator.give_port
        self.pktid_track.check_pkt(pktid,(self.IPP2P_v4 + "|" + self.IPP2P_v6, port)) # serve solo per evitare reinvii da parte mia
        
        research = input("Insert the name of file: ")
        
        pkt = b'QUER' + pktid.encode() + self.IPP2P_v4.encode + "|".encode() + self.IPP2P_v6.encode() + port.encode() + "10".encode() + research.ljust(20).encode()
        for peer in self.near_peer:
            try:
                connection, address = self.connect2peer( (peer[0].split('|')[random.choice([0,1])], peer[1]) )
                connection.send(pkt)
            except Exception:
                pass
            finally:
                connection.close()

        research_thread = threading.Thread(target=self._quer_research_thread, args=(port,))
        research_thread.start()

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

        while((int(time.time()) - self.pktid_track.get_listen_time()) < start_time):
            try:
                conn,addr = server_sock.accept()

                recvall(conn,4)
                recvall(conn,16)
                ip_complete = recvall(conn,55).decode()

                port = int(recvall(conn,5).decode())
                file_md5 = recvall(conn,32).decode()
                file_name = recvall(conn,100).decode().strip()
                received_peer.append((ip_complete, port, file_md5, file_name))
            except:
                pass
            finally:
                conn.close()
        
        print("Finded peer for the selected file:")
        for near in received_peer:
            print("\tIP: " + near[0] + "\tPORT: " + near[1] + "\n\t\tfile name: " + near[3] + "\t md5: " + near[2])
        print("$> ", end='')
        sys.stdout.flush()

    def is_same_peer(self, mittent, addr):
        try:
            # [addr4,addr6] = addr[0].split('|')
            port = addr[1]

            if ':' in addr[0]: # ipv6 address
                addr_ext = ipaddress.ip_address(addr[0])
                addr_ext = addr_ext.exploded
            else:
                addr_ext = '%03d' %int(addr[0].split('.')[0]) + '.' + '%03d' %int(addr[0].split('.')[1]) + '.' + '%03d' %int(addr[0].split('.')[2]) + '.' + '%03d' %int(addr[0].split('.')[3])
                
            if '.' in mittent[0]:
                mittent_ext = mittent[0].split(':')[-1]
                mittent_ext = '%03d' %int(mittent_ext.split('.')[0]) + '.' + '%03d' %int(mittent_ext.split('.')[1]) + '.' + '%03d' %int(mittent_ext.split('.')[2]) + '.' + '%03d' %int(mittent_ext.split('.')[3])
            else:
                mittent_ext = ipaddress.ip_address(mittent[0])
                mittent_ext = mittent_ext.exploded

            if mittent_ext == addr_ext:
                if mittent[1] == port:
                    return True
        except Exception as e:
            raise e

        return False
