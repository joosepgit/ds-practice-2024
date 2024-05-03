import logging
import time
import threading
import socket

import grpc_gen.db_pb2 as dbnode
import grpc_gen.db_pb2_grpc as dbnode_grpc
import grpc

from concurrent import futures

HOSTNAME = socket.gethostname()
COMMON_HOSTNAME = HOSTNAME[:-1]
PROC_ID = int(HOSTNAME[-1])
NUM_REPLICAS = 3


class DbnodeService(dbnode_grpc.DbnodeServiceServicer):

    def __init__(self) -> None:
        logging.debug(f"Hostname: {HOSTNAME}")
        self.is_leader = PROC_ID == 1
        logging.debug(f"Is leader: {self.is_leader}")
        self.last_heartbeat_timestamp = time.time()
        logging.info(f"Initialized with process_id: {PROC_ID}")

    # Just performs the query, no consensus mechanisms needed
    def GetDocument(self, request: dbnode.GetDocumentRequest, context):
        response = dbnode.DocumentResponse()
        # TODO: Query db
        return response

    # Forwards database operations to the next node in the chain until a node with the maximum
    # process id or a node that does not receive a response from the following nodes
    def UpdateDocument(self, request: dbnode.UpdateDocumentRequest, context):
        anyresponse = False
        for target_id in range(PROC_ID - 1, 0, -1):
            target_svc = f"{COMMON_HOSTNAME}{target_id}:50056"
            logging.debug(f"Targeting service {target_svc}")
            try:
                with grpc.insecure_channel(target_svc) as channel:
                    stub = dbnode_grpc.DbnodeServiceStub(channel)
                    response = stub.UpdateDocument(request)
                break
            # Silently skip intermediary failed nodes
            except Exception as e:
                logging.error(f"Received error from {target_svc}", exc_info=e)

        if not anyresponse:
            logging.info(f"Last healthy node in the db cluster: {HOSTNAME}")

        # TODO: Update db
        return dbnode.Empty()

    def Election(self, request: dbnode.RunElectionRequest, context):
        logging.debug(f"Received election message from process {request.process_id}")
        threading.Thread(target=self.run_election()).start()
        return dbnode.Empty()

    def HeartBeat(self, request: dbnode.HeartBeatRequest, context):
        logging.debug(f"Received hearbeat")
        self.last_heartbeat_timestamp = time.time()
        self.is_leader = False
        return dbnode.Empty()

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
        for target_id in range(1, NUM_REPLICAS + 1):
            if target_id == PROC_ID:
                continue
            target_svc = f"{COMMON_HOSTNAME}{target_id}:50056"
            logging.debug(f"Sending heartbeat to {target_svc}")
            try:
                with grpc.insecure_channel(target_svc) as channel:
                    stub = dbnode_grpc.DbnodeServiceStub(channel)
                    stub.HeartBeat(dbnode.HeartBeatRequest(process_id=PROC_ID))
            except Exception:
                logging.error(f"Received error from {target_svc}")

        # Also send heartbeat to the order executor service, so it knows who the current leader is
        for repl in range(1, 4):
            target_svc = f"orderexecutor{repl}:50055"
            try:
                with grpc.insecure_channel(target_svc) as channel:
                    stub = dbnode_grpc.DbnodeServiceStub(channel)
                    stub.HeartBeat(dbnode.HeartBeatRequest(process_id=PROC_ID))
            except Exception:
                logging.error(f"Received error from {target_svc}")

    def run_election(self):
        logging.debug(f"Running election")
        takeover = False
        for target_id in range(PROC_ID - 1, 0, -1):
            target_svc = f"{COMMON_HOSTNAME}{target_id}:50056"
            logging.debug(f"Targeting service {target_svc}")
            try:
                with grpc.insecure_channel(target_svc) as channel:
                    stub = dbnode_grpc.DbnodeServiceStub(channel)
                    stub.Election(dbnode.RunElectionRequest(process_id=PROC_ID))
                takeover = True
                break
            except Exception as e:
                logging.error(f"Received error from {target_svc}", exc_info=e)
        if not takeover:
            logging.info("No response from targets, becoming leader")
            self.is_leader = True
            self.send_heartbeat()


def serve():
    logging.basicConfig(
        format="%(asctime)s | %(levelname)s | %(processName)s| %(message)s",
        level=logging.DEBUG,
    )
    server = grpc.server(futures.ThreadPoolExecutor())
    dbnode_service = DbnodeService()
    dbnode_grpc.add_DbnodeServiceServicer_to_server(dbnode_service, server)
    port = "50056"
    server.add_insecure_port("[::]:" + port)
    server.start()
    print("Server started. Listening on port 50056.")
    election_checker_thread = threading.Thread(target=dbnode_service.check_state)
    election_checker_thread.start()
    server.wait_for_termination()


if __name__ == "__main__":
    serve()
