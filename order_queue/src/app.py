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
        priority = len(request.order_data.items.items)
        heapq.heappush(
            self.order_queue, (priority, (request.order_id.value, request.order_data))
        )

        logging.info(
            f"Successfully queued order {request.order_id.value} with priority {priority}"
        )
        return order_queue.EnqueueResponse()

    def Dequeue(self, request: order_queue.DequeueRequest, context):
        logging.info(f"Dequeueing order")

        response = order_queue.DequeueResponse()

        if not self.order_queue:
            logging.debug(f"No queued orders")
            return response

        popped: tuple[int, order_queue.OrderData] = heapq.heappop(self.order_queue)
        logging.debug(f"Got order from queue: {popped}")
        _, (response.order_id.value, data) = popped

        data: order_queue.OrderData = data

        response.order_data.user.user_name = data.user.user_name
        response.order_data.user.user_contact = data.user.user_contact

        response.order_data.credit_card.card_number = data.credit_card.card_number
        response.order_data.credit_card.expiration_date = (
            data.credit_card.expiration_date
        )
        response.order_data.credit_card.cvv = data.credit_card.cvv

        response.order_data.user_comment = data.user_comment

        for item in data.items.items:
            item: order_queue.Item = item
            response.order_data.items.items.append(
                order_queue.Item(name=item.name, quantity=item.quantity)
            )

        response.order_data.discount_code = data.discount_code
        response.order_data.shipping_method = data.shipping_method
        response.order_data.gift_message = data.gift_message

        response.order_data.billing_address.country = data.billing_address.country
        response.order_data.billing_address.state = data.billing_address.state
        response.order_data.billing_address.city = data.billing_address.city
        response.order_data.billing_address.street = data.billing_address.street
        response.order_data.billing_address.zip = data.billing_address.zip

        response.order_data.gift_wrapping = data.gift_wrapping

        response.order_data.terms_accepted = data.terms_accepted

        for preference in data.notification_preference.preferences:
            response.order_data.notification_preference.preferences.append(preference)

        logging.info(f"Successfully dequeued order {response.order_id.value}")
        logging.debug(f"Dequeued order data: {response.order_data}")
        return response


def serve():
    logging.basicConfig(
        format="%(asctime)s | %(levelname)s | %(processName)s| %(message)s",
        level=logging.DEBUG,
    )
    server = grpc.server(futures.ThreadPoolExecutor())
    order_queue_grpc.add_OrderQueueServiceServicer_to_server(
        OrderQueueService(), server
    )
    port = "50054"
    server.add_insecure_port("[::]:" + port)
    server.start()
    print("Server started. Listening on port 50054.")
    server.wait_for_termination()


if __name__ == "__main__":
    serve()
