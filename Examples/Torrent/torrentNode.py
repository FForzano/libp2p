from nodeP2P import nodeP2P
from utils import recvall
import os
import ipaddress, hashlib, threading, random, socket, time, sys
from string import ascii_uppercase, digits

part_size = 262144
IP_tracker = '172.016.000.022|fc00:0000:0000:0000:0000:0000:0000:1004'
P_tracker = 3000

class torrentNode(nodeP2P):

    def __init__(self,IPP2P_v4,IPP2P_v6,PP2P):
        super().__init__(IPP2P_v4,IPP2P_v6,PP2P)
        self.lock = threading.Lock()

        self.tracker = (IP_tracker,P_tracker)
        self.sessionId = None
        self.shared_files = {} # {md5:file_name}
        self.known_files = {}
        self.update_thread_status = False
    
    def server_function(self, connection, address):

        while not self.quitEvent.isSet():
            try:
                instruction = recvall(connection,4).decode()

                if instruction == "":
                    continue

                if instruction == "RETP":
                    self._function_RETP_server(connection)
            
                sys.exit()
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
                        "\n\tFIND: find a file;",\
                        "\n\tDOWNLOAD: download a file; ",\
                        "\n\tEXIT: close the node.")

                    command = input("$> ")
                    
                    if command == "LOGIN":
                        self.login()  

                    elif command == "LOGOUT":
                        self.logout()  

                    elif command == "SHARE":
                        self.add_file()

                    elif command == "FIND":
                        self.find_file()

                    elif command == "DOWNLOAD":
                        self.download_file()

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

    def _function_RETP_server(self, connection):
        max_chunk_size = 1024
        f = None
        try:
            md5 = recvall(connection,32).decode()
            part_number = int(recvall(connection,8).decode())

            name = self.shared_files[md5]

            if os.path.exists(name):

                f = open(name,"rb")
                f.seek(part_number*part_size)
                
                fsize = os.path.getsize(name)
                npart = int(fsize/part_size) + 1
                if part_number == (npart-1):
                    fsize = os.path.getsize(name)
                    fsize = (fsize%part_size)-1
                else:
                    fsize = part_size-1
            
            else:
                f = open(name + '%08d' %part_number + '.part' ,"rb")
                f.seek(0)

                fsize = os.path.getsize(name)

            out = "AREP" + ('%06d' %(int(fsize/max_chunk_size)+1))
            connection.sendall(out.encode())

            nChunk = int(fsize/max_chunk_size)+1
            i = 1
            end = False
            read_dim = max_chunk_size
            if nChunk == i:
                read_dim = (part_size%max_chunk_size)-1
                end = True

            chunk = f.read(read_dim)
            
            while chunk:
                out = '%05d' %(len(chunk))
                out = out.encode() + chunk
                connection.sendall(out)

                if end:
                    if not f is None:                                       
                        f.close()
                    connection.close()
                    return

                i += 1
                if (nChunk == i):
                    end = True
                    if not (part_size%max_chunk_size == 0):
                        read_dim = (part_size%max_chunk_size) -1
                    else:
                        read_dim = max_chunk_size

                else:
                    read_dim = max_chunk_size
                # print(read_dim)
                chunk = f.read(read_dim)

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



### CLIENT METHODS ###

    def login(self):
        try:
            tracker_socket = self.connect2peer(self.tracker)
            tracker_socket.sendall("LOGI".encode() + self.IPP2P_v4.encode() + b'|' + self.IPP2P_v6.encode() + self.PP2P.encode())
            recvall(tracker_socket,4)
            self.sessionId = recvall(tracker_socket, 16).decode()
            print("SessionID: ", self.sessionId)

            if self.server_status == False:
                self.restart_server()
        except Exception as e:
            print("Error occurs during login\n", e)
        finally:
            tracker_socket.close()


    def logout(self):
        if self.sessionId is None:
            print("Login before share new file please.")
            return

        tracker_socket = None
        try:
            tracker_socket = self.connect2peer(self.tracker)
            tracker_socket.sendall(b'LOGO' + self.sessionId.encode())

            answer = recvall(tracker_socket,4).decode()
            
            if answer == 'NLOG':
                partdown = int(recvall(tracker_socket,10).decode())
                print('Logout denied. The number of your parts downloaded at least one time is', partdown, '.')
            
            elif answer == 'ALOG':
                partown = int(recvall(tracker_socket,10).decode())
                print('Logout allowed. You had got', partown, 'parts.')
                print('Terminating all processes...')
                time.sleep(5)

                self.quitEvent.set()
                self.sessionId = None
                self.shared_files = {} # {md5:file_name}
                self.known_files = {}
                self.update_thread_status = False

        except Exception as e:
            print("Error occurs during logout")
        finally:
            tracker_socket.close()


    def add_file(self):
        if self.sessionId is None:
            print("Login before share new file please.")
            return
        
        file_name = input("Insert the file name: ")
        file_md5 = ""
        file_size = None

        if len(file_name) > 100:
            print("Please insert a name with length less then 100 characters")
            return
        file = None
        try:
            # file md5
            file = open(file_name,"rb")
            file_md5 = hashlib.md5(file.read()).hexdigest()
            file.close()

            # file size
            file_size = os.path.getsize(file_name)

        except FileNotFoundError:
            print(file_name + " not found.")
            return
        except Exception as e:
            file.close()
            print(e)
            return

        try:
            tracker_socket = self.connect2peer(self.tracker)
            tracker_socket.sendall(b'ADDR' + self.sessionId.encode() + ('%10d' %file_size).encode() + ('%06d' %part_size).encode() + file_name.ljust(100).encode() + file_md5.encode() )

            if (not recvall(tracker_socket, 4).decode() == 'AADR'):
                print("Error in tracker communication for file uploading.")

            number_of_parts =  int( recvall(tracker_socket, 8).decode() )
            print("The file is been uploaded. It has", number_of_parts, 'parts.')

            # self.known_files)

        except Exception as e:
            print("Error in file upload.\n",e)
            return
        finally:
            tracker_socket.close()

        self.shared_files[file_md5] = file_name

    def find_file(self):
        research_string = input('Insert the string to search: ')

        if len(research_string) > 20:
            print("The research string must have a length less or equal then 20")
            return
        
        tracker_socket = None
        received_files = {}

        try:
            tracker_socket = self.connect2peer(self.tracker)

            tracker_socket.sendall(b'LOOK' + self.sessionId.encode() + research_string.ljust(20).encode())

            if (not recvall(tracker_socket, 4).decode() == 'ALOO' ):
                print("Error occurs in the tracker answer.")

            num_idmd5 = int( recvall(tracker_socket, 3).decode() )

            print("Finded files:")

            for i in range(num_idmd5):
                md5 = recvall(tracker_socket, 32).decode()
                received_files[md5] = {}
                received_files[md5]['file_name']  = recvall(tracker_socket, 100).decode() 
                received_files[md5]['file_len'] =  int(recvall(tracker_socket, 10).decode())
                received_files[md5]['len_part'] =  int(recvall(tracker_socket, 6).decode())
                print(' > md5:', md5, '\tfile name:', received_files[md5]['file_name'].strip() )
                print('\tfile length:', received_files[md5]['file_len'], '\tpart length:', received_files[md5]['len_part'] )

                with self.lock:
                    self.known_files[md5] = []
                    self.known_files[md5].append( received_files[md5]['file_len'] )
                    self.known_files[md5].append( {} )

        except Exception as e:
            print("Error occurs during file research.\n", e)
        finally:
            if tracker_socket:
                tracker_socket.close()

        # status update
        if not self.update_thread_status and self.known_files:
            self.update_thread_status = True
            updating_thread = threading.Thread(target=self.status_update_tfunction)
            updating_thread.start()

    def status_update_tfunction(self):
        while not self.quitEvent.isSet():
            for md5, fileInfo in self.known_files.items():
                self.status_update(md5, int(fileInfo[0]/part_size)+1)
            
            # print(self.known_files)
            # print('$> ', end='')
            # sys.stdout.flush()
            time.sleep(5)
            
    def status_update(self, file_md5, num_parts):
        status = []
        try:
            tracker_socket = self.connect2peer(self.tracker)

            tracker_socket.sendall( b'FCHU' + self.sessionId.encode() + file_md5.encode() )

            recvall(tracker_socket,4)
            num_hitpeer = int(recvall(tracker_socket,3))

            for i in range(num_hitpeer):
                status.append( [] )
                status[-1].append( (recvall(tracker_socket,55).decode(), int(recvall(tracker_socket,5).decode())) )
                with self.lock:
                    self.known_files[file_md5][1][ status[-1][0] ] = b''

                for j in range(int(num_parts/8)+1):
                    status[-1].append( recvall(tracker_socket, 8) ) # problema qua
                    with self.lock:
                        self.known_files[file_md5][1][ status[-1][0] ] += status[-1][-1]


        except Exception as e:
            print("Error occurs during file update.\n", e)
        finally:
            if tracker_socket:
                tracker_socket.close()


    def download_file(self):
        file2download = input("Insert the md5 of the file that you want to download: ")
        file_name = input("Insert the file name: ")

        try:
            if not os.path.isdir("Downloads"):
                os.mkdir("Downloads")
        except Exception:
            print("Error occurs.")
            self.quitEvent.set()
            sys.exit(1)

        number_of_parts = int(self.known_files[file2download][0]/part_size)+1
        file_info = self.known_files[file2download][1]

        download_thread = []

        # The downloaded file is automatically shared
        self.shared_files[file2download] = 'Downloads/' + file_name

        for part_counter in range(number_of_parts):
            part2download, peer4part = self.__whichpart__(file_info, number_of_parts, file_name)
            
            if part2download is None:
                break

            # thread for download part
            download_thread.append( threading.Thread(target=self.download_tfunction, args=[file2download, file_name, part2download, random.choice(peer4part)]) )
            download_thread[-1].start()
            time.sleep(0.1)
            # download_thread[-1].join()
        
        # waiting download of parts
        while True:
            downloading_on = False
            for thread in download_thread:
                if thread.is_alive():
                    downloading_on = True
                    break
            if not downloading_on:
                break

            time.sleep(1)

        print('')

        # unify the parts
        try:
            out_file = open('Downloads/' + file_name, 'wb')
            for npart in range(number_of_parts):
                part_file = open('Downloads/' + file_name + '%08d' %npart + '.part', 'rb')
                out_file.write(part_file.read())

                part_file.close()
                os.remove('Downloads/' + file_name + '%08d' %npart + '.part')
        except Exception as e:
            print('Error in part unifying.\n', e)
            print('$> ', end='')
            sys.stdout.flush()
        finally:
            out_file.close()



    def download_tfunction(self, md5, file_name, part, addr):
        # print("Download part", part, "from peer", addr)

        download_socket = None
        try:
            downloaded_file = open("Downloads/"+file_name+'%08d'%part+'.part',"wb")
            downloaded_file.seek(0)

            download_socket = self.connect2peer(addr)

            pkt = "RETP"+ md5 + '%08d' %part
            download_socket.sendall(pkt.encode())
            try:
                recvall(download_socket, 4)
                Nchunk_string = recvall(download_socket, 6).decode()
                #print(Nchunk_string)
                Nchunk = int(Nchunk_string)
                for i in range(Nchunk):

                    len_chunk_string = recvall(download_socket, 5).decode()
                    len_chunk = int(len_chunk_string)

                    chunk = recvall(download_socket, len_chunk)

                    downloaded_file.write(chunk) 

                print("#",sep='',end='')
                sys.stdout.flush()
                
                # print("\nPart successfully downloaded")
                # print("$> ", end='')
                # sys.stdout.flush()
            except OSError:
                print('Error occurs during download of part', part, "from peer", addr)
                print("$> ", end='')
                sys.stdout.flush()
            finally:
                if not downloaded_file.closed:
                    downloaded_file.close()
                download_socket.close()

        except Exception as e:
            print('Error occurs during download of part', part, "from peer", addr)
            print(e)
            print('$> ', end='')
            sys.stdout.flush()
        finally:
            if download_socket:
                download_socket.close()

        # send to tracker the success of download
        tracker_socket = None
        try:
            tracker_socket = self.connect2peer(self.tracker)

            pkt = 'RPAD' + self.sessionId + md5 + '%08d' % part
            tracker_socket.sendall(pkt.encode())
            recvall(tracker_socket,4)
            recvall(tracker_socket,8).decode()
            # print("I have", recvall(tracker_socket,8).decode(), 'parts for the selected file')
            # print('$> ', end='')
            # sys.stdout.flush()

        except Exception as e:
            print('Error occurs during tracker communication')
            print(e)
            print('$> ', end='')
            sys.stdout.flush()
        finally:
            if tracker_socket:
                tracker_socket.close()

        sys.exit()
        

    def __whichpart__(self, file_info, nparts, file_name):
        counter_parts = []
        addr4parts = []
        for part_number in range(nparts):
            counter_parts.append(0)
            addr4parts.append([])
            for addr, parts in file_info.items():
                parts = parts.decode()
                counter_parts[-1] +=  int(parts[part_number])
                if int(parts[part_number]) == 1: # qua bisogna rivedere
                    addr4parts[-1].append( addr )
        
        # A questo punto in counter_parts ci sono le occorrenze di ogni parte (dove il numero della parte è
        # data da indice+1) e in addr4parts ci sono tutti i peer che mettono a disposizione ogni parte.

        for part_number in range(nparts):
            min_part = counter_parts.index( min(counter_parts) )
            if (not self.__havejet__(min_part, file_name)):
                return min_part, addr4parts[min_part]

            else:
                counter_parts[min_part] = float("inf")


        return None,None

    def __havejet__(self, part, file_name):
        return os.path.exists('Downloads/' + file_name + '%08d' %part + '.part')



if __name__ == "__main__":
    node = torrentNode(sys.argv[1], sys.argv[2], sys.argv[3])
    node.start()
