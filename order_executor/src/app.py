import logging
import time
import threading
import socket
import json

import grpc_gen.db_pb2 as database
import grpc_gen.db_pb2_grpc as database_grpc
import grpc_gen.order_queue_pb2 as order_queue
import grpc_gen.order_queue_pb2_grpc as order_queue_grpc
import grpc_gen.order_executor_pb2 as order_executor
import grpc_gen.order_executor_pb2_grpc as order_executor_grpc

import grpc

from concurrent import futures

from cachetools import TTLCache

from opentelemetry.sdk.resources import SERVICE_NAME, Resource

from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

from opentelemetry import metrics
from opentelemetry.exporter.otlp.proto.http.metric_exporter import OTLPMetricExporter
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader

# Service name is required for most backends
resource = Resource(attributes={SERVICE_NAME: socket.gethostname()})

traceProvider = TracerProvider(resource=resource)
processor = BatchSpanProcessor(
    OTLPSpanExporter(endpoint="http://observability:4318/v1/metrics")
)
traceProvider.add_span_processor(processor)
trace.set_tracer_provider(traceProvider)

reader = PeriodicExportingMetricReader(
    OTLPMetricExporter(endpoint="http://observability:4318/v1/metrics")
)
meterProvider = MeterProvider(resource=resource, metric_readers=[reader])
metrics.set_meter_provider(meterProvider)


HOSTNAME = socket.gethostname()
COMMON_HOSTNAME = HOSTNAME[:-1]
PROC_ID = int(HOSTNAME[-1])
NUM_REPLICAS = 3

COMMON_DBNODE_NAME = "dbnode"
# Cache current db cluster leader for 60 seconds
LEADER_KEY = "LEADER"
leader_cache = TTLCache(maxsize=100, ttl=60)

COLLECTION_NAME = "books"


# Dummy interface that stands in front of the database cluster that implements chain replication internally
class DatabaseService(database_grpc.DbnodeServiceServicer):

    # Takes note of who is the leader by listening to the heartbeat at all times
    def HeartBeat(self, request: database.HeartBeatRequest, context):
        logging.debug(f"Received database heartbeat from dbnode{request.process_id}")
        leader_cache[LEADER_KEY] = request.process_id
        return database.Empty()

    # Forwards database operations to the current db cluster leader
    def GetDocument(self, request: database.GetDocumentRequest, context):
        target_svc = f"{COMMON_DBNODE_NAME}{leader_cache[LEADER_KEY]}:50056"
        logging.info(
            f"Attempting to get book {request.book_title} from service {target_svc}"
        )
        with grpc.insecure_channel(target_svc) as channel:
            stub = database_grpc.DbnodeServiceStub(channel)
            response = stub.GetDocument(request)
        return response

    # Forwards database operations to the current db cluster leader
    def UpdateDocument(self, request: database.UpdateDocumentRequest, context):
        target_svc = f"{COMMON_DBNODE_NAME}{leader_cache[LEADER_KEY]}:50056"
        logging.info(
            f"Attempting to update book {request.document} with service {target_svc}"
        )
        with grpc.insecure_channel(target_svc) as channel:
            stub = database_grpc.DbnodeServiceStub(channel)
            response = stub.UpdateDocument(request)
        return response


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
        logging.debug(
            f"Received executor hearbeat from orderexecutor{request.process_id}"
        )
        self.last_heartbeat_timestamp = time.time()
        self.is_leader = False
        return order_executor.Empty()

    def attempt_execution(self):
        while True:
            time.sleep(2)
            self.execute_next()

    def execute_next(self):
        if not self.is_leader:
            return

        logging.info("Attempting to dequeue order")
        try:
            with grpc.insecure_channel("orderqueue:50054") as channel:
                stub = order_queue_grpc.OrderQueueServiceStub(channel)
                dq_response: order_queue.DequeueResponse = stub.Dequeue(
                    order_queue.DequeueRequest()
                )
        except Exception as e:
            logging.error(f"Order queue is down or something went wrong", exc_info=e)
            return

        if not dq_response.order_id.value:
            logging.info(f"Nothing was queued")
            return

        logging.info(f"Executing order: {dq_response.order_id}")
        logging.debug(f"Order data: {dq_response.order_data}")

        self.update_stock(dq_response)

    def update_stock(self, dq_response: order_queue.DequeueResponse):
        for item in dq_response.order_data.items.items:
            try:
                target_svc = "[::]:50055"
                logging.info(
                    f"Attempting to get book {item.name} from service {target_svc}"
                )
                with grpc.insecure_channel(target_svc) as channel:
                    stub = database_grpc.DbnodeServiceStub(channel)
                    query_response: database.DocumentResponse = stub.GetDocument(
                        database.GetDocumentRequest(
                            collection_name=COLLECTION_NAME, book_title=item.name
                        )
                    )
            except Exception as e:
                logging.error(f"Leader is down or something went wrong", exc_info=e)
                return

            document = json.loads(query_response.document)
            updated_quantity = document["stock"] - item.quantity
            document["stock"] = updated_quantity

            try:
                target_svc = "[::]:50055"
                with grpc.insecure_channel(target_svc) as channel:
                    stub = database_grpc.DbnodeServiceStub(channel)
                    stub.UpdateDocument(
                        database.UpdateDocumentRequest(
                            document=json.dumps(document, default=str)
                        )
                    )
            except Exception as e:
                logging.error(f"Leader is down or something went wrong", exc_info=e)
                return

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
            target_svc = f"{COMMON_HOSTNAME}{target_id}:50055"
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
        for target_id in range(PROC_ID - 1, 0, -1):
            target_svc = f"{COMMON_HOSTNAME}{target_id}:50055"
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
    logging.basicConfig(
        format="%(asctime)s | %(levelname)s | %(processName)s| %(message)s",
        level=logging.DEBUG,
    )
    server = grpc.server(futures.ThreadPoolExecutor())
    order_executor_service = OrderExecutorService()
    order_executor_grpc.add_OrderExecutorServiceServicer_to_server(
        order_executor_service, server
    )
    database_service = DatabaseService()
    database_grpc.add_DbnodeServiceServicer_to_server(database_service, server)
    port = "50055"
    server.add_insecure_port("[::]:" + port)
    server.start()
    print("Server started. Listening on port 50055.")
    execution_scheduler_thread = threading.Thread(
        target=order_executor_service.attempt_execution
    )
    execution_scheduler_thread.start()
    election_checker_thread = threading.Thread(
        target=order_executor_service.check_state
    )
    election_checker_thread.start()
    server.wait_for_termination()


if __name__ == "__main__":
    serve()
