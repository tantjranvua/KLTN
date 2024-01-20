import socket
import threading
import tqdm
import time
import pickle
import netifaces
import tensorflow as tf
import modelbuild
from queue import Queue
from threading import Event
import sys

HEADER = 128
BUFFER_SIZE = 4096
FORMAT = 'utf-8'
SEPARATOR = "<SEPARATOR>"
RECEIVE_SUCCESS = "<RECEIVESUCCESS>"
SEND_DATA = "<SENDDATA>"
SEND_MODEL = "<SENDMODEL>"
SEND_GRADIENT = "<SENDGRADIENT>"

run = 0
epoch = 1

config = {}
config['epochs'] = 10
config['batch_size'] = 32
config['steps_per_epoch'] = 1

workers = []
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
        
def send_data(worker_client: socket.socket, data_flow:tf.keras.preprocessing.image.DirectoryIterator):
    data_dumps = pickle.dumps(data_flow.next())
    try:
        # progress = tqdm.tqdm(range(len(data_dumps)), f"Sending data", disable = True, unit="B", unit_scale=True, unit_divisor=1024)
        worker_client.send(create_mess_header(data_dumps))
        worker_client.sendall(data_dumps)
    except:
        raise Exception("[No sigal], Fail to send data")
    mess = worker_client.recv(HEADER).decode(FORMAT).strip()
    if mess==RECEIVE_SUCCESS:
        print('[Success], send data')
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

def optimize(gra_queue: Queue,model,test_data, save_file_event: Event):
    global workers
    global run
    global epoch
    x,y=test_data
    # while True:
    #     while gra_queue.empty() != True:
    #         print('[OPTIMIZING]', gra_queue.qsize())
            
    #         # get gradient tu gradient queue
    #         gradient = gra_queue.get()
    #         print(gradient)
    #         time.sleep(5)
    #         model = gradient*-1
    #         model_dumps = pickle.dumps(model)
            
    #         #send model to all worker in worker list
    #         workers_lock.acquire()
    #         for worker in workers:
    #             print('Server send model after sending', model)
    #             worker.send(mess_to_header(SEND_MODEL))
    #             worker.send(create_mess_header(model_dumps))
    #             worker.sendall(model_dumps)
    #         mess = worker.recv(HEADER).decode(FORMAT).strip()
    #         if mess==RECEIVE_SUCCESS:
    #             print('[Success], send model')
    #         else:
    #             print(mess)
    #         workers_lock.release()
    while True:
        with gra_condition:
            print('[OPTIMIZING]', gra_queue.qsize())
            while gra_queue.empty() == True:
                gra_condition.wait()
                
            # get gradient tu gradient queue
            gradient = gra_queue.get()
            model.optimize_model(grads= gradient)
            save_file_event.clear
            model_dumps = pickle.dumps(model.model.get_weights())
            
            if(run== 77):
                model.model.save(('model1'+str(epoch)+'.h5'))
            
            #send model to all worker in worker list
            for worker in workers:
                try:
                    worker.send(mess_to_header(SEND_MODEL))
                    worker.send(create_mess_header(model_dumps))
                    worker.sendall(model_dumps)
                    mess = worker.recv(HEADER).decode(FORMAT).strip()
                    if mess==RECEIVE_SUCCESS:
                        print('[Success], send model')
                    else:
                        print(mess)
                except:
                    workers.remove(worker)
    
def master_handle_client(worker_client:socket.socket, addr:str, gra_queue: Queue, data_flow:tf.keras.preprocessing.image.DirectoryIterator):
    data_flow.batch_size = config['batch_size'] * 10
    data_size = len(data_flow)
    global run
    global epoch
    global workers
    #connect to worker server
    master_client = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
    master_client.connect((addr[0],5678))
    workers.append(master_client)
    # get request
    print(f'[ACTIVE CONNECTIONS]')
    while True:
        print('-----------Epoch:',epoch,'-Step:',run)
        try:
            request = receive_request_header(worker_client)
        except Exception as e:
            print(e)
            return
        
        if request == SEND_DATA:
            try:
                print(request)
                send_data(worker_client,data_flow)
                run +=1
                if run==data_size:
                    print('----Done epoch')
                    epoch +=1
                    if epoch ==16:
                        sys.exit()
                    run = 0
            except Exception as e:
                print(e)
                return
            
        if request == SEND_GRADIENT:
            try:
                print('[GET]', request)
                gradient = get_gradient(worker_client)
                with gra_condition:
                    gra_queue.put(gradient)
                    gra_condition.notify()
                
            except Exception as e:
                print(e)
                return
 