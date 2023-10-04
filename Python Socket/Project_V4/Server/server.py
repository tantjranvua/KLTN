import os
import socket
import threading

import util
import modelbuild
PORT = 65432
HOST = '172.16.1.136'
ADDR = (HOST,PORT)
MODELFILE = 'model.h5'
DATA_FOLDER = 'train'

patch_list = util.get_patch_list(DATA_FOLDER)
num_step = len(patch_list)
socket_dict = {}
server_socket = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
server_socket.bind(ADDR)
server_socket.listen()

model= modelbuild.buildmodel().compiled_model()
model.save(MODELFILE)

save_file_event = util.Event()
save_file_event.set()


print(f"Sever Connected on {HOST}")
socket_list = [server_socket]



while True:

    client_socket, addr = server_socket.accept()
    print(f'Conection {addr}')
    try:
        if not save_file_event.is_set():
            model.save(MODELFILE)
            save_file_event.set()
        file_name = MODELFILE
        file_size = os.path.getsize(file_name)
        util.send_model(client_socket,file_name,file_size)
        util.send_config(client_socket)
    except:
        print('[File], file name does not exist!!!')
        client_socket.close()
        print('Close connection!')
        continue
    thread = threading.Thread(target=util.handle_client,args=(client_socket,
                                                                addr,
                                                                model,
                                                                patch_list,
                                                                socket_dict,
                                                                save_file_event))
    thread.start()

    