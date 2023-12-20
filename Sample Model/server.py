import os
import modelbuild
import tensorflow as tf
from util import *

IP_ADDR = get_ip_address()
MASTER_ADDR = (IP_ADDR,5555)
MODELFILE = 'model.h5'
gra_queue = Queue()

master_server = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
master_server.bind(MASTER_ADDR)
master_server.listen()

model= modelbuild.buildmodel()
model.model.save(MODELFILE)
save_file_event = Event()
save_file_event.set()

target_size = tuple(model.model.input_shape[1:3])
img_gen = tf.keras.preprocessing.image.ImageDataGenerator(rescale=1/255)
train_gen = img_gen.flow_from_directory('./data',target_size=(224, 224),class_mode="binary")

print(train_gen)


print('[SERVER] is running')
optimize_thread = threading.Thread(target=optimize, args=(gra_queue,0))
optimize_thread.start()
while True:

    worker_client, addr = master_server.accept()
    try:
        if not save_file_event.is_set():
            model.save(MODELFILE)
            save_file_event.set()
        file_name = MODELFILE
        file_size = os.path.getsize(file_name)
        send_model_init(worker_client,file_name,file_size)
        send_config(worker_client)
    except:
        print('[File], file name does not exist!!!')
        worker_client .close()
        print('Close connection!')
        continue
    thread = threading.Thread(target=master_handle_client,args=(worker_client, addr, gra_queue))
    thread.start()