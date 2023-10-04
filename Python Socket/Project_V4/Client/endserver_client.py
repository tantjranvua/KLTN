import os
import socket
import pickle


import tensorflow as tf # not build-in


HEADER = 128
BUFFER_SIZE = 4096
PORT = 65432
HOST = '172.16.1.136'
ADDR = (HOST,PORT)
FORMAT = 'utf-8'
SEPARATOR = "<SEPARATOR>"
DISCONNECT_MESS = "<DISCONECT>"
RECEIVE_SUCCESS = "<RECEIVESUCCESS>"
GET_DATA = "<GETDATA>"
SEND_WEIGHT = "<SENDWEIGHT>"
client_socket = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
client_socket.connect(ADDR)


def create_mess_header(mess):
    return f"{len(mess):<{HEADER}}".encode(FORMAT)


def mess_to_header(mess):
    return f"{mess:<{HEADER}}".encode(FORMAT)


def get_model(client_socket:socket.socket):
    file_header = client_socket.recv(HEADER).decode(FORMAT).strip()
    file_name, file_size = file_header.split(SEPARATOR)
    file_name = os.path.basename(file_name)
    file_size = int(file_size)
    
    with open(os.path.join(file_name), "wb") as f:
        readed = 0
        while readed<file_size:
            bytes_read = client_socket.recv(BUFFER_SIZE)
            f.write(bytes_read)
            readed+=len(bytes_read)
            
    model=tf.keras.models.load_model(file_name)
    os.remove(file_name)
    client_socket.send(mess_to_header(RECEIVE_SUCCESS))

    return model


def get_config(client_socket:socket.socket):
    len_recv_bit = client_socket.recv(HEADER)
    if not len(len_recv_bit):
        raise Exception('[Fail], config not receive')
    len_recv = len_recv_bit.decode(FORMAT).strip()
    len_recv = int(len_recv)
    bytes_read = b""
    readed = 0
    while readed<len_recv:
        packet = client_socket.recv(len_recv)
        bytes_read += packet
        readed += len(packet)
    config = pickle.loads(bytes_read)
    client_socket.send(mess_to_header(RECEIVE_SUCCESS))
    return config


model = get_model(client_socket)
config = get_config(client_socket)


client_socket.close()