import argparse
from threading import Thread
import time
from socket import *
from os.path import *
import os
import struct
import hashlib
import math


def _argparse():
    parser = argparse.ArgumentParser(description="This is description!")
    parser.add_argument('--ip', action='store', required=True, dest='ip', help='ip')
    return parser.parse_args()


file_dir = 'share'
# --- ip identification ---
local_ip = ''  # ip address of this host
init = _argparse()
peer_ip = init.ip  # other peer' ip addresses

# --- ports identification ---
port = 21000  # TCP receive port (used for receiving file)


# --- The following codes are mainly divided into 3 parts: [Thread], [Module] and [Function] ---
# --- the function marked as [Thread] will be a real thread in the running time ---
# --- the function marked as [Module] can perform some important functions such as send file and detect online ---
# --- rhe function marked as [Function] just performs some essential function ---


# [Thread: send file by TCP]
def send_file(receiver_ip, receiver_port):
    while True:
        while True:
            try:
                sender_socket = socket(AF_INET, SOCK_STREAM)
                sender_socket.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
                sender_socket.connect((receiver_ip, receiver_port))
                break
            except Exception as e:
                pass


        while True:
            try:
                total_file_list = scan_file('share')
                for file_name in total_file_list:
                    file_size = os.path.getsize(file_name)
                    sender_socket.send(create_file_info(file_name))
                    while True:
                        file_flag_b = sender_socket.recv(4)
                        file_flag = struct.unpack('!I', file_flag_b)[0]
                        if file_flag == 0:
                            break
                        else: # file_flag = 1, 2, 3
                            sendFile(file_name, file_size, sender_socket)
            except:
                break


# [Function: traverse the file]
def scan_file(file_dir):
    flag = os.path.exists(file_dir)
    if not flag:
        os.mkdir(file_dir)
    file_list = []
    file_folder_list = os.listdir(file_dir)
    for file_folder_name in file_folder_list:
        suffixName = file_folder_name[-8:]
        if suffixName != '.download':
            if isfile(join(file_dir, file_folder_name)):
                file_list.append(join(file_dir, file_folder_name))
            else:
                file_list.extend(scan_file(join(file_dir, file_folder_name)))
    return file_list

# [Function: get file information]
def create_file_info(file_name):
    file_size = os.path.getsize(file_name)
    file_mtime = os.path.getmtime(file_name)
    file_md5 = create_file_md5(file_name)
    file_info = struct.pack('!QQd', len(file_name.encode()), file_size,
                            file_mtime) + file_name.encode() + file_md5.encode()
    return file_info


# [Function: get file md5]
def create_file_md5(file_name):
    file = open(file=file_name, mode='rb')
    file.seek(0)
    content = file.read(1024 * 1024 * 4)
    content_md5 = hashlib.md5(content).hexdigest()
    file.close()
    return content_md5


# [Module: send file by TCP]
def sendFile(file_name, file_size, sender_socket):
    file_name_length = len(file_name.encode())
    sender_socket.send(struct.pack('!I', file_name_length) + file_name.encode())
    for i in range(50):
        sender_socket.send(get_file_block(file_name, file_size, i))  # transfer the file by blocks
    sender_socket.close()


# [Function: get each file block for send]
def get_file_block(file_name, file_size, block_index):
    block_size = math.ceil(file_size / 10)
    f = open(file_name, 'rb')
    f.seek(block_index * block_size)
    file_block = f.read(block_size)
    f.close()
    return file_block


# [Thread: receive the peer's files]
def receive_file(local_ip, port):
    receiver_socket = socket(AF_INET, SOCK_STREAM)
    receiver_socket.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
    receiver_socket.bind((local_ip, port))
    receiver_socket.listen(128)
    while True:
        connection_socket, sender_addr = receiver_socket.accept()
        while True:
            try:
                file_info = connection_socket.recv(1500)
                file_size, file_mtime, file_name, file_md5 = unpack_file_info(file_info)
                file_flag = create_file_flag(file_name, file_mtime, file_md5)
                if file_flag == 0:
                    connection_socket.send(struct.pack('!I', file_flag))
                elif file_flag == 1:
                    write_file(file_name, file_size, file_flag, connection_socket)
                elif file_flag == 2:
                    # print('breakpoint resume')
                    os.remove(file_name + '.download')
                    write_file(file_name, file_size, file_flag, connection_socket)
                elif file_flag == 3:
                    os.remove(file_name)
                    write_file(file_name, file_size, file_flag, connection_socket)
            except:
                break


# [Function: decode the binary information sent from sender]
def unpack_file_info(file_info):
    file_name_length, file_size, file_mtime = struct.unpack('!QQd', file_info[:24])
    file_name = file_info[24:24 + file_name_length].decode()
    file_md5_b = file_info[24 + file_name_length:]
    file_md5 = file_md5_b.decode()
    return file_size, file_mtime, file_name, file_md5


# [Module: create the flag to indicate the file]
def create_file_flag(file_name, file_mtime, file_md5):
    """
     0: The file is the same as the peer's
     1: The file is added in peer's side, not in this side
     2: The file is shared, but not completely received
     3: Sender's file is updated
    """

    if not os.path.exists(file_name):
        if not os.path.exists(file_name + '.download'):
            file_flag = 1
        else:
            file_flag = 2
    else:
        host_file_md5 = create_file_md5(file_name)
        if file_md5 == host_file_md5:
            file_flag = 0
        else:
            host_file_mtime = os.path.getmtime(file_name)
            if host_file_mtime < file_mtime:
                file_flag = 3
            else:
                file_flag = 0
    return file_flag


# [Module: download the files]
def write_file(file_name, file_size, file_flag, connection_socket):
    print(file_name)
    path, rest_file_name = os.path.split(file_name)
    if not path == '':
        flag = os.path.exists(path)
        if not flag:
            os.makedirs(path)

    file_flag_b = struct.pack('!I', file_flag)
    connection_socket.send(file_flag_b)
    file_length = struct.unpack('!I', connection_socket.recv(4))[0]
    file_name = connection_socket.recv(file_length).decode()
    f = open(file=file_name + '.download', mode='wb')

    while True:
        text = connection_socket.recv(1024 * 64)
        f.write(text)
        if text == b'':  # the file is transferred completely
            break
    f.close()

    file_flag = 0
    file_flag_b = struct.pack('!I', file_flag)
    connection_socket.send(file_flag_b)
    os.rename(file_name + '.download', file_name)


def main():
    r = Thread(target=receive_file, args=(local_ip, port))
    r.start()
    s = Thread(target=send_file, args=(peer_ip, port))
    s.start()


if __name__ == '__main__':
    main()
