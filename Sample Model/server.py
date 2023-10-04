import socket
import threading

HEADER = 128
BUFFER_SIZE = 4096
FORMAT = 'utf-8'
SEPARATOR = "<SEPARATOR>"

MASTER_ADDR = ('172.16.1.136',5555)

master_server = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
master_server.bind(MASTER_ADDR)
master_server.listen()

while True:

    worker_client, addr = master_server.accept()
    print(f'Conection {addr}')
    # thread = threading.Thread(target=util.handle_client,args=(worker_client,
    #                                                             addr,
    #                                                             model,
    #                                                             patch_list,
    #                                                             socket_dict,
    # #                                                             save_file_event))
    # thread.start()