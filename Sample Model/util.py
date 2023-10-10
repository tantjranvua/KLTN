import socket
import threading
import tqdm
import pickle
from threading import Event

HEADER = 128
BUFFER_SIZE = 4096
FORMAT = 'utf-8'
SEPARATOR = "<SEPARATOR>"
RECEIVE_SUCCESS = "<RECEIVESUCCESS>"

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

def receive_request_header(worker_client:socket.socket):
    try:
        request_header = worker_client.recv(HEADER)
        if not len(request_header):
            raise Exception("[Fail], request not receive")
        return request_header.decode(FORMAT).strip()
    except:
        raise Exception("[Fail], request not receive")
    
def send_model(worker_client:socket.socket,file_name,file_size):
    worker_client.send(create_file_header(file_name,file_size))

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
            worker_client.sendall(bytes_read)
            progress.update(len(bytes_read))
    progress = None
    
    mess = worker_client.recv(HEADER).decode(FORMAT).strip()
    if mess==RECEIVE_SUCCESS:
        print('[Success], send model')
    else:
        print(mess)
    
def send_config(worker_client:socket.socket):
    config_dumps = pickle.dumps(config)
    try:
        worker_client.send(create_mess_header(config_dumps))
        worker_client.sendall(config_dumps)
    except:
        raise Exception("[No sigal], Fail to send config")
    mess = worker_client.recv(HEADER).decode(FORMAT).strip()
    if mess==RECEIVE_SUCCESS:
        pass
        # print('[Success], send data')
    else:
        print(mess)

def handle_client(worker_client:socket.socket, addr:str):
    # get request
    print(f'[ACTIVE CONNECTIONS] {threading.active_count()-1}')
    while True:
        try:
            request = receive_request_header(worker_client)
        except Exception as e:
            # handle_exception(e,worker_client,patch_list,socket_dict)
            return
        
