from nodeP2P import nodeP2P
from utils import recvall
import os
import ipaddress, hashlib, threading, random, socket, time, sys
from string import ascii_uppercase, digits

part_size = 262144

class tracker(nodeP2P):
    
    def __init__(self,IPP2P_v4,IPP2P_v6,PP2P):
        super().__init__(IPP2P_v4,IPP2P_v6,PP2P)
        self.lock = threading.Lock()

        self.sessionId = None
        self.logged_peers = {}
        self.peer4files = {}
        self.downloaded_parts = {}
        self.file_names = {}


    def server_function(self, connection, address):

        while not self.quitEvent.isSet():
            try:
                instruction = recvall(connection,4).decode()

                if instruction == "":
                    continue

                elif instruction == 'LOGI':
                    self._function_LOGI_server(connection)

                elif instruction == 'LOGO':
                    self._function_LOGO_server(connection)

                elif instruction == 'ADDR':
                    self._function_ADDR_server(connection)

                elif instruction == 'LOOK':
                    self._function_LOOK_server(connection)

                elif instruction == 'FCHU':
                    self._function_FCHU_server(connection)
                
                elif instruction == 'RPAD':
                    self._function_RPAD_server(connection)
            
                sys.exit()
            except Exception:
                pass
            finally:
                if not connection is None:
                    connection.close()

    def client_function(self):
        while(True):
            variable = input('$> ')

            if variable == 'logged_peers':
                print(self.logged_peers)
            if variable == 'peer4files':
                print(self.peer4files)
            if variable == 'file_names':
                print(self.file_names)
            # if variable == 'knowed_files':
            #     print(self.logged_peers)


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

    def _function_LOGO_server(self, connection):
        try:
            peer_SID = recvall(connection, 16).decode()

            if self.__allow_logout__(peer_SID):
                with self.lock:
                    del self.logged_peers[peer_SID]

                partown = 0
                for md5, peers in self.peer4files.items():
                    if peer_SID in peers.keys():
                        partown += peers[peer_SID][1].count('1')
                        with self.lock:
                            del self.peer4files[md5][peer_SID]
                
                peer4files_temp = {}
                for md5, peers in self.peer4files.items():
                    if peers:
                        peer4files_temp[md5] = peers
                    else:
                        del self.file_names[md5]
                
                self.peer4files = peer4files_temp

                partown_string = '%10d' %partown
                connection.sendall(b'ALOG' + partown_string.encode())

            else:
                partdown = 0

                for md5, file_info in self.peer4files.items():
                    if peer_SID in file_info.keys():
                        partdown += sum( self.downloaded_parts[md5] )

                partdown_string = '%10d' %partdown
                connection.sendall(b'NLOG' + partdown_string.encode())

        except Exception as e:
            print("Error occurs during logout operations.\n", e)
            print("$> ", end='')
            sys.stdout.flush()
        finally:
            if not connection is None:
                connection.close()
        
            
            
    def __allow_logout__(self, peer_SID):

        for md5, file_info in self.peer4files.items():
            if peer_SID in file_info.keys():
                if 0 in self.downloaded_parts[md5]:
                    return False

        return True

    def _function_ADDR_server(self, connection):
        try:
            sessionid = recvall(connection, 16).decode()
            lenfile = int(recvall(connection, 10).decode())
            lenpart = int( recvall(connection, 6).decode() )
            filename = recvall(connection, 100).decode()
            filemd5 = recvall(connection, 32).decode()

            # loggin control
            if sessionid not in self.logged_peers.keys():
                part_number = '00000000'
                connection.sendall( b'AADR' + part_number.encode())
                connection.close()
                return


            # Actions for logged users
            if filemd5 not in self.peer4files.keys():
                self.peer4files[filemd5] = {}
                self.downloaded_parts[filemd5] = [0]*(int(lenfile/lenpart) +1)
            
            with self.lock:
                self.file_names[filemd5] = filename
                self.peer4files[filemd5][sessionid] = []
                # The first position of the list is the length of the file
                self.peer4files[filemd5][sessionid].append(lenfile)

                string_parts = '1'*(int(lenfile/lenpart) +1)
                string_parts += '0'*(8- (int(lenfile/lenpart) +1)%8 )
                
                self.peer4files[filemd5][sessionid].append(string_parts)

            part_number = '%08d' %(int( lenfile/lenpart ) +1)
            connection.sendall( b'AADR' + part_number.encode())

        except Exception as e:
            print("Error occurs during add file operations")
            print("$> ", end='')
            sys.stdout.flush()
        finally:
            if not connection is None:
                connection.close()

    def _function_LOOK_server(self, connection):
        sessionid = recvall(connection, 16).decode()
        research_string = recvall(connection, 20).decode()

        if (sessionid not in self.logged_peers):
            connection.sendall(b'ALOO' + b'000')
            return
        
        num_idmd5 = 0
        files = []
        for md5, name in self.file_names.items():
            if research_string.strip() in name.strip():
                num_idmd5 += 1
                files.append( [] )
                files[-1].append( md5 )
                files[-1].append( name )
                key = random.choice(list(self.peer4files[md5].keys()))
                files[-1].append( '%10d' %self.peer4files[md5][key][0] )
                files[-1].append( '%06d' %part_size )
        
        idmd5_string = '%03d' %num_idmd5
        connection.send(b'ALOO' + idmd5_string.encode())
        for file in files:
            connection.sendall(file[0].encode() + file[1].ljust(100).encode() + file[2].encode() + file[3].encode())
        return


    def _function_FCHU_server(self, connection):
        sessionid = recvall(connection, 16).decode()
        file_md5 = recvall(connection, 32).decode()

        try:
            if (sessionid not in self.logged_peers):
                connection.sendall(b'AFCH' + b'000')
                return

            num_hitpeer = '%03d' %len( self.peer4files[file_md5] )
            connection.sendall(b'AFCH' + num_hitpeer.encode())

            for peerId, peerInfo in self.peer4files[file_md5].items():
                connection.sendall(self.logged_peers[peerId][0].encode() + self.logged_peers[peerId][1].encode() + peerInfo[1].encode())

        except Exception as e:
            print("Error occurs during research file operations")
            print("$> ", end='')
            sys.stdout.flush()
        finally:
            if not connection is None:
                connection.close()

    def _function_RPAD_server(self, connection):
        try:
            sessionId = recvall(connection,16).decode()
            md5 = recvall(connection,32).decode()
            part_num = int(recvall(connection,8).decode())

            self.downloaded_parts[md5][part_num] = 1

            # The file is in self.peer4files because the peer is downloading it from another peer

            if sessionId in self.peer4files[md5].keys():
                with self.lock:
                    parts_string = self.peer4files[md5][sessionId][1]
                    parts_list = list(parts_string)
                    parts_list[part_num] = '1'
                    parts_string = ''.join(parts_list)
                    self.peer4files[md5][sessionId][1] = parts_string

            else:
                with self.lock:
                    key = random.choice(list(self.peer4files[md5].keys()))
                    len_file = self.peer4files[md5][key][0]
                    self.peer4files[md5][sessionId] = [len_file]

                    parts_string = '0'*(int(len_file/part_size)+1)
                    parts_string += '0'*(8-len(parts_string)%8)
                    parts_list = list(parts_string)
                    parts_list[part_num] = '1'
                    parts_string = ''.join(parts_list)
                    self.peer4files[md5][sessionId].append( parts_string )
            
            tot_npart = '%08d' %self.peer4files[md5][sessionId][1].count('1')
            connection.sendall( b'APAD' + tot_npart.encode())


        except Exception as e:
            print("Error occurs during RPAD function.\n", e)
            print('$> ', end='')
            sys.stdout.flush()
        finally:
            if connection:
                connection.close()

if __name__ == "__main__":
    node = tracker(sys.argv[1], sys.argv[2], sys.argv[3])
    node.start()
