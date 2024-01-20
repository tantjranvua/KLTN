import socket
import threading
import os
import tqdm
import tensorflow as tf
import numpy as np
import modelbuild
from util import *

HEADER = 128
BUFFER_SIZE = 4096
FORMAT = 'utf-8'
SEPARATOR = "<SEPARATOR>"
RECEIVE_SUCCESS = "<RECEIVESUCCESS>"
SEND_DATA = "<SENDDATA>"
SEND_MODEL = "<SENDMODEL>"
SEND_GRADIENT = "<SENDGRADIENT>"

IP_ADDR = get_ip_address()
MASTER_ADDR = ('172.16.5.246',5555)
# MASTER_ADDR = ('172.16.5.128',5555)
WORKER_ADDR = (IP_ADDR,5678)
model_cache = 0
model_lib = modelbuild.buildmodel()

worker_server = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
worker_server.bind(WORKER_ADDR)
worker_server.listen()
print('Connectingggggg')
worker_client = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
worker_client.connect(MASTER_ADDR)

def get_model_init(worker_client:socket.socket):
    print('Get Model')
    file_header = worker_client.recv(HEADER).decode(FORMAT).strip()
    file_name, file_size = file_header.split(SEPARATOR)
    print(file_name)
    file_name = 'test2.png'
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

    model=tf.keras.models.load_model(file_name)
    os.remove(file_name) 
    worker_client.send(mess_to_header(RECEIVE_SUCCESS))

    return model
    # return 0

def get_model(worker_client:socket.socket):
    len_recv_bit = worker_client.recv(HEADER)
    if not len(len_recv_bit):
        raise Exception('[Fail], model not receive')
    len_recv = len_recv_bit.decode(FORMAT).strip()
    len_recv = int(len_recv)
    bytes_read = bytearray()
    readed = 0
    while readed<len_recv:
        packet = worker_client.recv(len_recv-readed)
        bytes_read.extend(packet)
        readed += len(packet)
    model = pickle.loads(bytes_read)
    worker_client.send(mess_to_header(RECEIVE_SUCCESS))
    return model

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

def training(worker_client, data):
    global model_lib
    global model_cache
    print('Client Traing')
    (x_train,y_train) = data
    for i in range(10):
        if model_cache:
            # print('Update model')
            model_lib.model.set_weights(model_cache) 
            model_cache = 0
        x_batch_train = x_train[i*config['batch_size']:(i+1)*config['batch_size']]
        y_batch_train = y_train[i*config['batch_size']:(i+1)*config['batch_size']]
        y_batch_train = y_batch_train.reshape(-1,1)
        loss_value, grad = model_lib.train_step(x = x_batch_train,y = y_batch_train)
        print( "Training loss : %.4f"% (float(loss_value)))
        # model_lib.optimize_model(grad)
        send_gradient(worker_client=worker_client, gradient=grad)
    print("Train acc", model_lib.metrics.result())

def get_data(worker_client:socket.socket):
    print('[SEND] Client get data')
    worker_client.send(mess_to_header(SEND_DATA))
    
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
    print('[SEND] Client send gradient')
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

def worker_handle_client(master_client:socket.socket, addr:str):
    global model_cache
    while True:
        try:
            request = receive_request_header(master_client)
        except Exception as e:
            print(e)
            return
        if request == SEND_MODEL:
            try:
                model_cache = get_model(master_client)
            except Exception as e:
                print(e)
                return
        

def server(worker_server:socket.socket,model_cache):
    while True:
        master_client, addr = worker_server.accept()
        thread = threading.Thread(target=worker_handle_client, args=(master_client,addr),name='Worker_server')
        thread.start()
        
server_thread = threading.Thread(target=server,args=(worker_server,model_cache))
server_thread.start()

model_lib.model = get_model_init(worker_client)
config = get_config(worker_client)
data = get_data(worker_client)
# model_lib.model = model_cache
while True:
    # Cập nhật model    <-                            getmodel
    # Kiểm tra đã có data chưa  
    # training data     ->          getdata
    #     ->                        send gradient
    
    
    training(worker_client, data)
    data = get_data(worker_client)
    # get_data() -> update_model()
    # send gradient