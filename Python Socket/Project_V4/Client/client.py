import os
import gc
import tqdm # not build-in
import socket
import pickle
import threading
import numpy as np

import tensorflow as tf # not build-in
from collections import deque
from datetime import datetime


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
    progress = tqdm.tqdm(range(file_size), f"Receiving  {file_name}", disable = True, unit="B", unit_scale=True, unit_divisor=1024)

    with open(os.path.join(file_name), "wb") as f:
        readed = 0
        while readed<file_size:
            # read 4096 bytes from the socket (receive)
            bytes_read = client_socket.recv(BUFFER_SIZE)
            # write to the file the bytes we just received
            f.write(bytes_read)
            readed+=len(bytes_read)
            # update the progress bar
            progress.update(len(bytes_read))
    progress = None

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
    bytes_read = bytearray()
    readed = 0
    while readed<len_recv:
        packet = client_socket.recv(len_recv-readed)
        bytes_read.extend(packet)
        readed += len(packet)
    config = pickle.loads(bytes_read)
    client_socket.send(mess_to_header(RECEIVE_SUCCESS))
    return config


def get_patch_data(client_socket:socket.socket):
    client_socket.send(mess_to_header(GET_DATA))

    data_header = client_socket.recv(HEADER)
    if not len(data_header):
        raise Exception('[Fail], weight not receive')
    len_recv = data_header.decode(FORMAT).strip()
    len_recv = int(data_header)

    bytes_read = bytearray()
    readed = 0
    progress = tqdm.tqdm(range(len_recv), f"Receiving  Data", disable = True, unit="B", unit_scale=True, unit_divisor=1024)
    
    while readed<len_recv:
        packet = client_socket.recv(len_recv-readed)
        bytes_read.extend(packet)
        readed += len(packet)
        progress.update(len(packet))
    progress = None
    patch_data = pickle.loads(bytes_read)
    client_socket.send(mess_to_header(RECEIVE_SUCCESS))
    return patch_data


def send_diff_weights(client_socket:socket.socket,model, tmp_weights):
    diff_weights = []
    for i, weight in enumerate(model.get_weights()):
        diff_weights.append(weight-tmp_weights[i])
    diff_weights_dumps = pickle.dumps(diff_weights)
    client_socket.send(create_mess_header(diff_weights_dumps))
    client_socket.sendall(diff_weights_dumps)
    mess = client_socket.recv(HEADER).decode(FORMAT).strip()
    if mess==RECEIVE_SUCCESS:
        # print('[Success], Object send')
        pass
    else:
        raise Exception('[Fail], Object send')


def receive_update_weights(client_socket:socket.socket,model):
    len_recv_bit = client_socket.recv(HEADER)
    if not len(len_recv_bit):
        raise Exception('[Fail], weight not receive')
    len_recv = len_recv_bit.decode(FORMAT).strip()
    len_recv = int(len_recv)
    bytes_read = bytearray()
    readed = 0
    progress = tqdm.tqdm(range(len_recv), f"Receiving  weight", disable = True, unit="B", unit_scale=True, unit_divisor=1024)
    while readed<len_recv:
        packet = client_socket.recv(len_recv-readed)
        bytes_read.extend(packet)
        readed += len(packet)
        progress.update(len(packet))
    progress = None
    new_weight = pickle.loads(bytes_read)
    client_socket.send(mess_to_header(RECEIVE_SUCCESS))
    model.set_weights(new_weight)
    del new_weight


def update_weight(client_socket:socket.socket,model,tmp_weights):
    client_socket.send(mess_to_header(SEND_WEIGHT))
    send_diff_weights(client_socket,model,tmp_weights)
    receive_update_weights(client_socket,model)


def get_data_with_thread(client_socket:socket.socket,data_queue:deque):
    # print('[Start], get data with thread')
    data_queue.append(get_patch_data(client_socket))
    # print('[End], get data with thread')



model = get_model(client_socket)
model.compile(loss = model.loss,optimizer=model.optimizer, metrics=['acc'])
config = get_config(client_socket)

epochs = config['epochs']
steps_per_epoch = config['steps_per_epoch']
batch_size = config['batch_size']

data_queue = deque()
data_queue.append(get_patch_data(client_socket))
start=datetime.now()
for i in range(epochs):
    for j in range(steps_per_epoch):
        gc.collect() # do not del this line
        tmp_weights = model.get_weights()

        if len(data_queue)==1:
            x,y = data_queue.popleft()
            x = (x/255).astype(np.float16)

        if len(data_queue)<1:
            thread = threading.Thread(target=get_data_with_thread,args=(client_socket,data_queue))
            thread.start()

        print(f'[RUN TIME], Epoch {i+1}/{epochs} : Step {j+1}/{steps_per_epoch}')
        model.fit(x,y,batch_size=batch_size,epochs=i+1,initial_epoch = i,verbose=2)

        try:
            thread.join()
            update_weight(client_socket,model,tmp_weights)
            # print('[Success], update model')
        except Exception as e:
            print(e)

print("--- %s ---" % (datetime.now()-start))

client_socket.close()