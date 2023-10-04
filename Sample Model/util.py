import socket
import threading

HEADER = 128
BUFFER_SIZE = 4096
FORMAT = 'utf-8'
SEPARATOR = "<SEPARATOR>"

def create_mess_header(mess):
    return f"{len(mess):<{HEADER}}".encode(FORMAT)


def mess_to_header(mess):
    return f"{mess:<{HEADER}}".encode(FORMAT)

def create_file_header(file_name,file_size):
    temp = f"{file_name}{SEPARATOR}{file_size}"
    return f"{temp:<{HEADER}}".encode(FORMAT)

def receive_request_header(client_socket:socket.socket):
    try:
        request_header = client_socket.recv(HEADER)
        if not len(request_header):
            raise Exception("[Fail], request not receive")
        return request_header.decode(FORMAT).strip()
    except:
        raise Exception("[Fail], request not receive")

def handle_client(worker_client:socket.socket, addr:str):
    # get request
    print(f'[ACTIVE CONNECTIONS] {threading.active_count()-1}')
    while True:
        try:
            request = receive_request_header(worker_client)
        except Exception as e:
            # handle_exception(e,worker_client,patch_list,socket_dict)
            return
        
