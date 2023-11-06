import threading
import time
# Shared resource
shared_resource = []

# Condition variable
condition = threading.Condition()

# Consumer thread
def consumer():
    # with condition:
    #     while len(shared_resource)==0:
    #         print("Consumer is waiting...")
    #         condition.wait()
    #     item = shared_resource.pop(0)
    #     print("Consumer consumed item:", item)
    # time.sleep(2)
    while True:
        print(1)
        time.sleep(1)
        with condition:
            # if len(shared_resource)==0:
            condition.wait()
            item = shared_resource.pop(0)
            print("Consumer consumed item:", item)
# Producer thread
def producer():
    run = 0
    while True:
        with condition:
            item = "New item"
            shared_resource.append(item)
            print("Producer produced item:", item)
            condition.notify_all()
        if run >5:
            run = 0
            time.sleep(7)
        else:
            run+=1
            time.sleep(0.5)


# Create and start the threads
consumer_thread = threading.Thread(target=consumer)
producer_thread = threading.Thread(target=producer)
consumer_thread.start()
producer_thread.start()