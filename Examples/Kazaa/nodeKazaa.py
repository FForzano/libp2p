from nodeP2P import nodeP2P
from pktTracker import pktTracker
from utils import recvall
import os
from pktTracker import pktTracker
import ipaddress, hashlib, threading, random, socket, time, sys
from string import ascii_uppercase, digits
from portFinder import portFinder

class nodeKazaa(nodeP2P):

    def __init__(self,IPP2P_v4,IPP2P_v6,PP2P, near_file):
        super().__init__(IPP2P_v4,IPP2P_v6,PP2P)
        self.lock = threading.Lock()
        self.port_generator = portFinder(min_port=50000, max_port=51000)

        self.sessionId = None
        self.my_supernode = None
        self.shared_files = {} # {md5:file_name}
        self.near_peer = self._read_near(near_file) # [addr1,addr2,...] --> addr=(IP,Port:int)
        self.pktid_track = pktTracker(listen_time=20)

        # Ricerca del supernodo di riferimento
        print("I'm searching the supernode...")
        self.select_supernode()
    
    def server_function(self, connection, address):

        # modify address
        #

        while not self.quitEvent.isSet():
            try:
                instruction = recvall(connection,4).decode()

                if instruction == "":
                    continue

                elif instruction == "SUPE":
                    self._function_SUPE_server(connection, address)

                elif instruction == "ASUP":
                    self._function_ASUP_server(connection)

                elif instruction == "LOGI":
                    self._function_LOGI_server(connection)

                elif instruction == "ADFF":
                    self._function_ADFF_server(connection)

                elif instruction == "DEFF":
                    self._function_DEFF_server(connection)

                elif instruction == "LOGO":
                    self._function_LOGO_server(connection)

                elif instruction == "RETR":
                    self._function_RETR_server(connection)

                elif instruction == "FIND":
                    self._function_FIND_server(connection)

                elif instruction == "QUER":
                    self._function_QUER_server(connection, address)
            
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
                    print("\tLOGIN: login to the supernode;",\
                        "\n\tLOGOUT: logout from the supernode;", \
                        "\n\tSHARE: share new file;", \
                        "\n\tDELETE: remove a shared file;", \
                        "\n\tLIST: list all the shared files;", \
                        "\n\tSUPERNODE: select a new supernode;",\
                        "\n\tFIND: find a file",\
                        "\n\tRETR: download a file; ",\
                        "\n\tEXIT: close the node.")

                    command = input("$> ")

                    if command == "SUPERNODE":
                        self.select_supernode()
                    
                    elif command == "LOGIN":
                        self.login()

                    elif command == "SHARE":
                        if self.sessionId is None:
                            print("Please login before add file")
                            continue
                        self.add_file()

                    elif command == "DELETE":
                        if self.sessionId is None:
                            print("Please login before delete file")
                            continue
                        self.delete_file()

                    elif command == "LIST":
                        print("Shared files are:")
                        for md5,name in self.shared_files.items():
                            print("\tFile name:", name, "\tmd5:", md5)

                    elif command == "LOGOUT":
                        if self.sessionId is None:
                            print("Please login before logout")
                            continue
                        self.logout()

                    elif command == "FIND":
                        if self.sessionId is None:
                            print("Please login before logout")
                            continue
                        self.find_file()

                    elif command == "RETR":
                        self.download_file()

                    # elif command == "NEAR":
                    #     self.NEAR_research()

                    # elif command == "FIND":
                    #     self.QUER_research()

                    

                    elif command == "EXIT":
                        raise KeyboardInterrupt

                    else:
                        print("Invalid command.")

                except Exception as error:
                    print("Error occurs: ", error)
                    print("$> ", end='')
                    sys.stdout.flush()

        except KeyboardInterrupt:
            print("Bye!")


### SERVER METHODS ###
    def _function_SUPE_server(self, connection, mit_address):
        try:
            pktid = recvall(connection, 16).decode()
            ip = recvall(connection, 55).decode()
            port = recvall(connection, 5).decode()
            ttl = recvall(connection, 2).decode()

            self._forward_pkt(pktid, (ip, int(port)), int(ttl)-1, "_supe_research", mit_address)
        except Exception as e:
            print("Error occurs during supe server elaboration.")
            print("$> ", end='')
            sys.stdout.flush()
        finally:
            if not connection is None:
                connection.close()

    def _function_ASUP_server(self, connection):
        try:
            pktid = recvall(connection, 16).decode()
            ip = recvall(connection, 55).decode()
            port = recvall(connection, 5).decode()

            self.supernodes.append( (ip, int(port)) )

        except Exception as e:
            print("Error occurs during asup server elaboration.")
            print("$> ", end='')
            sys.stdout.flush()
        finally:
            if not connection is None:
                connection.close()

    def _function_LOGI_server(self, connection):
        # The normal node do nothing
        if not connection is None:
            connection.close()

    def _function_ADFF_server(self, connection):
        # Normal node don't do anything
        if not connection is None:
            connection.close()

    def _function_DEFF_server(self, connection):
        # Normal node don't do anything
        if not connection is None:
            connection.close()

    def _function_LOGO_server(connection):
        # Normal node don't do anything
        if not connection is None:
            connection.close()

    def _function_FIND_server(self, connection):
        # Normal node don't do anything
        if not connection is None:
            connection.close()

    def _function_QUER_server(self, connection, mit_address):
        # Normal node don't do anything
        if not connection is None:
            connection.close()

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
                connection.sendall(out)
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

    def _forward_pkt(self, pktid, addr, TTL, research, mittent):
        connection_socket = None

        if research == "_supe_research":
            for near in self.near_peer:
                if not self.is_same_peer( mittent, (near[0].split('|')[0], near[1]) ) and not self.is_same_peer( mittent, (near[0].split('|')[1], near[1]) ):
                    try:
                        connection_socket = self.connect2peer( (near[0].split('|')[random.choice([0,1])], near[1]) )
                        connection_socket.send(b'SUPE')
                        connection_socket.send(pktid.encode())
                        connection_socket.send(addr[0].encode())
                        #connection_socket.send("|".encode())
                        port_string = '%05d' %addr[1]
                        connection_socket.send(port_string.encode())
                        TTL_string = '%02d' %TTL
                        connection_socket.send(TTL_string.encode())

                    except Exception:
                        pass
                    finally:
                        if not connection_socket is None:
                            connection_socket.close()

        elif research != "":
            research = research.ljust(20)

            for near in self.near_peer:
                if not self.is_same_peer( mittent, (near[0].split('|')[0], near[1]) ) and not self.is_same_peer( mittent, (near[0].split('|')[1], near[1]) ):
                    try:
                        connection_socket = self.connect2peer( (near[0].split('|')[random.choice([0,1])], near[1]) )
                        connection_socket.send(b'QUER')
                        connection_socket.send(pktid.encode())
                        connection_socket.send(addr[0].encode())
                        #connection_socket.send("|".encode())
                        port_string = '%05d' %addr[1]
                        connection_socket.send(port_string.encode())
                        TTL_string = '%02d' %TTL
                        connection_socket.send(TTL_string.encode())
                        connection_socket.sendall(research.encode())

                    except Exception:
                        pass
                    finally:
                        if not connection_socket is None:
                            connection_socket.close()
        
        else: 
            for near in self.near_peer:
                if not self.is_same_peer( mittent, (near[0].split('|')[0], near[1]) ) and not self.is_same_peer( mittent, (near[0].split('|')[1], near[1]) ):
                    try:
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



### CLIENT METHODS ###

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
        
        self.my_supernode = random.choice(self.supernodes)
        print("Selected supernode is:")
        print("\tIPv4|IPv6:", self.my_supernode[0], "\tPort:", self.my_supernode[1])

    def login(self):
        try:
            supernode_socket = self.connect2peer(self.my_supernode)
            supernode_socket.sendall("LOGI".encode() + self.IPP2P_v4.encode() + b'|' + self.IPP2P_v6.encode() + self.PP2P.encode())
            recvall(supernode_socket,4)
            self.sessionId = recvall(supernode_socket, 16).decode()
            print("SessionID: ", self.sessionId)
        except Exception as e:
            print("Error occurs during login\n", e)
        finally:
            supernode_socket.close()

    def add_file(self):
        file_name = input("Insert the file name: ")
        file_md5 = ""
        if len(file_name) > 100:
            print("Please insert a name with length less then 100 characters")
            return
        file = None
        try:
            file = open(file_name,"rb")
            file_md5 = hashlib.md5(file.read()).hexdigest()
            file.close()
        except FileNotFoundError:
            print(file_name + " not found.")
            return
        except Exception as e:
            file.close()
            print(e)
            return

        try:
            supernode_socket = self.connect2peer(self.my_supernode)
            supernode_socket.sendall(b'ADFF' + self.sessionId.encode() + file_md5.encode() + file_name.ljust(100).encode())
        except Exception as e:
            print("Error in file upload")
            return
        finally:
            supernode_socket.close()

        self.shared_files[file_md5] = file_name

    def delete_file(self):
        file_md5 = input("Insert the md5 checksum of the file: ")
        try:
            supernode_socket = self.connect2peer(self.my_supernode)
            supernode_socket.sendall(b'DEFF' + self.sessionId.encode() + file_md5.encode())
        except Exception as e:
            print("Error in file deleting")
            return
        finally:
            supernode_socket.close()

        del self.shared_files[file_md5]

    def logout(self):
        try:
            supernode_socket = self.connect2peer(self.my_supernode)
            supernode_socket.sendall("LOGO".encode() + self.sessionId.encode())
            recvall(supernode_socket,4)
            deleted_files = int(recvall(supernode_socket, 3).decode())
            print("Logout done with success.\n", deleted_files, "are been removed")
        except Exception as e:
            print("Error occurs during logout")
        finally:
            supernode_socket.close()

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

    def download_file(self):
        file2download = input("Insert the md5 of the file that you want to download: ")
        peer_address = input("Insert the IP address (IPv4|IPv6) of the selected peer: ")
        
        peer_port = input("Insert the port of the selected peer: ")
        file_name = input("Insert the file name: ")

        try:
            if not os.path.isdir("Downloads"):
                os.mkdir("Downloads")
        except Exception:
            print("Error occurs.")
            self.quitEvent.set()
            sys.exit(1)
        
        peer_address = peer_address.split('|')

        # connection at the peer server for file download
        random.shuffle(peer_address) # random choise between ipv4 and ipv6
        address = (peer_address[0],peer_port)
        print("Try to connect at", address[0])
        
        try:
            peer_peer_socket = self.connect2peer(address)

        except Exception:
            peer_peer_socket = None
        try:
            if peer_peer_socket is None:
                address = (peer_address[1],peer_port)
                print("Connection refused. Try to connect at", address[0])
                peer_peer_socket = self.connect2peer(address)
            
        except Exception:
            peer_peer_socket = None

        if peer_peer_socket is None:
            print("Connection failed.")
            print("$> ", end='')
            sys.stdout.flush()

        pkt = "RETR"+ file2download
        peer_peer_socket.sendall(pkt.encode())
        try:
            downloaded_file = open("Downloads/"+file_name,"wb")
            downloaded_file.seek(0)

            recvall(peer_peer_socket, 4)
            Nchunk_string = recvall(peer_peer_socket, 6).decode()
            #print(Nchunk_string)
            Nchunk = int(Nchunk_string)
            for i in range(Nchunk):

                # Download state bar
                if Nchunk > 40 and i%int(Nchunk/40) == 0:
                    print("#",sep='',end='')
                    sys.stdout.flush()
                elif Nchunk <= 40:
                    print("#",sep='',end='')
                    sys.stdout.flush()

                len_chunk_string = recvall(peer_peer_socket, 5).decode()
                len_chunk = int(len_chunk_string)

                chunk = recvall(peer_peer_socket, len_chunk)

                downloaded_file.write(chunk) 
            
            print("\nFile successfully downloaded")
            print("$> ", end='')
            sys.stdout.flush()
        except OSError:
            print("Error occurs during the download")
            print("$> ", end='')
            sys.stdout.flush()
        finally:
            if not downloaded_file.closed:
                downloaded_file.close()
            peer_peer_socket.close()

    def find_file(self):
        research_string = input("Insert the research string: ")
        if len(research_string) > 20:
            print("Please insert a string with length less then 20 characters")
            return

        find_thread = threading.Thread(target=self._find_files_thread, args=(research_string,))
        find_thread.start()

    def _find_files_thread(self, research_string):
        try:
            supernode_socket = self.connect2peer(self.my_supernode, timeout=False)
            supernode_socket.sendall(b'FIND' + self.sessionId.encode() + research_string.ljust(20).encode())
            if recvall(supernode_socket,4) != b'AFIN':
                print("Invalid return value")
                print("$> ",end='')
                sys.stdout.flush()
                return
            
            nfile = int(recvall(supernode_socket,3))
            if nfile == 0:
                print("File not found in the directory")
                print("$> ",end='')
                sys.stdout.flush()
                return

            for i in range(nfile):
                current_md5 = recvall(supernode_socket,32).decode()
                current_filename = recvall(supernode_socket,100).decode()
                ncopy = int(recvall(supernode_socket,3))
                print("--> File name:", current_filename.strip(), "\tmd5 checksum:", current_md5)

                for j in range(ncopy):
                    current_IP = recvall(supernode_socket,55).decode()
                    current_port = recvall(supernode_socket,5).decode()
                    print("\t@ IPP2P:",current_IP,"PP2P:",current_port)

                print("$> ", end='')
                sys.stdout.flush()
                

        except Exception as e:
            print("Error occurs in file research", e)
            print("$> ", end='')
            sys.stdout.flush()
        finally:
            supernode_socket.close()
            
    def _read_near(self, near_file):
        nears = []
        
        with open(near_file, "rt") as file:
            line = file.readline()
            if not 'NEAR_PEERS' in line:
                return []
            
            line = file.readline()
            while line:
                info = line.split(',')
                nears.append( (info[0].strip(), int(info[1].strip())) )
        return nears


    # def QUER_research(self):
    #     letters = ascii_uppercase + digits
    #     pktid = ''.join(random.choice(letters) for i in range(16))
    #     port = '%05d' %self.port_generator.give_port()
    #     self.pktid_track.check_pkt(pktid) # serve solo per evitare reinvii da parte mia
        
    #     research = input("Insert the name of file: ")
        
    #     research_thread = threading.Thread(target=self._quer_research_thread, args=(port,))
    #     research_thread.start()

    #     pkt = b'QUER' + pktid.encode() + self.IPP2P_v4.encode() + "|".encode() + self.IPP2P_v6.encode() + port.encode() + "10".encode() + research.ljust(20).encode()
    #     for peer in self.near_peer:
    #         try:
    #             connection = self.connect2peer( (peer[0].split('|')[random.choice([0,1])], peer[1]) )
    #             connection.sendall(pkt)
    #         except Exception:
    #             pass
    #         finally:
    #             connection.close()

    # # def _quer_research_thread(self, port):
    #     try:
    #         if socket.has_dualstack_ipv6():
    #             server_sock = socket.create_server(("", int(port)), family=socket.AF_INET6, dualstack_ipv6=True)
    #         else:
    #             print("Dual stack not avaible.")
    #             print("$> ", end='')
    #             sys.stdout.flush()
    #             server_sock = socket.create_server(("", int(port)))
    #     except Exception:
    #         pass
        
    #     start_time = int(time.time())
    #     received_peer = []

    #     server_sock.settimeout(3)
    #     conn = None
    #     while((int(time.time()) - self.pktid_track.get_listen_time()) < start_time):
    #         try:
    #             conn,addr = server_sock.accept()

    #             recvall(conn,4)
    #             recvall(conn,16)
    #             ip_complete = recvall(conn,55).decode()

    #             port = int(recvall(conn,5).decode())
    #             file_md5 = recvall(conn,32).decode()
    #             file_name = recvall(conn,100).decode().strip()
    #             received_peer.append( (ip_complete, port, file_md5, file_name) )
    #         except:
    #             pass
    #         finally:
    #             if conn:
    #                 conn.close()
        
    #     print("Finded peer for the selected file:")
    #     for near in received_peer:
    #         print(" @ IP: ", near[0], "\tPORT: ", near[1], "\n\t", "-> file name: ", near[3], "\t md5: ", near[2])
    #     print("$> ", end='')
    #     sys.stdout.flush()