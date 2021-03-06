#!/usr/bin/python
import socket
import hashlib
import argparse
import sys
import os


configs = {
"buffer_size" : 1024,
"client_id" : hashlib.sha1("192.168.1.1"+"12345").digest(),
"root_ip" : "10.10.123.6",
"root_port" : 16500,
"port":12345,
"ip" :""
}

# converts an IP address to bytes.
def ip_addr_to_bytes(ip_addr):
    if ip_addr:
        return bytearray([int(i) for i in ip_addr.split('.')])
    return bytearray([0]*4)

# converts IP address from bytes to a string
def bytes_to_ip_addr(data):
    if any(data):
        return ".".join([str(i) for i in data])
    return None

# converts a SHA1 hash string to bytes
def hash_to_bytes(ip_hash):
    if ip_hash:
        return ip_hash
    return bytearray([0]*20)

#converts a SHA1 hash from bytes to string
def bytes_to_hash(data):
    if any(data):
        return bytes(data)
    return None

#converts "UPDATE" packets to bytes.
def gen_update_data(data,arr):
    arr += ip_addr_to_bytes(data['for'])
    arr += ip_addr_to_bytes(data['succ_ip'])
    arr += hash_to_bytes(data['succ_hash'])
    arr += port_to_bytes(data['succ_port'])
    arr += ip_addr_to_bytes(data['pre_ip'])
    arr += hash_to_bytes(data['pre_hash'])
    arr += port_to_bytes(data['pre_port'])
    return arr

# converts bytes to dictionary
def gen_update_dict(data):
    p = {}
    p["for"] = bytes_to_ip_addr(data[:4])
    p['succ_ip'] = bytes_to_ip_addr(data[4:8])
    p['succ_hash'] = bytes_to_hash(data[8:28])
    p['succ_port'] = bytes_to_port(data[28:30])
    p['pre_ip'] = bytes_to_ip_addr(data[30:34])
    p['pre_hash'] = bytes_to_hash(data[34:54])
    p['pre_port'] = bytes_to_port(data[54:56])
    return p

# converts port number to bytes
def port_to_bytes(port):
    if port :
        hex_num = hex(port).split('x')[1]
        return bytearray([int(hex_num[i]+hex_num[i+1]) for i in range(0,len(hex_num),2)])
    return bytearray([0]*2)

# converts bytes to port numbers
def bytes_to_port(data):
    if(all(data)):
        return int(str(int(data[0])) + str(int(data[1])),16)
    return None

# decodes a packet from bytes into dictionary
def decode_packet_bytes(data):

    types = {
    1 : "update",
    2 : "init",
    3 : "answer",
    4 : "query",
    5 : "join",
    6 : "dead",
    7 : "data"
    }
    operations = {
    1 : "put",
    2 : "lookup",
    3 : "response",
    4 : "redirect",
    5 : "close",
    6 : "get",
    7 : "move"
    }

    p = {}
    arr = bytearray(data)
    p['type'] = types[arr[0]]
    if p['type'] == "data":
        p['client_id'] = bytes_to_hash(arr[1:21])
        p['operation'] = operations[arr[21]]

        if p['operation'] == "put" or  p['operation'] == "move" :
            p['obj_name_len'] = arr[22]
            name_end = 23+arr[22]
            p['obj_name'] = str(arr[23:name_end])
            p['obj_key'] = bytes_to_hash(arr[name_end:name_end+20])
            p['obj_len'] = arr[name_end+20]
            p['obj'] = str(arr[name_end+21:name_end+21+p['obj_len']])


        elif p['operation'] == "lookup":
            p['method'] = 'R' if arr[22] == 1 else 'I'
            p['obj_key'] = bytes_to_hash(arr[23:43])

        elif p['operation'] == "redirect":
            p['ip'] = bytes_to_ip_addr(arr[22:26])
            p['port'] = bytes_to_port(arr[26:28])

        elif p['operation'] == "response":
            p['obj_name_len'] = arr[22]
            name_end = 23+arr[22]
            p['obj_name'] = str(arr[23:name_end])
            p['obj_key'] = bytes_to_hash(arr[name_end:name_end+20])
            p['obj_len'] = arr[name_end+20]
            p['obj'] = str(arr[name_end+21:name_end+21+p['obj_len']])

        elif p['operation'] == "get":
            p['obj_key'] = bytes_to_hash(arr[22:42])

    else:
        p['ip'] = bytes_to_ip_addr(arr[1:5])
        p['ip_hash'] = bytes_to_hash(arr[5:25])

        if p['type'] == "update":
            p['data'] = gen_update_dict(arr[25:])

        elif p['type'] == "init":
            p['data'] = 'pre_sock' if arr[25] == 1 else 'succ_sock'

        elif p['type'] == "answer":
            p['data'] = "succ" if arr[25] == 1 else "pre"

        elif p['type'] == "dead":
            p['data'] = bytes_to_hash(arr[25:45])
            p['port'] = bytes_to_port(arr[45:47])

        elif p['type'] == "query":
            p['data'] = "succ" if arr[25] == 1 else "pre"

        elif p['type'] == "join":
            p['port'] = bytes_to_port(arr[25:27])

    return p

# debug function to print hex value of a packet.
def print_hex(data):
    print "".join("%02x " % b for b in data)

#encodes a dictionary into bytes.
def encode_packet_bytes(packet):

    types = {
    "update" : 1,
    "init" : 2,
    "answer" : 3,
    "query" : 4,
    "join" : 5,
    "dead" : 6,
    "data": 7
    }

    operations = {
    "put": 1,
    "lookup" : 2,
    "response" : 3,
    "redirect" : 4,
    "close" : 5,
    "get" : 6,
    "move": 7
    }
    arr = bytearray()
    arr.append(types[packet['type']])
    if packet['type'] == "data":
        arr += hash_to_bytes(packet['client_id'])
        arr.append(operations[packet['operation']])

        if packet['operation'] == "put" or packet['operation'] == "move":
            arr.append(packet['obj_name_len'])
            arr += packet['obj_name']
            arr += hash_to_bytes(packet['obj_key'])
            arr.append(packet['obj_len'])
            arr += packet['obj']

        elif packet['operation'] == "lookup":
            arr.append(1 if packet['method'] == 'R' else 2)
            arr += hash_to_bytes(packet['obj_key'])

        elif packet['operation'] == "redirect":
            arr += ip_addr_to_bytes(packet['ip'])
            arr += port_to_bytes(packet['port'])

        elif packet['operation'] == "response":
            arr.append(packet['obj_name_len'])
            arr += packet['obj_name']
            arr += hash_to_bytes(packet['obj_key'])
            arr.append(packet['obj_len'])
            arr += packet['obj']

        elif packet['operation'] == "get":
            arr += hash_to_bytes(packet['obj_key'])


    else:
        arr += ip_addr_to_bytes(packet['ip'])
        arr += hash_to_bytes(packet['ip_hash'])

        if packet['type'] == "update":
            arr = gen_update_data(packet['data'],arr)

        elif packet['type'] == "init":
            arr.append(1 if packet['data'] == "pre_sock" else 2)

        elif packet['type'] == "answer":
            arr.append(1 if packet['data'] == "succ" else 2)

        elif packet['type'] == "dead":
            arr += hash_to_bytes(packet['data'])
            arr += port_to_bytes(packet['port'])

        elif packet['type'] == "query":
            arr.append(1 if packet['data'] == "succ" else 2)

        elif packet['type'] == "join":
            arr += port_to_bytes(packet['port'])

    return arr


def send_packet(conn,packet):
    payload = encode_packet_bytes(packet)
    payload_len = '{:04x}'.format(len(payload)).decode('hex')
    packet = bytearray(payload_len) + payload
    conn.send(packet)

def recv_packet(conn):
    global configs
    packet_len_byte = conn.recv(2)
    packet_len = int(str(packet_len_byte).encode('hex'),16)
    p = conn.recv(packet_len)
    return decode_packet_bytes(p)

def recursive_lookup(key):
    global configs

    s = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
    #s.bind((configs['ip'],configs['port']))
    #s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.connect((configs['root_ip'],configs['root_port']))

    print "connecting to ", configs['root_ip'], configs['root_port']


    p = {
    "type" : "data",
    "client_id": configs['client_id'],
    "operation" : "lookup",
    "obj_key" : key,
    "method" : "R"
    }

    send_packet(s,p)
    data = recv_packet(s)
    s.close()
    return (data['ip'],data['port'])

def iterative_lookup(key):
    global configs

    ip = configs['root_ip']
    port = configs['root_port']
    while True:
        s = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
        #s.bind((configs['ip'],configs['port']))
        #s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.connect((ip,port))
        print "connecting to ", ip, port

        p = {
        "type" : "data",
        "client_id": configs['client_id'],
        "operation" : "lookup",
        "obj_key" : key,
        "method" : "I"
        }
        send_packet(s,p)
        data = recv_packet(s)
        s.close()

        if data['ip'] == None and data['port'] == None:
            return (ip,port)

        ip = data['ip']
        port = data['port']

def retrieve_object(key, mode):
    global confgs
    print "="*50
    if mode == 'R' :
        goto = recursive_lookup(key)
    else:
        goto = iterative_lookup(key)
    s = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
    s.connect(goto)

    p = {
    "type" : "data",
    "client_id" : configs['client_id'],
    "operation" : "get",
    "obj_key" : key
    }

    send_packet(s,p)
    data = recv_packet(s)
    s.close()

    f_name = configs['client_id'].encode('hex')+"_"+data['obj_name']
    print "retrieving object from :"
    print "connecting to ",goto[0],goto[1]
    print "OBJECT : ",data['obj']
    print "writing object to file : ",f_name
    print "="*50
    with open(f_name,"w") as f:
        f.write(data['obj'])

def store_object(key, obj, name):
    print "="*50
    goto = recursive_lookup(key)
    s = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
    s.connect(goto)

    p = {
    "type" : "data",
    "client_id": configs['client_id'],
    "operation" : "put",
    "obj_name" : name,
    "obj_name_len" : len(name),
    "obj": obj,
    "obj_len" : len(obj),
    "obj_key" : key,
    }
    send_packet(s,p)
    data = recv_packet(s)
    s.close()

    if data['operation'] == "close":
        print "stored object at",goto[0],goto[1]
    else:
        print "stored operation failed at",goto[0],goto[1]

    print "="*50

def draw_menu():
    os.system('clear')

    print "="*50
    print "s. store object"
    print "i. retrieve object iterative"
    print "r. retrieve object recursive"
    print "e. exit"
    print "="*50

def gen_hash(i):
    return bytes(bytearray([0]*19) + bytearray('{:02x}'.format(int(i)).decode('hex')))

def store_this(i):
    obj = "this is object "+str(i)
    f_name = "obj_"+str(i)+".txt"
    store_object(gen_hash(i),obj,f_name)

def main():
    # store_this(5)
    # store_this(6)
    # store_this(7)
    # store_this(20)
    # store_this(27)
    # store_this(44)
    # store_this(12)
    # store_this(26)
    # store_this(30)

    retrieve_object(gen_hash(5),'R')
    retrieve_object(gen_hash(6),'R')
    retrieve_object(gen_hash(7),'R')
    retrieve_object(gen_hash(20),'R')
    retrieve_object(gen_hash(27),'R')
    retrieve_object(gen_hash(44),'R')
    retrieve_object(gen_hash(12),'R')
    retrieve_object(gen_hash(26),'R')
    retrieve_object(gen_hash(30),'R')



if __name__ == "__main__":
    main()
