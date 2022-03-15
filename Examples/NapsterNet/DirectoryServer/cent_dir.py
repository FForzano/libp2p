import threading, random, socket
from string import ascii_uppercase, digits
from tkinter import E
#import doublelisten as dl
import napsterprotocol as np
from utils import recvall

server_port = 3000
max_thread = 100
max_pkt_size = 4048
sessionid_size = 16

lock = threading.Lock()

# NB: acquire lock before modify this structure!
logged_peer = {} # dictionary with {SessionId:(IPP2P,PP2P)}
peer4files = {} # dictionary with {filemd5:[SessionIds]}
file_names = {} # dictionary with {filemd5:name}
file_downloads = {} # dictionary with {filemd5:number_of_downloads}

def logout(sessionid):
    '''
    logout(sessionid)
    logout execute the logout of the sessionid peer. All its files are removed and the 
    number of deleted file is returned.
    '''

    global file_names
    global peer4files
    del_num = 0
    with lock:
        del logged_peer[sessionid]
        temp_peer4files = {}
        temp_file_names = {}

        for file,peers in peer4files.items():
            if sessionid in peers:
                peer4files[file].remove(sessionid)
                del_num += 1
                if peer4files[file]:
                    temp_peer4files[file] = peer4files[file]
                    temp_file_names[file] = file_names[file]
            else:
                temp_peer4files[file] = peer4files[file]
                temp_file_names[file] = file_names[file]
        peer4files = temp_peer4files
        file_names = temp_file_names

    return del_num

def num3dig(number_string):
    if len(number_string) == 1:
        return "00" + number_string
    if len(number_string) == 2:
        return "0" + number_string
    else:
        return number_string

def read_instruction(connection):
    try:
        buff = recvall(connection, 4)
        inst_code = buff.decode()

        if inst_code == "LOGI":
            buff += recvall(connection, 60)
        elif inst_code == "ADDF":
            buff += recvall(connection, 16+32+100)
        elif inst_code == "DELF":
            buff += recvall(connection, 16+32)
        elif inst_code == "FIND":
            buff += recvall(connection, 16+20)
        elif inst_code == "RETR":
            buff += recvall(connection, 32)
        elif inst_code == "DREG":
            buff += recvall(connection, 16+32)
        elif inst_code == "LOGO":
            buff += recvall(connection, 16)
    except Exception as e:
        print(e)
        raise e 
        return b''
    return buff

def thread_function(conn_socket):
    sessionid = ""
    global peer4files
    global file_names
    global file_downloads

    print("new thread for peer connection")
    try:
        while True:
            recv_data=read_instruction(conn_socket)
            if len(recv_data.decode())<=0:
                # magari logout
                conn_socket.close()
                break

            # VERIFICA CONNESSIONE

            recv_instruction = np.napster_parser(recv_data)

            if recv_instruction[0] == "LOGI":
                # manca il caso di fail

                try:
                    if (recv_instruction[1],'%05d'%int(recv_instruction[2])) in logged_peer.values():
                        # return SessionId
                        for key,value in logged_peer.items():
                            if value == (recv_instruction[1],'%05d'%int(recv_instruction[2])):
                                msg=np.napster_revparser(["ALGI",key])
                                break

                    else:
                        # If is not logged jet
                        letters = ascii_uppercase + digits
                        SessionId = ''.join(random.choice(letters) for i in range(sessionid_size))
                        # SessionId must be unique:
                        while SessionId in logged_peer.keys():
                            SessionId = ''.join(random.choice(letters) for i in range(sessionid_size))
                        
                        with lock:
                            logged_peer[SessionId] = (recv_instruction[1],'%05d'%int(recv_instruction[2]))
                        msg=np.napster_revparser(["ALGI",SessionId])
                        #return SessionId
                    
                except Exception:
                    msg = np.napster_revparser(["ALGI","0000000000000000"])

                #try:
                #print(msg)
                conn_socket.sendall(msg)

                
            elif recv_instruction[0] == "ADDF":

                filemd5 = recv_instruction[2]
                sessionid = recv_instruction[1]
                filename = recv_instruction[3]

                # loggin control
                if sessionid not in logged_peer.keys():
                    # If peer is not logged, the null answer is sent.
                    resp = np.napster_revparser(["AADD","000"])
                    conn_socket.sendall(resp)

                else:
                    # Actions for logged users

                    if filemd5 in peer4files.keys():
                        # if the file is in the directory jet
                        if sessionid in peer4files[filemd5]:
                            # if the user is not listed jet
                            with lock:
                                file_names[filemd5] = filename
                        else:
                            with lock:
                                peer4files[filemd5].append(sessionid)
                                file_names[filemd5] = filename
                    else:
                        # if the file in not in the directory jet
                        with lock:
                            peer4files[filemd5] = [sessionid]
                            file_names[filemd5] = filename
                            file_downloads[filemd5] = 0
                    
                    # The #copy field must be 3B size
                    number_files = num3dig(str(len(peer4files[filemd5])))
                    
                    resp = np.napster_revparser(["AADD",number_files])
                    conn_socket.sendall(resp)

                    # debug print
                    #print("logged user:\n",logged_peer,"\npeer for files:\n", peer4files, "\nFiles name:\n", file_names)
                
            elif recv_instruction[0] == "DELF":
                filemd5 = recv_instruction[2]
                sessionid = recv_instruction[1]

                # loggin control
                if sessionid not in logged_peer.keys():
                    # If peer is not logged, the null answer is sent.
                    resp = np.napster_revparser(["ADEL","000"])
                    conn_socket.sendall(resp)

                else:
                    resp = ""
                    if filemd5 not in peer4files.keys():
                        # file not in the directory
                        resp = np.napster_revparser(["ADEL","999"])
                    
                    elif sessionid not in peer4files[filemd5]:
                        # file in the directory but the peer is not one of the owners
                        resp = np.napster_revparser(["ADEL","999"])

                    else:
                        # It is possible to remove the file
                        removedrecord_flag = False
                        with lock:
                            peer4files[filemd5].remove(sessionid)
                            if not peer4files[filemd5]:
                                print("deleting dictionary record...")
                                del peer4files[filemd5]
                                del file_names[filemd5]
                                removedrecord_flag = True
                        
                        if not removedrecord_flag:
                            number_files = num3dig(str(len(peer4files[filemd5])))

                        else:
                            number_files = "000"

                        resp = np.napster_revparser(["ADEL",number_files])
                    
                    # send message
                    conn_socket.sendall(resp)
                    
            elif recv_instruction[0] == "FIND":
                research_string = recv_instruction[2]
                sessionid = recv_instruction[1]

                # loggin control
                if sessionid not in logged_peer.keys():
                    # If peer is not logged, the null answer is sent.
                    resp = np.napster_revparser(["AFIN","000"])
                    conn_socket.sendall(resp)
                
                res_list = ["AFIN","000"]

                if research_string.strip() == "*":
                    for file_md5,file_n in file_names.items():
                        # increment the number of md5 founded
                        new_n_md5 = num3dig(str(int(res_list[1])+1))

                        res_list[1]=new_n_md5

                        # add the md5 file, the relative name and the number of copy to the answer
                        res_list.append(file_md5)
                        res_list.append(file_n)
                        res_list.append(num3dig(str(len(peer4files[file_md5]))))
                        for peer in peer4files[file_md5]:
                            res_list.append(logged_peer[peer][0])
                            res_list.append(logged_peer[peer][1])

                else:
                    for file_md5,file_n in file_names.items():
                        if research_string.lower().strip() in file_n.lower().strip():
                            # increment the number of md5 founded
                            new_n_md5 = num3dig(str(int(res_list[1])+1))

                            res_list[1]=new_n_md5

                            # add the md5 file, the relative name and the number of copy to the answer
                            res_list.append(file_md5)
                            res_list.append(file_n)
                            res_list.append(num3dig(str(len(peer4files[file_md5]))))
                            for peer in peer4files[file_md5]:
                                res_list.append(logged_peer[peer][0])
                                res_list.append(logged_peer[peer][1])

                resp = np.napster_revparser(res_list)
                #print(resp)
                conn_socket.sendall(resp)

            elif recv_instruction[0] == "DREG":
                sessionid = recv_instruction[1]
                file_md5 = recv_instruction[2]

                # loggin control
                if sessionid not in logged_peer.keys():
                    # If peer is not logged, the null answer is sent.
                    resp = np.napster_revparser(["ADRE","00000"])
                    conn_socket.sendall(resp)

                else:
                    file_downloads[file_md5] = file_downloads[file_md5]+1

                    num_down = str(file_downloads[file_md5])
                    num_down_five = ""
                    for i in range(0,5-len(num_down)):
                        num_down_five = num_down_five + "0"
                    num_down_five = num_down_five + num_down
                    resp_list = ["ADRE",num_down_five]

                    conn_socket.sendall(np.napster_revparser(resp_list))

            elif recv_instruction[0] == "LOGO":
                sessionid = recv_instruction[1]

                # loggin control
                if sessionid not in logged_peer.keys():
                    # If peer is not logged, the null answer is sent.
                    resp = np.napster_revparser(["ALGO","000"])
                    conn_socket.sendall(resp)

                else:
                    deleted = logout(sessionid)
                    conn_socket.sendall(np.napster_revparser(["ALGO",num3dig(str(deleted))]))
                
                print("logged peer: ", logged_peer)
                print("peers for file: ", peer4files)

            else:
                raise Exception("Invalid instruction.")
                

            #elif recv_instruction[0] == "ADDF":

    except Exception as e:
        print("Terminating the thread...")
        #raise e
    finally:
        # For any problem in connection the peer is logged out and the connection is closed
        '''
        if sessionid in logged_peer.keys():
            # If peer is logged, then loggout.
            logout(sessionid)
        '''

        conn_socket.close()


if __name__ == "__main__":

    try:
        '''
        server_sock = dl.create_server_sock(("", server_port), queue_size=30)
        if not dl.has_dual_stack(server_sock):
            server_sock.close()
            server_sock = dl.MultipleSocketsListener([("0.0.0.0", server_port), ("::", server_port)])
        '''
        if socket.has_dualstack_ipv6():
            server_sock = socket.create_server(("", int(server_port)), family=socket.AF_INET6, dualstack_ipv6=True)
        else:
            print("Dual stack not avaible.")
            server_sock = socket.create_server(("", int(server_port)))
        # Creation of a double listener socket in both IPv4 and IPv6.

        while True:
            print("Try to accept connection")
            peer_conn, peer_addr = server_sock.accept() # peer_conn is the connection socket, peer_addr is a tuple of (ip_addr,port,etc) 
            # handle new connection
            # EVENTUALI CONTROLLI

            print("Connection accepted")

            peer_thread = threading.Thread(target=thread_function,args=(peer_conn,))
            #peer_thread.daemon = True
            # creation of a new thread for the peer request
            peer_thread.start()
            #peer_conn.close()

    except (Exception, KeyboardInterrupt):
        print("\nShutdown the server...")
        #peer_conn.close()
        #server_sock.close()