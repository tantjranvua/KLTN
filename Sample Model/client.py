import socket
import threading
import os
import tqdm
import tensorflow as tf
import numpy as np
from util import *

HEADER = 128
BUFFER_SIZE = 4096
FORMAT = 'utf-8'
SEPARATOR = "<SEPARATOR>"
RECEIVE_SUCCESS = "<RECEIVESUCCESS>"
SEND_DATA = "<SENDDATA>"
SEND_MODEL = "<SENDMODEL>"
SEND_GRADIENT = "<SENDGRADIENT>"

# MASTER_ADDR = ('172.16.7.241',5555)
# WORKER_ADDR = ('172.16.7.241',5678)
MASTER_ADDR = ('192.168.1.103',5555)
WORKER_ADDR = ('192.168.1.103',5678)
model_cache = 0

worker_server = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
worker_server.bind(WORKER_ADDR)
worker_server.listen()
print('Connectingggggg')
worker_client = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
worker_client.connect(MASTER_ADDR)

def get_model(worker_client:socket.socket):
    print('Get Model')
    file_header = worker_client.recv(HEADER).decode(FORMAT).strip()
    file_name, file_size = file_header.split(SEPARATOR)
    file_name = 'test2'
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
    # os.remove(file_name)
    worker_client.send(mess_to_header(RECEIVE_SUCCESS))

    # return model
    return 0

def get_config(worker_client:socket.socket):
    print('Get config')
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

def training():
    print('Client Traing')
    time.sleep(3) 

def get_data(worker_client:socket.socket):
    len_recv_bit = worker_client.recv(HEADER)
    if not len(len_recv_bit):
        raise Exception('[Fail], data not receive')
    len_recv = len_recv_bit.decode(FORMAT).strip()
    len_recv = int(len_recv)
    bytes_read = bytearray()
    readed = 0
    while readed<len_recv:
        packet = worker_client.recv(len_recv-readed)
        bytes_read.extend(packet)
        readed += len(packet)
    data = pickle.loads(bytes_read)
    worker_client.send(mess_to_header(RECEIVE_SUCCESS))
    return data

def update_model(): 
    print('Client Updating')
    time.sleep(3)

def send_gradient(worker_client:socket.socket, gradient):
    print('Client send gradient')
    gradient_dumps = pickle.dumps(gradient)
    # progress = tqdm.tqdm(range(file_size), f"Sending  {file_name}",unit="B", unit_scale=True, unit_divisor=1024)
    worker_client.send(mess_to_header(SEND_GRADIENT))
    worker_client.send(create_mess_header(gradient_dumps))
    worker_client.sendall(gradient_dumps)
    mess = worker_client.recv(HEADER).decode(FORMAT).strip()
    if mess==RECEIVE_SUCCESS:
        print('[Success], send gradient')
    else:
        print(mess)

def handle_client(master_client:socket.socket, addr:str, model_cache):
    while True:
        try:
            request = receive_request_header(master_client)
        except Exception as e:
            print(e)
            return
        if request == send_model:
            try:
                model_cache = get_model(master_client)
            except Exception as e:
                print(e)
                return
        

def server(worker_server:socket.socket,model_cache):
    while True:
        master_client, addr = worker_server.accept()
        thread = threading.Thread(target=handle_client, args=(master_client,addr,model_cache))
        thread.start()
        
server_thread = threading.Thread(target=server,args=(worker_server,model_cache))
server_thread.start()

model = get_model(worker_client)
config = get_config(worker_client)

while True:
    # model = model_cache
    training()
    # get_data() -> update_model()
    send_gradient(worker_client=worker_client, gradient=np.arange(100))