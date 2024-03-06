import sys
import os
import logging

import grpc_gen.fraud_detection_pb2 as fraud_detection
import grpc_gen.fraud_detection_pb2_grpc as fraud_detection_grpc

import grpc
from concurrent import futures


# Create a class to derive the server functions
class FraudDetectionService(fraud_detection_grpc.FraudDetectionServiceServicer):
    # Create an RPC function to say hello
    def DetectFraud(self, request, context):
        # Create a response object
        logging.info(f"Checking for fraud for {request.name}")
        response = fraud_detection.FraudDetectionResponse()
        response.success = True
        # Return the response object
        return response


def serve():
    # Create a gRPC server
    logging.basicConfig(format="%(asctime)s | %(levelname)s | %(processName)s| %(message)s", level=logging.INFO)
    logging.info("Starting the fraud detection server")
    server = grpc.server(futures.ThreadPoolExecutor())
    fraud_detection_grpc.add_FraudDetectionServiceServicer_to_server(FraudDetectionService(), server)
    # Listen on port 50051
    port = "50051"
    server.add_insecure_port("[::]:" + port)
    # Start the server
    server.start()
    logging.info(f"Server started. Listening on port {port}.")
    # Keep thread alive
    server.wait_for_termination()


if __name__ == '__main__':
    serve()
