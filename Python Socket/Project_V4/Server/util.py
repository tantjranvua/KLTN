import socket
import tqdm
import pickle
import os
import random
import cv2 as cv
import numpy as np
from PIL import Image
import threading
from threading import Event
from collections import deque

HEADER = 128
BUFFER_SIZE = 4096
FORMAT = 'utf-8'
SEPARATOR = "<SEPARATOR>"
DISCONNECT_MESS = "<DISCONECT>"
RECEIVE_SUCCESS = "<RECEIVESUCCESS>"
GET_DATA = "<GETDATA>"
SEND_WEIGHT = "<SENDWEIGHT>"

config = {}
config['epochs'] = 10
config['batch_size'] = 32
config['steps_per_epoch'] = 1

def create_mess_header(mess):
    return f"{len(mess):<{HEADER}}".encode(FORMAT)


def mess_to_header(mess):
    return f"{mess:<{HEADER}}".encode(FORMAT)


def create_file_header(file_name,file_size):
    temp = f"{file_name}{SEPARATOR}{file_size}"
    return f"{temp:<{HEADER}}".encode(FORMAT)


def get_patch_list(folder_name,max_client = 2):
    class_list = os.listdir(folder_name)
    return_list = []
    tmp_list = []
    q = deque()

    if len(class_list)==2:
        for i,c in enumerate(class_list):
            for file_name in os.listdir(os.path.join(folder_name,c)):
                tmp_list.append((os.path.join(folder_name,c,file_name),i))
    
    random.shuffle(tmp_list)

    for i in range(max_client):
        return_list.append([])

    for i in range(len(tmp_list)):
        return_list[i%max_client].append(tmp_list[i])

    for i in range(max_client):
        q.append(return_list[i])

    return q
    

def send_model(client_socket:socket.socket,file_name,file_size):
    client_socket.send(create_file_header(file_name,file_size))

    progress = tqdm.tqdm(range(file_size), f"Sending  {file_name}",unit="B", unit_scale=True, unit_divisor=1024)
    with open(file_name, "rb") as f:
        while True:
            # read the bytes from the file
            bytes_read = f.read(BUFFER_SIZE)
            if not bytes_read:
                # file transmitting is done
                break
            # we use sendall to assure transimission in 
            # busy networks
            client_socket.sendall(bytes_read)
            progress.update(len(bytes_read))
    progress = None


    mess = client_socket.recv(HEADER).decode(FORMAT).strip()
    if mess==RECEIVE_SUCCESS:
        print('[Success], send model')
    else:
        print(mess)


def send_config(client_socket:socket.socket):
    config_dumps = pickle.dumps(config)
    try:
        client_socket.send(create_mess_header(config_dumps))
        client_socket.sendall(config_dumps)
    except:
        raise Exception("[No sigal], Fail to send config")
    mess = client_socket.recv(HEADER).decode(FORMAT).strip()
    if mess==RECEIVE_SUCCESS:
        pass
        # print('[Success], send data')
    else:
        print(mess)


def get_patch_data(patch,image_shape = (224,224)):
    x = np.empty((len(patch),image_shape[0],image_shape[1],3),dtype=np.uint8)
    y = np.empty((len(patch)),dtype=np.uint8)
    for i,img_info in enumerate(patch):
        img = np.array(Image.open(img_info[0]))
        img = cv.resize(img,image_shape)
        x[i]=img
        y[i]=img_info[1]
    return x,y
    

def send_patch_data(client_socket:socket.socket,patch_list:deque):
    if len(patch_list)==0:
        raise Exception("[Data], All patch are in use")
    patch = patch_list.popleft()
    patch_data = get_patch_data(patch)
    data_dumps = pickle.dumps(patch_data)
    try:
        client_socket.send(create_mess_header(data_dumps))
        client_socket.sendall(data_dumps)
    except:
        patch_list.appendleft(patch)
        raise Exception("[No sigal], Fail to send path data")
    mess = client_socket.recv(HEADER).decode(FORMAT).strip()
    if mess==RECEIVE_SUCCESS:
        pass
        # print('[Success], send data')
    else:
        print(mess)
    return patch


def receive_request_header(client_socket:socket.socket):
    try:
        request_header = client_socket.recv(HEADER)
        if not len(request_header):
            raise Exception("[Fail], request not receive")
        return request_header.decode(FORMAT).strip()
    except:
        raise Exception("[Fail], request not receive")

        
def receive_model_update_weights(client_socket:socket.socket):
    try:
        len_recv_bit = client_socket.recv(HEADER)
        if not len(len_recv_bit):
            return False
        len_recv = len_recv_bit.decode(FORMAT).strip()
        len_recv = int(len_recv)
        
        bytes_read = bytearray()
        readed = 0
        progress = tqdm.tqdm(range(len_recv), f"Receiving  weight",unit="B", unit_scale=True, unit_divisor=1024)
        while readed<len_recv:
            packet = client_socket.recv(len_recv-readed)
            bytes_read.extend(packet)
            readed += len(packet)
            progress.update(len(packet))
        progress = None
        diff_weights = pickle.loads(bytes_read)
        client_socket.send(mess_to_header(RECEIVE_SUCCESS))
        return diff_weights
    except Exception as e:
        print(e,'[Fail], weight not receive')
        return False

def update_weights(client_socket:socket.socket,model):
    diff_weights = receive_model_update_weights(client_socket)
    if diff_weights is False:
        raise Exception("[No sigal], connection loss")
    # check lock
    for i, weight in enumerate(diff_weights):
        model.weights[i].assign_add(weight)
        model.weights[i]


def send_update_weights(client_socket:socket.socket,model):
    weights = model.get_weights()
    weight_dumps = pickle.dumps(weights)
    try:
        client_socket.send(create_mess_header(weight_dumps))
        client_socket.sendall(weight_dumps)
    except:
        raise Exception("[No sigal], Fail to send updated weights")
    mess = client_socket.recv(HEADER).decode(FORMAT).strip()
    if mess==RECEIVE_SUCCESS:
        print('[Success], send weight')
    else:
        print(mess)
        

def handle_exception(e,client_socket:socket.socket,patch_list:deque, socket_dict:dict):
    print(e)
    try:
        patch_list.append(socket_dict[client_socket])
        del socket_dict[client_socket]
    except:
        pass
    client_socket.close() #
    print('Close connection!')

def handle_client(client_socket:socket.socket, addr:str, model, patch_list:deque, socket_dict:dict, save_file_event: Event):
    # get request
    print(f'[ACTIVE CONNECTIONS] {threading.active_count()-1}')
    while True:
        try:
            request = receive_request_header(client_socket)
        except Exception as e:
            handle_exception(e,client_socket,patch_list,socket_dict)
            return
        
        ## send data
        if request == GET_DATA:
            try:
                patch = send_patch_data(client_socket,patch_list)
                if socket_dict.get(client_socket,0)!=0:
                    patch_list.append(socket_dict[client_socket])
                socket_dict[client_socket] = patch

            except Exception as e:
                handle_exception(e,client_socket,patch_list,socket_dict)
                return

        # update weight
        if request == SEND_WEIGHT:
            try:
                update_weights(client_socket,model)
                save_file_event.clear()
                print(f"[Update Weights] update from {addr}")
                send_update_weights(client_socket,model)
                print(f"[Send updated Weights] to {addr}")
            except Exception as e:
                handle_exception(e,client_socket,patch_list,socket_dict)
                return