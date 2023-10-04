import socket
import threading

HEADER = 128
BUFFER_SIZE = 4096
FORMAT = 'utf-8'
SEPARATOR = "<SEPARATOR>"

MASTER_ADDR = ('172.16.1.136',5555)
WORKER_ADDR = ('172.16.1.136',5050)

worker_server = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
worker_server.bind(WORKER_ADDR)
worker_server.listen()

worker_client = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
worker_client.connect(MASTER_ADDR)
