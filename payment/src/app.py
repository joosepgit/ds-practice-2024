import logging

import grpc_gen.payment_pb2 as payment
import grpc_gen.payment_pb2_grpc as payment_grpc

import grpc

from concurrent import futures


class PaymentService(payment_grpc.PaymentServiceServicer):

    def DoPayment(self, request, context):
        return super().DoPayment(request, context)


def serve():
    logging.basicConfig(
        format="%(asctime)s | %(levelname)s | %(processName)s| %(message)s",
        level=logging.DEBUG,
    )
    server = grpc.server(futures.ThreadPoolExecutor())
    payment_grpc.add_PaymentServiceServicer_to_server(PaymentService(), server)
    port = "50057"
    server.add_insecure_port("[::]:" + port)
    server.start()
    print("Server started. Listening on port 50057.")
    server.wait_for_termination()


if __name__ == "__main__":
    serve()
