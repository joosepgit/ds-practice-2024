import logging
import asyncio
import grpc

import grpc_gen.fraud_detection_pb2 as fraud_detection
import grpc_gen.fraud_detection_pb2_grpc as fraud_detection_grpc
import grpc_gen.suggestions_pb2 as suggestions
import grpc_gen.suggestions_pb2_grpc as suggestions_grpc
import grpc_gen.transaction_verification_pb2 as transaction_verification
import grpc_gen.transaction_verification_pb2_grpc as transaction_verification_grpc

from exception.validation_error import FraudDetectionError
from exception.validation_error import TransactionVerificationError
from exception.validation_error import CheckoutError
from exception.validation_error import SuggestionsError


async def init_fraud_detection(order_id, credit_card, billing_address) -> None:
    logging.info(f'Initializing fraud detection with credit card: {credit_card}\
                   and billing address: {billing_address}')
    
    order_id_proto = fraud_detection.OrderUUID()
    order_id_proto.value = order_id
    
    credit_card_grpc_proto = fraud_detection.CreditCard()
    credit_card_grpc_proto.card_number = credit_card['number']
    credit_card_grpc_proto.expiration_date = credit_card['expirationDate']
    credit_card_grpc_proto.cvv = credit_card['cvv']

    billing_address_grpc_proto = fraud_detection.BillingAddress()
    billing_address_grpc_proto.country = billing_address['country']
    billing_address_grpc_proto.state = billing_address['state']
    billing_address_grpc_proto.city = billing_address['city']
    billing_address_grpc_proto.street = billing_address['street']
    billing_address_grpc_proto.zip = billing_address['zip']

    with grpc.insecure_channel('fraud_detection:50051') as channel:
        stub = fraud_detection_grpc.FraudDetectionServiceStub(channel)
        response: fraud_detection.InitializationResponse = \
            stub.Initialize(fraud_detection.InitializationRequest(
                order_id=order_id_proto,
                card_information=credit_card_grpc_proto,
                billing_address=billing_address_grpc_proto))
    
    if not response.success:
        await clear_data(order_id, None)
        raise FraudDetectionError(response.additional_info)
    
    logging.info(f'Fraud detection initialized successfully')
    logging.info(f'Additional information: {response.additional_info}')

async def init_transaction_verification(order_id, credit_card, billing_address, items) -> None:
    logging.info(f"Initializing transaction verification with: {credit_card};\
                   billing address: {billing_address};\
                   items: {items}")
    
    order_id_proto = transaction_verification.OrderUUID()
    order_id_proto.value = order_id

    credit_card_grpc_proto = transaction_verification.CreditCard()
    credit_card_grpc_proto.card_number = credit_card['number']
    credit_card_grpc_proto.expiration_date = credit_card['expirationDate']
    credit_card_grpc_proto.cvv = credit_card['cvv']

    billing_address_grpc_proto = transaction_verification.BillingAddress()
    billing_address_grpc_proto.country = billing_address['country']
    billing_address_grpc_proto.state = billing_address['state']
    billing_address_grpc_proto.city = billing_address['city']
    billing_address_grpc_proto.street = billing_address['street']
    billing_address_grpc_proto.zip = billing_address['zip']

    items_grpc_proto = transaction_verification.Items()
    for item in items:
        items_grpc_proto.items.append(
            transaction_verification.Item(name=item['name'], quantity=item['quantity']))

    with grpc.insecure_channel('transaction_verification:50052') as channel:
        stub = transaction_verification_grpc.TransactionVerificationServiceStub(channel)
        response: transaction_verification.InitializationResponse = \
            stub.Initialize(transaction_verification.InitializationRequest(
                order_id=order_id_proto,
                card_information=credit_card_grpc_proto,
                billing_address=billing_address_grpc_proto,
                items=items_grpc_proto))
    
    if not response.success:
        await clear_data(order_id, None)
        raise TransactionVerificationError(response.additional_info)
    
    logging.info(f'Transaction verification initialized successfully')
    logging.info(f'Additional information: {response.additional_info}')

async def init_suggestions(order_id, books):
    logging.info(f"Initializing book suggestions based on {books}")

    order_id_proto = suggestions.OrderUUID()
    order_id_proto.value = order_id

    with grpc.insecure_channel('suggestions:50053') as channel:
        stub = suggestions_grpc.SuggestionServiceStub(channel)
        response: suggestions.InitializationResponse = \
            stub.Initialize(suggestions.InitializationRequest(
                order_id=order_id_proto,
                title=books[0]['name']))
        
    if not response.success:
        await clear_data(order_id, None)
        raise SuggestionsError(response.additional_info)
        
    logging.info(f"Suggestions initialized successfully")
    
async def checkout(order_id: str) -> None:

    order_id_proto = transaction_verification.OrderUUID()
    order_id_proto.value = order_id

    vector_clock_proto = transaction_verification.VectorClock()

    with grpc.insecure_channel('transaction_verification:50052') as channel:
        stub = transaction_verification_grpc.TransactionVerificationServiceStub(channel)
        response: transaction_verification.TransactionVerificationResponse = \
            stub.VerifyTransaction(transaction_verification.TransactionVerificationRequest(
                order_id=order_id_proto,
                vector_clock=vector_clock_proto))
        
    if not response.success:
        await clear_data(order_id, None)
        raise CheckoutError(response.additional_info)
    
    logging.info(f"Successfully checked out order {order_id}")
    return dict(response.vector_clock.clocks)

async def get_suggestions(order_id: str, post_success_vector_clock: dict):
    logging.info(f"Getting book suggestions for successful order {order_id}")

    order_id_proto = suggestions.OrderUUID()
    order_id_proto.value = order_id

    post_success_vector_clock_proto = suggestions.VectorClock()
    post_success_vector_clock_proto.clocks.update(post_success_vector_clock)

    with grpc.insecure_channel('suggestions:50053') as channel:
        stub = suggestions_grpc.SuggestionServiceStub(channel)
        response: suggestions.GetSuggestionsResponse = \
            stub.GetSuggestions(suggestions.GetSuggestionsRequest(
                order_id=order_id_proto,
                vector_clock=post_success_vector_clock_proto))
        
    if not response.success:
        await clear_data(order_id, None)
        raise SuggestionsError(response.additional_info)
    
    suggested_books = list(map(
        lambda book: {'bookId': book.book_id, 'title': book.title, 'author': book.author},
        response.suggested_books)
    )
    
    logging.info(f"Successfully fetched suggestions {response.suggested_books}")
    return suggested_books, dict(response.vector_clock.clocks)

async def clear_data(order_id: str, final_vector_clock: dict):
    logging.info(f"Clearing all data for order {order_id}")
    await asyncio.gather(clear_transaction_verification_data(order_id, final_vector_clock),
                   clear_fraud_detection_data(order_id, final_vector_clock),
                   clear_suggestions_data(order_id, final_vector_clock))
    logging.info(f"Successfully cleared all data for order {order_id}")

async def clear_transaction_verification_data(order_id: str, final_vector_clock: dict):
    logging.info(f"Clearing order {order_id} data from transaction verification")

    transaction_verification_order_id_proto = transaction_verification.OrderUUID()
    transaction_verification_order_id_proto.value = order_id

    transaction_verification_final_vector_clock_proto = transaction_verification.VectorClock()
    if final_vector_clock:
        transaction_verification_final_vector_clock_proto.clocks.update(final_vector_clock)

    with grpc.insecure_channel('transaction_verification:50052') as channel:
        stub = transaction_verification_grpc.TransactionVerificationServiceStub(channel)
        stub.ClearData(transaction_verification.ClearDataRequest(
                order_id=transaction_verification_order_id_proto,
                vector_clock=transaction_verification_final_vector_clock_proto))
        
async def clear_fraud_detection_data(order_id: str, final_vector_clock: dict):
    logging.info(f"Clearing order {order_id} data from fraud detection")
        
    fraud_order_id_proto = fraud_detection.OrderUUID()
    fraud_order_id_proto.value = order_id

    fraud_final_vector_clock_proto = fraud_detection.VectorClock()
    if final_vector_clock:
        fraud_final_vector_clock_proto.clocks.update(final_vector_clock)

    with grpc.insecure_channel('fraud_detection:50051') as channel:
        stub = fraud_detection_grpc.FraudDetectionServiceStub(channel)
        stub.ClearData(fraud_detection.ClearDataRequest(
                order_id=fraud_order_id_proto,
                vector_clock=fraud_final_vector_clock_proto))
        
async def clear_suggestions_data(order_id: str, final_vector_clock: dict):
    logging.info(f"Clearing order {order_id} data from suggestions")
        
    suggestions_order_id_proto = suggestions.OrderUUID()
    suggestions_order_id_proto.value = order_id

    suggestions_final_vector_clock_proto = suggestions.VectorClock()
    if final_vector_clock:
        suggestions_final_vector_clock_proto.clocks.update(final_vector_clock)

    with grpc.insecure_channel('suggestions:50053') as channel:
        stub = suggestions_grpc.SuggestionServiceStub(channel)
        stub.ClearData(suggestions.ClearDataRequest(
                order_id=suggestions_order_id_proto,
                vector_clock=suggestions_final_vector_clock_proto))
