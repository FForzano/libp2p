'''
Useful functions for pharsing and reverse pharsing of napster messages.
'''

# Packets field size:
from ast import Bytes


LOGI = [4,55,5]
ALGI = [4,16]
ADDF = [4,16,32,100]
AADD = [4,3]
DELF = [4,16,32]
ADEL = [4,3]
FIND = [4,16,20]
AFIN = [4,3]
RETR = [4,32]
ARET = [4,6]#L BYTES
DREG = [4,16,32]
ADRE = [4,5]
LOGO = [4,16]
ALGO = [4,3]

def napster_parser(msg):
    '''
    [instruction, parameters] = napster_pharser(msg)
    napset_pharser decode from a msg the relative field. The lenght of the output list
    depends from the instruction type.
    '''

    msg = msg.decode()
    instruction_code = msg[0:4]
    #print(instruction_code)
    msg_list = []

    if instruction_code == "LOGI":
        i=0
        for dim in LOGI:
            msg_list.append(msg[i:(i+dim)])
            i=i+dim

    if instruction_code == "ALGI":
        i=0
        for dim in ALGI:
            msg_list.append(msg[i:(i+dim)])
            i=i+dim
        
    elif instruction_code == "ADDF":
        i=0
        for dim in ADDF:
            msg_list.append(msg[i:(i+dim)])
            i=i+dim

    elif instruction_code == "AADD":
        i=0
        for dim in AADD:
            msg_list.append(msg[i:(i+dim)])
            i=i+dim

    elif instruction_code == "DELF":
        i=0
        for dim in DELF:
            msg_list.append(msg[i:(i+dim)])
            i=i+dim
        
    elif instruction_code == "ADEL":
        i=0
        for dim in ADEL:
            msg_list.append(msg[i:(i+dim)])
            i=i+dim

    elif instruction_code == "FIND":
        i=0
        for dim in FIND:
            msg_list.append(msg[i:(i+dim)])
            i=i+dim

    elif instruction_code == "AFIN":
        '''
        msg_list = ["AFIN",#idmd5,[Filemd5_i,Filename_i,#copy_i,[peers]]]
        '''
        file_msg_size = [32,100,3]
        peer_msg_size = [55,5]
        i=0
        for dim in AFIN:
            msg_list.append(msg[i:(i+dim)])
            i=i+dim
        
        file_number = int(msg_list[-1])
        msg_list.append([]) # list of files
        for k in range(file_number):
            for dim in file_msg_size:
                msg_list[-1].append(msg[i:(i+dim)])
                i=i+dim
            #print(msg_list[-1])
            #print((msg_list[-1])[-1])
            peer_number = int(msg_list[-1][-1])
            msg_list[-1].append([]) # list of peer for files
            for j in range(peer_number):
                for dim_peer in peer_msg_size:
                    msg_list[-1][-1].append(msg[i:(i+dim_peer)])
                    i=i+dim_peer
            #print(msg_list)

    elif instruction_code == "DREG":
        i=0
        for dim in DREG:
            msg_list.append(msg[i:(i+dim)])
            i=i+dim
    
    elif instruction_code == "RETR":
        i=0
        for dim in RETR:
            msg_list.append(msg[i:(i+dim)])
            i=i+dim

    elif instruction_code == "ADRE":
        i=0
        for dim in ADRE:
            msg_list.append(msg[i:(i+dim)])
            i=i+dim

    elif instruction_code == "ARET":
        i=0
        for dim in ARET:
            msg_list.append(msg[i:(i+dim)])
            i=i+dim


    elif instruction_code == "LOGO":
        i=0
        for dim in LOGO:
            msg_list.append(msg[i:(i+dim)])
            i=i+dim
        
    elif instruction_code == "ALGO":
        i=0
        for dim in ALGO:
            msg_list.append(msg[i:(i+dim)])
            i=i+dim
    
    return msg_list

def napster_revparser(msg_list):
    #msg_string = ""
    msg_byte = "".encode()
    for item in msg_list:
        if isinstance(item,str):
            msg_byte += item.encode()
        else:
            msg_byte += item
        #msg_string = msg_string + item

    #return msg_string.encode()
    return msg_byte


# test
if __name__ == "__main__":

    msg = ["LOGI","127.000.000.001|2001:0db8:85a3:0000:0000:8a2e:0370:7334","00141"]
    print(msg)
    codified_msg = napster_revparser(msg)
    print(codified_msg)
    decod_msg = napster_parser(codified_msg)
    print(decod_msg)