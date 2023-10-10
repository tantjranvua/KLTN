import socket
import threading
import os
import tqdm
import tensorflow as tf
from util import *

HEADER = 128
BUFFER_SIZE = 4096
FORMAT = 'utf-8'
SEPARATOR = "<SEPARATOR>"
RECEIVE_SUCCESS = "<RECEIVESUCCESS>"

MASTER_ADDR = ('172.16.1.136',5555)
WORKER_ADDR = ('172.16.1.136',5050)

worker_server = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
worker_server.bind(WORKER_ADDR)
worker_server.listen()

worker_client = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
worker_client.connect(MASTER_ADDR)

def get_model(worker_client:socket.socket):
    file_header = worker_client.recv(HEADER).decode(FORMAT).strip()
    file_name, file_size = file_header.split(SEPARATOR)
    file_name = os.path.basename(file_name)
    file_size = int(file_size)
    progress = tqdm.tqdm(range(file_size), f"Receiving  {file_name}", disable = True, unit="B", unit_scale=True, unit_divisor=1024)

    with open(os.path.join(file_name), "wb") as f:
        readed = 0
        while readed<file_size:
            # read 4096 bytes from the socket (receive)
            bytes_read = worker_client.recv(BUFFER_SIZE)
            # write to the file the bytes we just received
            f.write(bytes_read)
            readed+=len(bytes_read)
            # update the progress bar
            progress.update(len(bytes_read))
    progress = None

    # model=tf.keras.models.load_model(file_name)
    os.remove(file_name)
    worker_client.send(mess_to_header(RECEIVE_SUCCESS))

    # return model

def get_config(worker_client:socket.socket):
    len_recv_bit = worker_client.recv(HEADER)
    if not len(len_recv_bit):
        raise Exception('[Fail], config not receive')
    len_recv = len_recv_bit.decode(FORMAT).strip()
    len_recv = int(len_recv)
    bytes_read = bytearray()
    readed = 0
    while readed<len_recv:
        packet = worker_client.recv(len_recv-readed)
        bytes_read.extend(packet)
        readed += len(packet)
    config = pickle.loads(bytes_read)
    worker_client.send(mess_to_header(RECEIVE_SUCCESS))
    return config

model = get_model(worker_client)
config = get_config(worker_client)