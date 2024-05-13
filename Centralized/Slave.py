import sys, os

sys.path.append(os.path.dirname(os.path.abspath(__file__)) + '/../proto')

import grpc
import store_pb2 as store_pb2
import store_pb2_grpc as store_pb2_grpc
from concurrent import futures
import random
import time

class SlaveKeyValueStoreServicer(store_pb2_grpc.KeyValueStoreServicer):
    def __init__(self, ip, port, master):
        self.data = {}
        self.temp = {}
        self.ip = ip
        self.port = port
        self.was_slowed = False
        self.delay = 0

        try:
            channel = grpc.insecure_channel(f'{master}')
            self.stub = store_pb2_grpc.KeyValueStoreStub(channel)
            response = self.stub.register(store_pb2.RegisterRequest(ip=self.ip, port=self.port))
            if response.success == False:
                print(f"[SLAVE-{self.port}] Faliled to conect to MASTER, success :", response.success)
                self.stub.unregister(store_pb2.UnregisterRequest(ip=self.ip, port=self.port))
                exit()
            else:
                print(f"[SLAVE-{self.port}] Registered at MASTER")
                
        except Exception as e:
            print(f"[SLAVE-{self.port}] Faliled to conect to MASTER")
            print(f"[SLAVE-{self.port}]", e)
            exit()
        super().__init__()
    
    def prepare(self, request, context):
        try:
            if request.key != '':
                print(f"[SLAVE-{self.port}] Preparing to commit '{request.key}' : '{request.value}'")
                self.temp[request.key] = request.value
                return store_pb2.PrepareResponse(success=True)
            else:
                print(f"[SLAVE-{self.port}] No key provided")
                return store_pb2.PrepareResponse(success=False)
            
        except Exception as e:
            print(f"[SLAVE-{self.port}] Failed to prepare commit '{request.key}' : '{request.value}'")
            print(f"[SLAVE-{self.port}]", e)
            return store_pb2.PrepareResponse(success=False)
        
    def commit(self, request, context):
        try:
            if request.key != '':
                print(f"[SLAVE-{self.port}] Commiting key : {request.key}")
                self.data[request.key] = self.temp[request.key]
                return store_pb2.CommitResponse(success=True)
            else:
                print(f"[SLAVE-{self.port}] Can't commit, no key provided")
                return store_pb2.CommitResponse(success=False)
            
        except Exception as e:
            print(f"[SLAVE-{self.port}] Failed to commit key : {request.key}")
            print(f"[SLAVE-{self.port}]", e)
            return store_pb2.CommitResponse(success=False)

    def abort(self, request, context):
        try:
            if request.key != '':
                print(f"[SLAVE-{self.port}] Aborting key : {request.key}")
                del self.temp[request.key]
                return store_pb2.AbortResponse(success=True)
            else:
                print(f"[SLAVE-{self.port}] Can't abort, no key provided")
                return store_pb2.AbortResponse(success=False)
            
        except Exception as e:
            print(f"[SLAVE-{self.port}] Failed to abort key : {request.key}")
            print(f"[SLAVE-{self.port}]", e)
            return store_pb2.AbortResponse(success=False)

    def get(self, request, context):
        try: 
            if request.key != '':
                if request.key in self.data:
                    print(f"[SLAVE-{self.port}] Getting key : {request.key}")
                    return store_pb2.GetResponse(found=True, value=self.data[request.key])
                else:
                    print(f"[SLAVE-{self.port}] Key : {request.key} not found")
                    return store_pb2.GetResponse(found=False)
            else:
                print(f"[SLAVE-{self.port}] Cant get, no key provided")
                return store_pb2.GetResponse(found=False)
            
        except Exception as e:
            print(f"[SLAVE-{self.port}] Failed to get key : '{request.key}'")
            print(f"[SLAVE-{self.port}]", e)
            return store_pb2.GetResponse(found=False)
    
    def slowDown(self, request, context):
        try:
            print(f"[SLAVE-{self.port}] Slowing down for {request.seconds} seconds")
            self.delay = request.seconds
            self.was_slowed = True
            while self.delay > 0:
                time.sleep(1)
                self.delay -= 1
            print(f"[SLAVE-{self.port}] SlowDown terminated")
            return store_pb2.SlowDownResponse(success=True)
        
        except Exception as e:
            print(f"[SLAVE-{self.port}] Failed to slow down")
            print(f"[SLAVE-{self.port}]", e)
            return store_pb2.SlowDownResponse(success=False)

    def restore(self, request, context):
        try:
            if self.was_slowed:
                print(f"[SLAVE-{self.port}] Restoring data")
                self.delay = 0
                return store_pb2.RestoreResponse(success=True)
            else:
                print(f"[SLAVE-{self.port}] Was not slowed")
                return store_pb2.RestoreResponse(success=False)
        except Exception as e:
            print(f"[SLAVE-{self.port}] Failed to restore data")
            print(f"[SLAVE-{self.port}]", e)
            return store_pb2.RestoreResponse(success=False)

def serve(ip, port, master):
    print(f"[SLAVE-{port}] Serve at {ip}:{port}")
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=1))
    store_pb2_grpc.add_KeyValueStoreServicer_to_server(SlaveKeyValueStoreServicer(ip, port, master), server)
    server.add_insecure_port(f'{ip}:{port}')
    server.start()
    server.wait_for_termination()

if __name__ == '__main__':
    serve("localhost", 50052)
