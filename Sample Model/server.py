import socket
import threading
import os
from util import *

MASTER_ADDR = ('172.16.1.136',5555)
HEADER = 128
BUFFER_SIZE = 4096
FORMAT = 'utf-8'
SEPARATOR = "<SEPARATOR>"
RECEIVE_SUCCESS = "<RECEIVESUCCESS>"
MODELFILE = 'test.txt'

master_server = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
master_server.bind(MASTER_ADDR)
master_server.listen()

# model= modelbuild.buildmodel().compiled_model()
# model.save(MODELFILE)
# save_file_event = Event()
# save_file_event.set()

while True:

    worker_client, addr = master_server.accept()
    print(f'Conection {addr}')
    try:
        # if not save_file_event.is_set():
        #     model.save(MODELFILE)
        #     save_file_event.set()
        file_name = MODELFILE
        file_size = os.path.getsize(file_name)
        send_model(worker_client,file_name,file_size)
        send_config(worker_client)
    except:
        print('[File], file name does not exist!!!')
        worker_client .close()
        print('Close connection!')
        continue
    # thread = threading.Thread(target=util.handle_client,args=(worker_client,
    #                                                             addr,
    #                                                             model,
    #                                                             patch_list,
    #                                                             socket_dict,
    # #                                                             save_file_event))
    # thread.start()