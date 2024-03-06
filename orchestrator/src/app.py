import logging
import sys
import os
import asyncio

import grpc_gen.fraud_detection_pb2 as fraud_detection
import grpc_gen.fraud_detection_pb2_grpc as fraud_detection_grpc
import grpc_gen.suggestions_pb2 as suggestions
import grpc_gen.suggestions_pb2_grpc as suggestions_grpc
import grpc_gen.transaction_verification_pb2 as transaction_verification
import grpc_gen.transaction_verification_pb2_grpc as transaction_verification_grpc


import grpc


def check_for_fraud(name='you'):
    # Establish a connection with the fraud-detection gRPC service.
    with grpc.insecure_channel('fraud_detection:50051') as channel:
        # Create a stub object.
        stub = fraud_detection_grpc.FraudDetectionService(channel)
        # Call the service through the stub object.
        response = stub.DetectFraud(fraud_detection.FraudDetectionRequest(name=name))
    return response.success


def verify_transaction(id='0'):
    # Establish a connection with the fraud-detection gRPC service.
    with grpc.insecure_channel('fraud_detection:50052') as channel:
        # Create a stub object.
        stub = fraud_detection_grpc.TransactionVerificationService(channel)
        # Call the service through the stub object.
        response = stub.VerifyTransaction(fraud_detection.TransactionVerificationRequest(id=id))
    return response.success


def check_for_suggestions(name='you'):
    # Establish a connection with the fraud-detection gRPC service.
    with grpc.insecure_channel('fraud_detection:50053') as channel:
        # Create a stub object.
        stub = fraud_detection_grpc.SuggestionService(channel)
        # Call the service through the stub object.
        response = stub.GetSuggestions(fraud_detection.GetSuggestionsRequest(name=name))
    return response.suggestedBooks.title


# Import Flask.
# Flask is a web framework for Python.
# It allows you to build a web application quickly.
# For more information, see https://flask.palletsprojects.com/en/latest/
from flask import Flask, request
from flask_cors import CORS

# Create a simple Flask app.
app = Flask(__name__)
# Enable CORS for the app.
CORS(app)


# Define a GET endpoint.
@app.route('/', methods=['GET'])
def index():
    """
    Responds with 'Hello, [name]' when a GET request is made to '/' endpoint.
    """
    # Test the fraud-detection gRPC service.
    response = ""
    # Return the response.
    return response


@app.route('/checkout', methods=['POST'])
def checkout():
    """
    Responds with a JSON object containing the order ID, status, and suggested books.
    """

    async def fraud():
        logging.info(f"Checking for fraud for {request.json['name']}")
        is_fraud = check_for_fraud(request.json["name"])
        logging.info(f"Is fraudulent: {is_fraud}")

    async def transaction():
        logging.info(f"Verifying transaction {request.json['name']}")
        transaction_verified = verify_transaction(request.json["ID"])
        logging.info(f"Transaction verified: {transaction_verified}")

    async def suggestions():
        logging.info(f"Checking for book suggestions for {request.json['name']}")
        suggested_book = check_for_suggestions(request.json["name"])
        logging.info(f"Book {suggested_book} suggested for {request.json['name']}")

    # Print request object data
    logging.debug(f"Request Data: {request.json}")

    asyncio.gather(fraud(), transaction(), suggestions())

    # Dummy response following the provided YAML specification for the bookstore
    order_status_response = {
        'orderId': '12345',
        'status': 'Order Approved',
        'suggestedBooks': [
            {'bookId': '123', 'title': 'Dummy Book 1', 'author': 'Author 1'},
            {'bookId': '456', 'title': 'Dummy Book 2', 'author': 'Author 2'}
        ]
    }

    return order_status_response


if __name__ == '__main__':
    logging.basicConfig(format="%(asctime)s | %(levelname)s | %(processName)s| %(message)s", level=logging.INFO)
    # Run the app in debug mode to enable hot reloading.
    # This is useful for development.
    # The default port is 5000.
    app.run(host='0.0.0.0')
