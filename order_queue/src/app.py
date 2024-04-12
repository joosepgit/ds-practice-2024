import logging
import heapq

import grpc_gen.order_queue_pb2 as order_queue
import grpc_gen.order_queue_pb2_grpc as order_queue_grpc

import grpc

from concurrent import futures

class OrderQueueService(order_queue_grpc.OrderQueueServiceServicer):

    def __init__(self) -> None:
        # In-memory queue, for now
        self.order_queue = []

    def Enqueue(self, request: order_queue.EnqueueRequest, context):
        logging.info(f"Enqueueing order {request.order_id.value}")
        logging.debug(f"Order data: {request.order_data}")
        # Min heap priority queue, processes smaller orders first
        priority = len(request.order_data.items)
        heapq.heappush(self.order_queue, (priority, (request.order_id.value, request.order_data)))
        
        logging.info(f"Successfully queued order {request.order_id.value} with priority {priority}")
        return order_queue.EnqueueResponse()
    
    def Dequeue(self, request: order_queue.DequeueRequest, context):
        logging.info(f"Dequeueing order")

        response = order_queue.DequeueResponse()

        if not self.order_queue:
            logging.debug(f"No queued orders")
            return response
        
        popped: tuple[int, order_queue.OrderData] = heapq.heappop(self.order_queue)
        response.order_id.value, response.order_data = popped
        
        logging.info(f"Successfully dequeued order {response.order_id.value}")
        logging.debug(f"Dequeued order data: {response.order_data}")
        return response
    

def serve():
    logging.basicConfig(format="%(asctime)s | %(levelname)s | %(processName)s| %(message)s", level=logging.DEBUG)
    server = grpc.server(futures.ThreadPoolExecutor())
    order_queue_grpc.add_OrderQueueServiceServicer_to_server(OrderQueueService(), server)
    port = "50054"
    server.add_insecure_port("[::]:" + port)
    server.start()
    print("Server started. Listening on port 50054.")
    server.wait_for_termination()

if __name__ == '__main__':
    serve()