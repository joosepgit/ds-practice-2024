import logging

import grpc_gen.transaction_verification_pb2 as transaction_verification
import grpc_gen.transaction_verification_pb2_grpc as transaction_verification_grpc

import grpc

from concurrent import futures
from datetime import datetime

class TransactionVerificationService(transaction_verification_grpc.TransactionVerificationServiceServicer):
    def VerifyTransaction(self, request: transaction_verification.TransactionVerificationRequest, context):
        logging.info(f"Verifying transaction data: {request}")
        response = transaction_verification.TransactionVerificationResponse()

        logging.info(f'Validating credit card information')
        credit_card_success, credit_card_msg = self.validate_credit_card(request.card_information)
        if not credit_card_success:
            response.success = False
            response.additional_info = credit_card_msg
            return response
    
        logging.info(f'Validating billing address')
        billing_address_success, billing_address_msg = self.validate_billing_address(request.billing_address)
        if not billing_address_success:
            response.success = False
            response.additional_info = billing_address_msg
            return response
        
        logging.info(f'Validating cart contents')
        cart_success, cart_msg = self.validate_cart(request.items)
        if not cart_success:
            response.success = False
            response.additional_info = cart_msg
            return response
        
        response.success = True
        response.additional_info = f'{credit_card_msg}; {billing_address_msg}'
        logging.info(f'Successfully verified transaction, response {response}')
        return response
    
    def validate_billing_address(self, billing_address: transaction_verification.BillingAddress):
        # Address information
        if not billing_address.country:
            return False, "Country can not be empty or blank."
        if not billing_address.state:
            return False, "State can not be empty or blank."
        if not billing_address.city:
            return False, "City can not be empty or blank."
        if not billing_address.street:
            return False, "Street can not be empty or blank."
        
        # ZIP code
        if not billing_address.zip.isnumeric():
            return False, "ZIP code should be numeric."
        if len(billing_address.zip) != 5:
            return False, "ZIP code should contain exactly 5 numbers."

        return True, ""
    
    def validate_credit_card(self, credit_card: transaction_verification.CreditCard):
        # CVV
        if not credit_card.cvv.isnumeric():
            return False, "CVV should be numeric."
        if len(credit_card.cvv) != 3:
            return False, "CVV should contain exactly 3 numbers."

        # Expiration date
        try: 
            expiration_date = datetime.strptime(credit_card.expiration_date, '%m/%y')
        except ValueError:
            return False, "Invalid input format for expiration date. Please use YY/MM."
        if datetime.now() > expiration_date:
            return False, "Card is expired."
        
        # Card number
        if not credit_card.card_number.isnumeric():
            return False, "Card number should be numeric."
        if len(credit_card.card_number) < 8 or len(credit_card.card_number) > 19:
            return False, "Card number should contain at least 8 and at most 19 numbers."
        
        return True, ""
    
    def validate_cart(self, cart: transaction_verification.Items):
        if len(cart.items) == 0:
            return False, "Cart can not be empty."
        return True, ""

def serve():
    logging.basicConfig(format="%(asctime)s | %(levelname)s | %(processName)s| %(message)s", level=logging.INFO)
    server = grpc.server(futures.ThreadPoolExecutor())
    transaction_verification_grpc.add_TransactionVerificationServiceServicer_to_server(TransactionVerificationService(), server)
    port = "50052"
    server.add_insecure_port("[::]:" + port)
    server.start()
    print("Server started. Listening on port 50052.")
    server.wait_for_termination()

if __name__ == '__main__':
    serve()