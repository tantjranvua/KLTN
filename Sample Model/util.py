import socket
import threading
import tqdm
import time
import pickle
import netifaces
from queue import Queue
from threading import Event

HEADER = 128
BUFFER_SIZE = 4096
FORMAT = 'utf-8'
SEPARATOR = "<SEPARATOR>"
RECEIVE_SUCCESS = "<RECEIVESUCCESS>"
SEND_DATA = "<SENDDATA>"
SEND_MODEL = "<SENDMODEL>"
SEND_GRADIENT = "<SENDGRADIENT>"

config = {}
config['epochs'] = 10
config['batch_size'] = 32
config['steps_per_epoch'] = 1
workers = []
workers_lock = threading.Lock() #lock synchrony worker list
gra_lock = threading.Lock() #lock synchrony gradient queue
gra_condition = threading.Condition() #condition call optimize after get gradient

def get_ip_address():
    iface = netifaces.gateways()['default'][netifaces.AF_INET][1]
    ip = netifaces.ifaddresses(iface)[netifaces.AF_INET][0]['addr']
    return ip

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
    
def send_model_init(worker_client:socket.socket,file_name,file_size):
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
        print('[Success], send config')
    else:
        print(mess)
        
def get_gradient(worker_client:socket.socket):
    len_recv_bit = worker_client.recv(HEADER)
    if not len(len_recv_bit):
        raise Exception('[Fail], gradient not receive')
    len_recv = len_recv_bit.decode(FORMAT).strip()
    len_recv = int(len_recv)
    bytes_read = bytearray()
    readed = 0
    while readed<len_recv:
        packet = worker_client.recv(len_recv-readed)
        bytes_read.extend(packet)
        readed += len(packet)
    gradient = pickle.loads(bytes_read)
    worker_client.send(mess_to_header(RECEIVE_SUCCESS))
    return gradient

def optimize(gra_queue: Queue,tmp):
    global workers
    with gra_condition: #luong doi cho den khi nhan duoc gradient va su ly den kkhi het gradient
        while gra_queue.empty() == True:
            gra_condition.wait()
        print('[OPTIMIZING]')
        # get gradient tu gradient queue
        gra_lock.acquire()
        gradient = gra_queue.get()
        gra_lock.release()
        
        print(gradient)
        time.sleep(5)
        model = gradient*-1
        model_dumps = pickle.dumps(model)
        
        #send model to all worker in worker list
        workers_lock.acquire()
        for worker in workers:
            print('Server send model')
            worker.send(mess_to_header(SEND_MODEL))
            worker.send(create_mess_header(model_dumps))
            worker.sendall(model_dumps)
        mess = worker.recv(HEADER).decode(FORMAT).strip()
        if mess==RECEIVE_SUCCESS:
            print('[Success], send config')
        else:
            print(mess)
        workers_lock.release()

    
def master_handle_client(worker_client:socket.socket, addr:str, gra_queue: Queue):
    global workers
    #connect to worker server
    master_client = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
    master_client.connect((addr[0],5678))
    workers_lock.acquire()
    workers.append(master_client)
    workers_lock.release()
    # get request
    print(f'[ACTIVE CONNECTIONS]')
    while True:
        try:
            request = receive_request_header(worker_client)
        except Exception as e:
            print(e)
            return
        
        if request == SEND_DATA:
            try:
                print(request)
            except Exception as e:
                print(e)
                return
            
        if request == SEND_GRADIENT:
            try:
                print(request)
                gradient = get_gradient(worker_client)
                
                #put gradient to gradient queue
                gra_lock.acquire()
                gra_queue.put(gradient)
                gra_condition.notify()
                gra_lock.release()
            except Exception as e:
                print(e)
                return
