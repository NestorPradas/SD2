import sys, os

sys.path.append(os.path.dirname(os.path.abspath(__file__)) + '/../proto')

import grpc
import store_pb2 as store_pb2
import store_pb2_grpc as store_pb2_grpc
from concurrent import futures
import random
import time

class NodeKeyValueStoreServicer(store_pb2_grpc.KeyValueStoreServicer):
    def __init__(self, ip, port, node0_host, weight, node0_weight):
        self.data = {}
        self.temp = {}
        self.nodes = {}
        self.ip = ip
        self.port = port
        self.was_slowed = False
        self.weight = weight
        self.min_weight_for_commit = 0
        self.timeout = 0.1
        self.delay = 0

        ## ¿Crear archivo de recuperacion por nodo?
        ## ¿Leer archivo de recuperacion de datos?

        try:
            if f"{ip}:{port}" != node0_host: 
                channel = grpc.insecure_channel(f'{node0_host}')
                stub = store_pb2_grpc.KeyValueStoreStub(channel)
                response = stub.register(store_pb2.RegisterRequest(ip=self.ip, port=self.port, weight=self.weight), timeout=self.timeout)
                self.nodes[node0_host] = (stub, node0_weight)
                if response.success == False:
                    print(f"[NODE-{self.port}] Faliled to conect to {node0_host}, success :", response.success)
                    #stub.unregister(store_pb2.UnregisterRequest(ip=self.ip, port=self.port))
                    exit()
                else:
                    print(f"[NODE-{self.port}] Registered at {node0_host}, weight {node0_weight}")

                node_num = 0
                response_addcon = stub.addcon(store_pb2.AddConRequest(num=node_num), timeout=self.timeout)
                while response_addcon.node != '':
                    if response_addcon.node != f'{self.ip}:{self.port}':
                        node_channel = grpc.insecure_channel(f'{response_addcon.node}')
                        node_stub = store_pb2_grpc.KeyValueStoreStub(node_channel)
                        node_response = node_stub.register(store_pb2.RegisterRequest(ip=self.ip, port=self.port, weight=self.weight), timeout=self.timeout)
                        if node_response.success == False:
                            print(f"[NODE-{self.port}] Faliled to conect to {response_addcon.node}")
                            #stub.unregister(store_pb2.UnregisterRequest(ip=self.ip, port=self.port))
                        else:
                            self.nodes[response_addcon.node] = (node_stub, response_addcon.weight)
                            print(f"[NODE-{self.port}] Registered to {response_addcon.node}, weight {response_addcon.weight}")
                    node_num += 1
                    response_addcon = stub.addcon(store_pb2.AddConRequest(num=node_num), timeout=self.timeout)
                    
        except Exception as e:
            print(f"[NODE-{self.port}] Faliled to conect")
            print(f"[NODE-{self.port}]", e)
            exit()

        super().__init__()

    def put(self, request, context):
        try:
            print(f"[NODE-{self.port}] preparing to put '{request.key}' : '{request.value}'")
            key = request.key
            value = request.value
            
            prepare_responses = self.weight
            commit_responses = self.weight
            commit_nodes = []
            abort = False

            self.temp[key] = value

            for adress, stub in self.nodes.items():
                try:
                    prepare_request = store_pb2.PrepareRequest(key=key, value=value)
                    prepare_response = stub[0].prepare(prepare_request, timeout=self.timeout)
                    if prepare_response.success:
                        prepare_responses += stub[1]
                except Exception:
                    pass
            if prepare_responses >= self.min_weight_for_commit:
                commit_request = store_pb2.CommitRequest(key=key)
                print(f"[NODE-{self.port}] Committing...")
                for stub in self.nodes.values():
                    try:
                        commit_response = stub[0].commit(commit_request, timeout=self.timeout)
                        if commit_response.success:
                            commit_responses += stub[1]
                            commit_nodes.append(stub[0])
                    except Exception:
                        pass
                if commit_responses >= self.min_weight_for_commit:
                    self.data[key] = value
                    ## ¿Escribir archivo de recuperacion de datos?
                else:
                    abort = True
            else:
                abort = True

            if abort:
                abort_request = store_pb2.AbortRequest(key=key)
                print(f"[NODE-{self.port}] Aborting prepare...")
                for stub in self.nodes.values():
                    stub[0].abort(abort_request, timeout=self.timeout)
                print(f"[NODE-{self.port}] Put failed")
                return store_pb2.PutResponse(success=False)
            else:
                print(f"[NODE-{self.port}] Put success")
                return store_pb2.PutResponse(success=True)
            
        except Exception as e:
            print(f"[NODE-{self.port}] Faliled to conect")
            print(f"[NODE-{self.port}]", e)
            return store_pb2.PutResponse(success=False)

    def prepare(self, request, context):
        try:
            if request.key != '':
                print(f"[NODE-{self.port}] Preparing to commit '{request.key}' : '{request.value}'")
                self.temp[request.key] = request.value
                return store_pb2.PrepareResponse(success=True)
            else:
                print(f"[NODE-{self.port}] No key provided")
                return store_pb2.PrepareResponse(success=False)
            
        except Exception as e:
            print(f"[NODE-{self.port}] Failed to prepare commit '{request.key}' : '{request.value}'")
            print(f"[NODE-{self.port}]", e)
            return store_pb2.PrepareResponse(success=False)
        
    def commit(self, request, context):
        try:
            if request.key != '':
                print(f"[NODE-{self.port}] Commiting key : {request.key}")
                self.data[request.key] = self.temp[request.key]
                return store_pb2.CommitResponse(success=True)
            else:
                print(f"[NODE-{self.port}] Can't commit, no key provided")
                return store_pb2.CommitResponse(success=False)
            
        except Exception as e:
            print(f"[NODE-{self.port}] Failed to commit key : {request.key}")
            print(f"[NODE-{self.port}]", e)
            return store_pb2.CommitResponse(success=False)

    def abort(self, request, context):
        try:
            if request.key != '':
                print(f"[NODE-{self.port}] Aborting key : {request.key}")
                del self.temp[request.key]
                return store_pb2.AbortResponse(success=True)
            else:
                print(f"[NODE-{self.port}] Can't abort, no key provided")
                return store_pb2.AbortResponse(success=False)
            
        except Exception as e:
            print(f"[NODE-{self.port}] Failed to abort key : {request.key}")
            print(f"[NODE-{self.port}]", e)
            return store_pb2.AbortResponse(success=False)

    def get(self, request, context):
        try: 
            if request.key != '':
                ## Modificar
                # se piden los valores a todos los nodos vecinos
                # todos los que respondan se crea un array como en relacion valor-weight de todas los posibles valores
                # se devuelve el que mayor peso tenga
                
                if request.key in self.data:
                    print(f"[NODE-{self.port}] Getting key '{request.key}'")
                    return store_pb2.GetResponse(found=True, value=self.data[request.key])
                else:
                    found = False
                    node = 0
                    print(f"[NODE-{self.port}] Can't get key '{request.key}'")
                    
                    while not found:
                        if (len(list(self.nodes.keys()))) > node:
                            if context.peer() != list(self.nodes.keys())[node]:
                                print(f"[NODE-{self.port}] Redirecting to {list(self.nodes.keys())[node]}")
                                try:
                                    node_con = list(self.nodes.keys())[node]
                                    response = self.nodes[node_con][0].get(store_pb2.GetRequest(key=request.key), timeout=self.timeout)
                                    return response
                                except Exception:
                                    print(f"[NODE-{self.port}] Failed to get key '{request.key}' from {list(self.nodes.keys())[node]}")
                                    node += 1
                        else:
                            return store_pb2.GetResponse(found=False)
                        
                    print(f"[NODE-{self.port}] Key : {request.key} not found")
                    return store_pb2.GetResponse(found=False)
            else:
                print(f"[NODE-{self.port}] Cant get, no key provided")
                return store_pb2.GetResponse(found=False)
            
        except Exception as e:
            print(f"[NODE-{self.port}] Failed to get key : '{request.key}'")
            print(f"[NODE-{self.port}]", e)
            return store_pb2.GetResponse(found=False)
    
    def slowDown(self, request, context):
        try:
            print(f"[NODE-{self.port}] Slowing down for {request.seconds} seconds")
            self.delay = request.seconds
            self.was_slowed = True
            while self.delay > 0:
                time.sleep(1)
                self.delay -= 1
            print(f"[NODE-{self.port}] SlowDown terminated")
            return store_pb2.SlowDownResponse(success=True)
        except Exception as e:
                print(f"[SLAVE-{self.port}] Failed to slow down")
                print(f"[SLAVE-{self.port}]", e)
                return store_pb2.SlowDownResponse(success=False)

    def restore(self, request, context):
        try:
            if self.was_slowed:
                print(f"[NODE-{self.port}] Restoring data")
                self.delay = 0
                self.was_slowed = False
                return store_pb2.RestoreResponse(success=True)
            else:
                print(f"[NODE-{self.port}] Was not slowed")
                return store_pb2.RestoreResponse(success=False)
        except Exception as e:
            print(f"[NODE-{self.port}] Failed to restore data")
            print(f"[NODE-{self.port}]", e)
            return store_pb2.RestoreResponse(success=False)

    def register(self, request, context):
        try:
            if f"{request.ip}:{request.port}" not in self.nodes:
                print(f"[NODE-{self.port}] Registering node {request.ip}:{request.port}, weight: {request.weight}")
                channel = grpc.insecure_channel(f"{request.ip}:{request.port}")
                self.nodes[f"{request.ip}:{request.port}"] = (store_pb2_grpc.KeyValueStoreStub(channel), request.weight)
            
                self.min_weight_for_commit = int(sum(value[1] for value in self.nodes.values()) * 0.6)
            
            return store_pb2.RegisterResponse(success=True)
        except Exception as e:
            print(f"[NODE-{self.port}] Error connecting to node {request.ip}:{request.port}")
            print(f"[NODE-{self.port}]",e)
            return store_pb2.RegisterResponse(success=False)

    def addcon(self, request, context):
        if (len(list(self.nodes.keys()))) > request.num:
            node = list(self.nodes.keys())[request.num]
            return store_pb2.AddConResponse(node=node, weight=self.nodes[node][1])
        else:
            return store_pb2.AddConResponse(node='', weight=0)
        
    def unregister(self, request, context):
        try:
            print(f"[NODE-{self.port}] Unregistering node {request.ip}:{request.port}")
            del self.nodes[f"{request.ip}:{request.port}"]

        except Exception as e:
            print(f"[NODE-{self.port}] Error unregistering node {request.ip}:{request.port}")
            print(f"[NODE-{self.port}]",e)
            return store_pb2.RegisterResponse(success=False)
    
def serve(ip, port, master, weight, master_weight):
    print(f"[NODE-{port}] Serve at {ip}:{port}")
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=2))
    store_pb2_grpc.add_KeyValueStoreServicer_to_server(NodeKeyValueStoreServicer(ip, port, master, weight, master_weight), server)
    server.add_insecure_port(f'{ip}:{port}')
    server.start()
    server.wait_for_termination()

if __name__ == '__main__':
    serve("localhost", 32771, "localhost:32770", 1, 1)
