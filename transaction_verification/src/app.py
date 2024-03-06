import sys
import os
import logging

import grpc_gen.transaction_verification_pb2 as transaction_verification
import grpc_gen.transaction_verification_pb2_grpc as transaction_verification_grpc

import grpc
from concurrent import futures

# Create a class to derive the server functions
class TransactionVerificationService(transaction_verification_grpc.TransactionVerificationServiceServicer):
    # Create an RPC function to say hello
    def DetectFraud(self, request, context):
        # Create a response object
        response = transaction_verification.TransactionVerificationResponse()
        response.success = True
        # Return the response object
        return response

def serve():
    # Create a gRPC server
    server = grpc.server(futures.ThreadPoolExecutor())
    transaction_verification_grpc.add_TransactionVerificationServiceServicer_to_server(TransactionVerificationService, server)
    # Listen on port 50051
    port = "50052"
    server.add_insecure_port("[::]:" + port)
    # Start the server
    server.start()
    print("Server started. Listening on port 50052.")
    # Keep thread alive
    server.wait_for_termination()

if __name__ == '__main__':
    serve()