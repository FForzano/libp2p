'''
Useful functions for pharsing and reverse pharsing of napster messages.
'''

# Packets field size:
from ast import Bytes
from utils import recvall


LOGI = [4,55,5]
ALGI = [4,16]
ADDF = [4,16,32,100]
AADD = [4,3]
DELF = [4,16,32]
ADEL = [4,3]
FIND = [4,16,20]
AFIN = [4,3,32,100,3,55,5]
RETR = [4,32]
ARET = [4,6,5]#L BYTES
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
        
    elif instruction_code == "ADDF":
        i=0
        for dim in ADDF:
            msg_list.append(msg[i:(i+dim)])
            i=i+dim

    elif instruction_code == "DELF":
        i=0
        for dim in DELF:
            msg_list.append(msg[i:(i+dim)])
            i=i+dim
        
    elif instruction_code == "FIND":
        i=0
        for dim in FIND:
            msg_list.append(msg[i:(i+dim)])
            i=i+dim

    elif instruction_code == "DREG":
        i=0
        for dim in DREG:
            msg_list.append(msg[i:(i+dim)])
            i=i+dim

    elif instruction_code == "LOGO":
        i=0
        for dim in LOGO:
            msg_list.append(msg[i:(i+dim)])
            i=i+dim
        
    return msg_list

def napster_revparser(msg_list):
    msg_string = ""
    for item in msg_list:
        msg_string = msg_string + item

    return msg_string.encode()


# test
if __name__ == "__main__":

    msg = ["LOGI","127.000.000.001|2001:0db8:85a3:0000:0000:8a2e:0370:7334","00141"]
    print(msg)
    codified_msg = napster_revparser(msg)
    print(codified_msg)
    decod_msg = napster_parser(codified_msg)
    print(decod_msg)