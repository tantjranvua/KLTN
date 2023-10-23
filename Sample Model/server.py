import os
from util import *

# MASTER_ADDR = ('172.16.7.241',5555)
MASTER_ADDR = ('192.168.1.103',5555)
MODELFILE = 'test.png'

master_server = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
master_server.bind(MASTER_ADDR)
master_server.listen()

# model= modelbuild.buildmodel().compiled_model()
# model.save(MODELFILE)
# save_file_event = Event()
# save_file_event.set()

while True:

    worker_client, addr = master_server.accept()
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
    thread = threading.Thread(target=handle_client,args=(worker_client,addr))
    thread.start()