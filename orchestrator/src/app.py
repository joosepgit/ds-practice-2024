import logging
import asyncio
import uuid
import json

import service.orchestrator_service as orchestrator_service

from exception.validation_error import FraudDetectionError
from exception.validation_error import TransactionVerificationError

from enum import Enum

from flask import Flask, request, Response
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

class OrderStatus(Enum):
    ACCEPTED = 'Order Accepted'
    REJECTED = 'Order Rejected'

@app.route('/checkout', methods=['POST'])
async def checkout():
    """
    Responds with a JSON object containing the order ID, status, and suggested books.
    """

    data = request.json
    logging.debug(f"Request Data: {data}")

    order_id = str(uuid.uuid4())
    logging.info(f"Initializing order {order_id} checkout")
    
    # Initialize all services with necessary data, results in caching data and freshly
    # initialized vector clock with order uuid as key.
    await asyncio.gather(
        orchestrator_service.init_fraud_detection(
            order_id,
            data['creditCard'],
            data['billingAddress']),
        orchestrator_service.init_transaction_verification(
            order_id,
            data['creditCard'],
            data['billingAddress'],
            data['items']),
        orchestrator_service.init_suggestions(
            order_id,
            data['items']))
    
    logging.info(f"Checking out order {order_id}")
    
    # Call transaction verification service to begin checkout, the following calls are
    # made from transaction verification service if it succeeds, any failure is
    # immediately propagated back to this call. Returns most recent vector clock.
    post_success_vector_clock = await orchestrator_service.checkout(order_id)
    
    # Fetches the generated suggestions from suggestions service cache based on order 
    # id and updates suggestions service vector clock. Returns final vector clock
    suggested_books, final_vector_clock = await orchestrator_service.get_suggestions(
        order_id, post_success_vector_clock)

    # Broadcasts a message to all services with the final vector clock, indicating
    # to clear all data related to the current order by order id
    await orchestrator_service.clear_data(order_id, final_vector_clock)

    return {
        'orderId': str(order_id),
        'status': OrderStatus.ACCEPTED.value,
        'suggestedBooks': suggested_books
    }

@app.errorhandler(FraudDetectionError)
def fraud_detection_error(e: FraudDetectionError):
    id = str(uuid.uuid4())
    logging.error(f'Fraud detection failed {id}', e)
    res = {"error": 
        {id: str(e)}
    }
    return Response(status=e.status_code, mimetype="application/json", response=json.dumps(res))

@app.errorhandler(TransactionVerificationError)
def fraud_detection_error(e: TransactionVerificationError):
    id = str(uuid.uuid4())
    logging.error(f'Transaction verification failed {id}', e)
    res = {"error": 
        {id: str(e)}
    }
    return Response(status=e.status_code, mimetype="application/json", response=json.dumps(res))

@app.errorhandler(Exception)
def general_exception(e: Exception):
    id = str(uuid.uuid4())
    logging.error(f'Internal error {id}', e)
    res = {"error": 
        {id: str(e)}
    }
    return Response(status=500, mimetype="application/json", response=json.dumps(res))

if __name__ == '__main__':
    logging.basicConfig(format="%(asctime)s | %(levelname)s | %(processName)s| %(message)s", level=logging.INFO)
    # Run the app in debug mode to enable hot reloading.
    # This is useful for development.
    # The default port is 5000.
    app.run(host='0.0.0.0')
