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


    results = await asyncio.gather(orchestrator_service.detect_fraud(data['creditCard'],
                                                           data['billingAddress']),
                         orchestrator_service.verify_transaction(data['creditCard'],
                                                                 data['billingAddress'],
                                                                 data['items']),
                         orchestrator_service.get_suggestions(data['items']))
    
    order_id = 12345
    status = OrderStatus.ACCEPTED
    suggested_books = [{'bookId': book.book_id, 'title': book.title, 'author': book.author}\
                        for book in results[2]]

    if not results[0] or not results[1]:
        status = OrderStatus.REJECTED
        suggested_books = []

    return {
        'orderId': str(order_id),
        'status': status.value,
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
