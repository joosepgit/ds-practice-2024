import logging
import heapq
import os
import time
import threading
import socket

import grpc_gen.order_queue_pb2 as order_queue
import grpc_gen.order_queue_pb2_grpc as order_queue_grpc
import grpc_gen.order_executor_pb2 as order_executor
import grpc_gen.order_executor_pb2_grpc as order_executor_grpc

import grpc

from concurrent import futures

import docker

class OrderExecutorService(order_executor_grpc.OrderExecutorServiceServicer):

    def __init__(self) -> None:
        self.process_id = int(socket.gethostname()[-1])
        self.is_leader = False
        self.last_heartbeat_timestamp = time.time()
        logging.debug(f"Socket hostname: {socket.gethostname()}")
        logging.info(f"Initialized with process_id: {self.process_id}")
    
    def Election(self, request: order_executor.RunElectionRequest, context):
        self.is_leader = True
        logging.info("Elected as leader")
        return order_executor.Empty()
    
    def HeartBeat(self, request: order_executor.HeartBeatRequest, context):
        logging.debug(f"Received hearbeat")
        self.is_leader = self.process_id == request.process_id
        self.last_heartbeat_timestamp = time.time()
        return order_executor.Empty()
    
    def execute_next(self):
        if not self.is_leader:
            logging.debug("Current executor instance is not the leader, can't execute order")
            return
        
        logging.info("Attempting to dequeue order")
        with grpc.insecure_channel('order_queue:50054') as channel:
            stub = order_queue_grpc.OrderQueueServiceStub(channel)
            response: order_queue.DequeueResponse = \
                stub.Dequeue(order_queue.DequeueRequest())

        logging.info(f"Executing order: {response.order_id}")
        logging.debug(f"Order data: {response.order_data}")
    
    def attempt_execution(self):
        while True:
            self.execute_next()
            time.sleep(5)

    def check_election(self):
        while True:
            if self.is_leader:
                client = docker.from_env()
                containers = client.containers.list(filters={"name": "order_executor"})
                logging.debug(f"Containers: containers")
                for container in containers:
                    logging.debug(f"Attempting to send heartbeat to {container.name}")
                    with grpc.insecure_channel(f'{container.name}:50055') as channel:
                        stub = order_executor_grpc.OrderExecutorServiceStub(channel)
                        stub.HeartBeat(order_executor.HeartBeatRequest(process_id=self.process_id))
            elif time.time() - self.last_heartbeat_timestamp > 30:
                next_svc = f'ds-practice-2024-order_executor-{self.process_id + 1}:50055'
                logging.debug(f"Attempting to run election, targeting service {next_svc}")
                with grpc.insecure_channel(next_svc) as channel:
                    stub = order_executor_grpc.OrderExecutorServiceStub(channel)
                    stub.Election(order_executor.RunElectionRequest(process_id=self.process_id))
            else:
                logging.debug("Nothing to do in election check")
            time.sleep(10)
                

def serve():
    logging.basicConfig(format="%(asctime)s | %(levelname)s | %(processName)s| %(message)s", level=logging.DEBUG)
    server = grpc.server(futures.ThreadPoolExecutor())
    order_executor_service = OrderExecutorService()
    order_executor_grpc.add_OrderExecutorServiceServicer_to_server(order_executor_service, server)
    port = "50055"
    server.add_insecure_port("[::]:" + port)
    server.start()
    print("Server started. Listening on port 50055.")
    execution_scheduler_thread = threading.Thread(target=order_executor_service.attempt_execution)
    execution_scheduler_thread.start()
    election_checker_thread = threading.Thread(target=order_executor_service.check_election)
    election_checker_thread.start()
    server.wait_for_termination()

if __name__ == '__main__':
    serve()