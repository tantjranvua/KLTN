import time
import threading

shared_resource = []
condition = threading.Condition()

def producer():
    i=0
    while True:
        i+=1
        # time.sleep(0.001)
        with condition:
            print('PRODUCER adding item', i)
            shared_resource.append(i)
            condition.notify() # wake up sleeping consumers

def consumer():
    while True:
        with condition:
            while len(shared_resource)==0: # buffer is empty
                condition.wait() # wait for notification
            item = shared_resource.pop(0)
            print("+++++++ consumed item:", item)
            time.sleep(0.01)
threading.Thread(target=producer).start()
threading.Thread(target=consumer).start()