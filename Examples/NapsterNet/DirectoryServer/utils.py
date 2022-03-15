def recvall(connection, buff):
    chunk = b''

    current_recv = connection.recv(buff)
    chunk += current_recv
    while len(chunk) != buff:
        current_recv = connection.recv(buff-len(chunk))
        chunk += current_recv

    return chunk