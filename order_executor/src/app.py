import logging
import time
import threading
import socket

import grpc_gen.order_queue_pb2 as order_queue
import grpc_gen.order_queue_pb2_grpc as order_queue_grpc
import grpc_gen.order_executor_pb2 as order_executor
import grpc_gen.order_executor_pb2_grpc as order_executor_grpc

import grpc

from concurrent import futures

HOSTNAME = socket.gethostname()
COMMON_HOSTNAME = HOSTNAME[:-1]
PROC_ID = int(HOSTNAME[-1])
NUM_REPLICAS = 3

class OrderExecutorService(order_executor_grpc.OrderExecutorServiceServicer):

    def __init__(self) -> None:
        logging.debug(f"Hostname: {HOSTNAME}")
        self.is_leader = PROC_ID == 1
        logging.debug(f"Is leader: {self.is_leader}")
        self.last_heartbeat_timestamp = time.time()
        logging.info(f"Initialized with process_id: {PROC_ID}")
    
    def Election(self, request: order_executor.RunElectionRequest, context):
        logging.debug(f"Received election message from process {request.process_id}")
        threading.Thread(target=self.run_election()).start()
        return order_executor.Empty()
    
    def HeartBeat(self, request: order_executor.HeartBeatRequest, context):
        logging.debug(f"Received hearbeat")
        self.last_heartbeat_timestamp = time.time()
        self.is_leader = False
        return order_executor.Empty()
    
    def attempt_execution(self):
        while True:
            time.sleep(5)
            self.execute_next()
    
    def execute_next(self):
        if not self.is_leader:
            return
        
        logging.info("Attempting to dequeue order")
        with grpc.insecure_channel('order_queue:50054') as channel:
            stub = order_queue_grpc.OrderQueueServiceStub(channel)
            response: order_queue.DequeueResponse = \
                stub.Dequeue(order_queue.DequeueRequest())

        if not response.order_id.value:
            logging.info(f"Nothing was queued")
            return
        
        logging.info(f"Executing order: {response.order_id}")
        logging.debug(f"Order data: {response.order_data}")

    def check_state(self):
        while True:
            time.sleep(10)
            if self.is_leader:
                self.send_heartbeat()
            elif time.time() - self.last_heartbeat_timestamp > 30:
                self.run_election()
            else:
                logging.debug("Nothing to do in election check")

    def send_heartbeat(self):
        logging.debug(f"Broadcasting heartbeat")
        for target_id in range(1, NUM_REPLICAS+1):
            if target_id == PROC_ID:
                continue
            target_svc = f'{COMMON_HOSTNAME}{target_id}:50055'
            logging.debug(f"Sending heartbeat to {target_svc}")
            try:
                with grpc.insecure_channel(target_svc) as channel:
                    stub = order_executor_grpc.OrderExecutorServiceStub(channel)
                    stub.HeartBeat(order_executor.HeartBeatRequest(process_id=PROC_ID))
            except Exception:
                logging.error(f"Received error from {target_svc}")

    def run_election(self):
        logging.debug(f"Running election")
        takeover = False
        for target_id in range(PROC_ID-1, 0, -1):
            target_svc = f'{COMMON_HOSTNAME}{target_id}:50055'
            logging.debug(f"Targeting service {target_svc}")
            try:
                with grpc.insecure_channel(target_svc) as channel:
                    stub = order_executor_grpc.OrderExecutorServiceStub(channel)
                    stub.Election(order_executor.RunElectionRequest(process_id=PROC_ID))
                takeover = True
                break
            except Exception as e:
                logging.error(f"Received error from {target_svc}", exc_info=e)
        if not takeover:
            logging.info("No response from targets, becoming leader")
            self.is_leader = True
            self.send_heartbeat()

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
    election_checker_thread = threading.Thread(target=order_executor_service.check_state)
    election_checker_thread.start()
    server.wait_for_termination()

if __name__ == '__main__':
    serve()