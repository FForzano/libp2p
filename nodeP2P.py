import socket, threading

class nodeP2P:

    def __init__(self,IPP2P_v4,IPP2P_v6,PP2P):
        self.IPP2P_v4 = IPP2P_v4
        self.IPP2P_v6 = IPP2P_v6
        self.PP2P = PP2P
        self.quitEvent = threading.Event()
    
    def start(self):
        try:
            self._start_server()
            self._start_client()
        except Exception as e:
            raise e
        finally:
            self.quitEvent.set()



    def _start_server(self):
        try:
            # Main peer server thread
            self.peer_server = threading.Thread(target=self._peer_server_thread)
            #peer_server.deamon = True
            self.peer_server.start()
        except Exception as e:
            self.quitEvent.set()
            raise e

    def _start_client(self):
        self.client_function()

        # Close all the app (included server)
        self.quitEvent.set()

        if self.peer_server.is_alive():
            print("Waiting for terminating the upload request")
            self.peer_server.join(timeout=1)


    def _peer_server_thread(self):
        '''
        _peer_server_thread()
        This thread listen from the port self.PP2P and create new thread for send files
        '''

        print("Start server")

        server_sock = None
        try:
            if socket.has_dualstack_ipv6():
                server_sock = socket.create_server(("", int(self.PP2P)), family=socket.AF_INET6, dualstack_ipv6=True)
            else:
                print("Dual stack not avaible.")
                server_sock = socket.create_server(("", int(self.PP2P)))

            # Creation of a double listener socket in both IPv4 and IPv6.
            
            server_sock.settimeout(5)
            while not self.quitEvent.isSet():
                #print("Try to accept connection for send file")
                try:
                    peer_conn, peer_addr = server_sock.accept() # peer_conn is the connection socket, peer_addr is a tuple of (ip_addr,port,etc) 

                    request_thread = threading.Thread(target=self.server_function,args=(peer_conn,))
                    # creation of a new thread for the peer request
                    request_thread.start()
                except socket.timeout:
                    pass
        except Exception as e:
            raise e
        finally:
            server_sock.close()

    def server_function(self, connection):
        '''
        server_function implements the peer server functionality.
        connection is the accepted connection with another peer.
        '''

        connection.sendall(connection.recv(1024))


    def client_function(self):
        '''
        client_function implements the peer client functionality.
        This is an abstract method, it is necessary to oveload this.
        '''

        print("Start client.")
        print("Please extends nodeP2P and implements this method")


    def connect2peer(self, addr):
        '''
        connect2peer(addr)

        This method create a connection socket with the peer specified in the address.
        The addr fiel must be a 2-tuple with addr=(ip,port), i.e ('172.0.0.1',1000) or
        ('::1', 1000).
        The return value is the connection socket with the selected peer.
        '''

        ip = ''
        if addr[0].find(':') == -1:
            addr_fields = addr[0].split('.')
            for field in addr_fields:
                ip += str(int(field))
                ip += '.'
            ip = ip[0:-1]
        else:
            ip = addr[0]
        
        port = addr[1]

        try:
            for res in socket.getaddrinfo(ip, port, socket.AF_UNSPEC, socket.SOCK_STREAM):	# SOCKET peer_directory
                try:
                    af, socktype, protocol, canonname, sa = res
                    
                    #sa = (address,int(peer_port)) # getaddrinfo get wrong address for ipv4...
                    peer_peer_socket = socket.socket(af, socktype, protocol)	# creazione tipo socket 
                    peer_peer_socket.settimeout(10)
                    peer_peer_socket.connect(sa)
                    break
                except socket.timeout:
                    peer_peer_socket = None
                except OSError:
                    peer_peer_socket = None
                except Exception:
                    peer_peer_socket = None
            
            peer_peer_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        except Exception:
            peer_peer_socket = None

        if peer_peer_socket is None:
            raise socket.error("Connection refused.")
        
        return peer_peer_socket


