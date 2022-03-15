from utils import recvall
import os, random, ipaddress, hashlib, socket, sys
import napsterprotocol as np
from nodeP2P import nodeP2P

class napsternode(nodeP2P):
    added_files = {}

    def __init__(self,IPP2P_v4,IPP2P_v6,PP2P):
        super().__init__(IPP2P_v4,IPP2P_v6,PP2P)

    def server_function(self, connection):
        '''
        This thread send the file
        '''

        max_chunk_size = 1024
        f = None
        try:
            command = recvall(connection,4).decode()
            md5 = recvall(connection,32).decode()
            if command != "RETR":
                print("Invalid instruction received")
                raise Exception("Invalid received instruction")

            name = self.added_files[md5]

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
        finally:
            if not f is None:
                f.close()
            connection.close()

    def client_function(self):
        # Socket creation for directory communication
        DIRECTORY_IP_4 = '172.16.0.22' # per prove in vpn (localhost)
        DIRECTORY_IP_6 = 'fc00::1004' # per prove in vpn (localhost)
        random_choice = [DIRECTORY_IP_4, DIRECTORY_IP_6]
        DIRECTORY_IP = random_choice[random.randint(0,1)]

        SERVER_PORT = 3000

        try:
            # Automatic login
            # make the address string
            self.IPP2P_v6 = ipaddress.ip_address(self.IPP2P_v6)
            IPv4 = '%03d' %int(self.IPP2P_v4.split('.')[0]) + '.' + '%03d' %int(self.IPP2P_v4.split('.')[1]) + '.' + '%03d' %int(self.IPP2P_v4.split('.')[2]) + '.' + '%03d' %int(self.IPP2P_v4.split('.')[3])
            IPv6 = self.IPP2P_v6.exploded
            IPADD = IPv4 + '|' + IPv6
            PORT = '%05d' %int(self.PP2P)
            self.PP2P = PORT
            
            for i in range(3):
                peer_directory_socket = super().connect2peer((DIRECTORY_IP,SERVER_PORT))
                peer_directory_socket.sendall(np.napster_revparser(["LOGI",IPADD, self.PP2P]))
                resp = recvall(peer_directory_socket,20)
                resp_list = np.napster_parser(resp)
                peer_directory_socket.close()
                # print(resp)
                if resp_list[1] != "0000000000000000":
                    break
            
            if resp_list[1] == "0000000000000000":
                print("Login failed. Please login before execute any action.")
            else:
                print("Login with SessionId: " + resp_list[1])
                sessionId = resp_list[1]
                login_status = True
            
            while True:
                DIRECTORY_IP = random_choice[random.randint(0,1)]
                
                print("\nAvailable instructions: \nLOGI (login), ADDF (add file), DELF (delete file), FIND (find file), RETR (download file), LOGO (logout)")
                command = input("Insert the command: ")

                peer_directory_socket = super().connect2peer((DIRECTORY_IP,SERVER_PORT))

                if command == "LOGI":
                    peer_directory_socket.sendall(np.napster_revparser(["LOGI",IPADD, self.PP2P]))
                    resp = recvall(peer_directory_socket,20)
                    resp_list = np.napster_parser(resp)
                    print("Login with SessionId: " + resp_list[1])
                    sessionId = resp_list[1]
                    login_status = True
                
                elif command == "ADDF":

                    if login_status == False:
                        print("Login before add file.")
                        continue

                    file_name = input("Insert the file name: ")
                    file_md5 = ""
                    if len(file_name) > 100:
                        print("Please insert a name with length less then 100 characters")
                        
                        continue
                    file = 0
                    try:
                        file = open(file_name,"rb")
                        file_md5 = hashlib.md5(file.read()).hexdigest()
                        #print(file_md5)
                        file.close()
                    except FileNotFoundError:
                        print(file_name + " not found.")
                        continue
                    except Exception as e:
                        file.close()
                        print(e)
                        continue
                    msg = np.napster_revparser(["ADDF",sessionId,file_md5,os.path.basename(file_name).ljust(100)])
                    #print(msg)
                    peer_directory_socket.sendall(msg)
                    recv_list = np.napster_parser(recvall(peer_directory_socket, 7))
                    print(file_name, "successfully added.")
                    print(recv_list[1], "copy of this file are in the directory")

                    self.added_files[file_md5] = file_name

                elif command == "DELF":
                    file_md5 = input("Insert the md5 checksum of the file that you want to delete: ")
                    peer_directory_socket.sendall(np.napster_revparser(["DELF",sessionId,file_md5]))
                    recv_list = np.napster_parser(recvall(peer_directory_socket,7))
                    if recv_list[1] == "999":
                        print("File not in directory. Please add the file before delete it")
                    else:
                        print("File successfully deleted. There are", recv_list[1], "copy of this file now.")

                    if file_md5 in self.added_files.keys():
                        del self.added_files[file_md5]
                
                elif command == "FIND":
                    research_string = input("Insert the research string: ")
                    if len(research_string) > 20:
                        print("Please insert a string with length less then 20 characters")
                        continue

                    peer_directory_socket.sendall(np.napster_revparser(["FIND",sessionId,research_string.ljust(20)]))
                    if recvall(peer_directory_socket,4) != b'AFIN':
                        print("Invalid return value")
                        continue
                    
                    nfile = int(recvall(peer_directory_socket,3))
                    if nfile == 0:
                        print("File not found in the directory")
                        continue

                    for i in range(nfile):
                        current_md5 = recvall(peer_directory_socket,32).decode()
                        current_filename = recvall(peer_directory_socket,100).decode()
                        ncopy = int(recvall(peer_directory_socket,3))
                        print("--> File name:", current_filename.strip(), "\tmd5 checksum:", current_md5)

                        for j in range(ncopy):
                            current_IP = recvall(peer_directory_socket,55).decode()
                            current_port = recvall(peer_directory_socket,5).decode()
                            print("\t@ IPP2P:",current_IP,"PP2P:",current_port)


                elif command == "RETR":
                    file2download = input("Insert the md5 of the file that you want to download: ")
                    peer_address = input("Insert the IP address (IPv4|IPv6) of the selected peer: ")
                    
                    peer_port = input("Insert the port of the selected peer: ")
                    # make socket for download

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
                        continue

                    # Succesfull connection

                    peer_peer_socket.sendall(np.napster_revparser(["RETR",file2download]))
                    try:
                        downloaded_file = open("Downloads/"+file2download,"wb")
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
                    except OSError:
                        print("Error occurs during the download")
                        continue
                    finally:
                        if not downloaded_file.closed:
                            downloaded_file.close()
                        peer_peer_socket.close()
                    
                    peer_directory_socket.sendall(np.napster_revparser(["DREG",sessionId,file2download]))
                    resp_list = np.napster_parser(recvall(peer_directory_socket,9))
                    print("Number of total download for the selected file:", resp_list[1])


                elif command == "LOGO":
                    peer_directory_socket.sendall(np.napster_revparser(["LOGO",sessionId]))
                    resp = recvall(peer_directory_socket,7)
                    resp_list = np.napster_parser(resp)
                    print("Logout executed. Number of removed files: " + resp_list[1])
                    print("Bye.")
                    login_status = False
                    self.quitEvent.set()
                    break

                else:
                    print("Invalid command.")

                peer_directory_socket.close()



        except (Exception, KeyboardInterrupt) as error:
            print(error)
            print("\nError occurs.\nShutdown the peer node...")
            self.quitEvent.set()
            # logout if is logged
            '''
            if login_status:
                peer_directory_socket.sendall(np.napster_revparser(["LOGO",sessionId]))
                resp_list = np.napster_parser(recvall(peer_directory_socket,7))
                print("Logout executed. Number of removed files: " + resp_list[1])
            '''
            peer_directory_socket.close()
            sys.exit(1)
            #peer_conn.close()
            #server_sock.close()
    
if __name__ == "__main__":
    node = napsternode(sys.argv[1],sys.argv[2],sys.argv[3])
    node.start()
