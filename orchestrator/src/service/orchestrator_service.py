import logging
import grpc

import grpc_gen.fraud_detection_pb2 as fraud_detection
import grpc_gen.fraud_detection_pb2_grpc as fraud_detection_grpc
import grpc_gen.suggestions_pb2 as suggestions
import grpc_gen.suggestions_pb2_grpc as suggestions_grpc
import grpc_gen.transaction_verification_pb2 as transaction_verification
import grpc_gen.transaction_verification_pb2_grpc as transaction_verification_grpc

from exception.validation_error import FraudDetectionError
from exception.validation_error import TransactionVerificationError


async def detect_fraud(credit_card, billing_address) -> bool:
    logging.info(f'Checking for fraud with credit card: {credit_card}\
                   and billing address: {billing_address}')
    
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
        response: fraud_detection.FraudDetectionResponse = \
            stub.DetectFraud(fraud_detection.FraudDetectionRequest(
                card_information=credit_card_grpc_proto,
                billing_address=billing_address_grpc_proto))
    
    if not response.success:
        raise FraudDetectionError(response.additional_info)
    
    logging.info(f'Fraud detection successfully validated checkout')
    logging.info(f'Additional information: {response.additional_info}')
    return response.success

async def verify_transaction(credit_card, billing_address, items) -> bool:
    logging.info(f"Verifying transaction with: {credit_card};\
                   billing address: {billing_address};\
                   items: {items}")

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
        response: transaction_verification.TransactionVerificationResponse = \
            stub.VerifyTransaction(transaction_verification.TransactionVerificationRequest(
                card_information=credit_card_grpc_proto,
                billing_address=billing_address_grpc_proto,
                items=items_grpc_proto))
    
    if not response.success:
        raise TransactionVerificationError(response.additional_info)
    
    logging.info(f'Transaction verification succeeded')
    logging.info(f'Additional information: {response.additional_info}')
    return response.success

async def get_suggestions(books):
    logging.info(f"Fetching for book suggestions based on {books}")
    with grpc.insecure_channel('suggestions:50053') as channel:
        stub = suggestions_grpc.SuggestionServiceStub(channel)
        response: suggestions.GetSuggestionsResponse = \
            stub.GetSuggestions(suggestions.GetSuggestionsRequest(
                title=books[0]['name']))
    logging.info(f"Fetched suggestion: {response.suggestedBooks}")
    return response.suggestedBooks