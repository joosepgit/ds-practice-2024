import logging

import grpc_gen.fraud_detection_pb2 as fraud_detection
import grpc_gen.fraud_detection_pb2_grpc as fraud_detection_grpc
import grpc_gen.transaction_verification_pb2 as transaction_verification
import grpc_gen.transaction_verification_pb2_grpc as transaction_verification_grpc

import grpc

from concurrent import futures
from datetime import datetime

from cachetools import TTLCache

SERVICE_IDENTIFIER = "TRANSACTION_VERIFICATION"

vector_clock_cache = TTLCache(maxsize=100, ttl=60)

class TransactionVerificationService(transaction_verification_grpc.TransactionVerificationServiceServicer):

    def Initialize(self, request: transaction_verification.InitializationRequest, context):
        logging.info("Initializing transaction verification")

        response = transaction_verification.InitializationResponse()

        vector_clock = {SERVICE_IDENTIFIER : 0}
        vector_clock_cache[request.order_id.value] = [vector_clock, request]

        response.success = True
        response.additional_info = ""
        logging.info(f"Successfully initialized transaction verification with vector clock: {vector_clock} \
                      and data: {request}")
        return response

    def VerifyTransaction(self, request: transaction_verification.TransactionVerificationRequest, context):
        logging.info(f"Verifying transaction data: {request}")

        self.update_vector_clock(request.order_id.value, dict(request.vector_clock.clocks))

        response = transaction_verification.TransactionVerificationResponse()

        cached_data: tuple[dict, transaction_verification.InitializationRequest] = vector_clock_cache[request.order_id.value]
        vector_clock, data = cached_data

        logging.info(f'Validating cart contents')
        cart_success, cart_msg = self.validate_cart(data.items)
        if not cart_success:
            response.success = False
            response.additional_info = cart_msg
            return response
        
        vector_clock[SERVICE_IDENTIFIER] += 1
        vector_clock = self.update_vector_clock(request.order_id.value, vector_clock)

        logging.info(f'Validating billing address')
        billing_address_success, billing_address_msg = self.validate_billing_address(data.billing_address)
        if not billing_address_success:
            response.success = False
            response.additional_info = billing_address_msg
            return response
        
        vector_clock[SERVICE_IDENTIFIER] += 1
        vector_clock = self.update_vector_clock(request.order_id.value, vector_clock)

        logging.info(f'Validating credit card information')
        credit_card_success, credit_card_msg = self.validate_credit_card(data.card_information)
        if not credit_card_success:
            response.success = False
            response.additional_info = credit_card_msg
            return response
        
        vector_clock[SERVICE_IDENTIFIER] += 1
        vector_clock = self.update_vector_clock(request.order_id.value, vector_clock)

        fraud_detection_response: fraud_detection.FraudDetectionResponse = self.detect_fraud(request.order_id.value, vector_clock)

        # Increment self after sending a message to fraud detection
        vector_clock[SERVICE_IDENTIFIER] += 1
        vector_clock = self.update_vector_clock(request.order_id.value, vector_clock)

        # Update based on fraud detection response
        vector_clock = self.update_vector_clock(request.order_id.value, dict(fraud_detection_response.vector_clock.clocks))
        
        response.vector_clock.clocks.update(vector_clock_cache[request.order_id.value][0])
        
        response.success = fraud_detection_response.success
        response.additional_info = f'\nResult:\n\
            Transaction Verification:\n\
            \tCart: {cart_msg};\n\
            \tCredit card: {credit_card_msg};\n\
            \tBilling address: {billing_address_msg};\n\
            {fraud_detection_response.additional_info}'
        logging.info(f'Successfully verified transaction, response {response}')
        return response
    
    def ClearData(self, request: transaction_verification.ClearDataRequest, context):
        logging.info(f"Clearing data for request {request}")
        curr_vector_clock: dict = vector_clock_cache[request.order_id.value][0]
        passed_vector_clock = dict(request.vector_clock.clocks)
        for k, _ in curr_vector_clock.items():
            if curr_vector_clock[k] > passed_vector_clock[k]:
                raise ValueError(f"Final vector clock has a smaller value  than local vector clock for service {k}")
            
        logging.debug(f"Current vector clock: {curr_vector_clock}")
        logging.debug(f"Passed vector clock: {passed_vector_clock}")
        del vector_clock_cache[request.order_id.value]
        return transaction_verification.ClearDataResponse()
    
    def update_vector_clock(self, order_id: int, vector_clock_in: dict):
        logging.info("Updating vector clock")
        vector_clock_curr = vector_clock_cache[order_id][0]
        for k in vector_clock_in.keys():
            if k not in vector_clock_curr.keys():
                vector_clock_curr[k] = vector_clock_in[k]
            vector_clock_curr[k] = max(vector_clock_curr[k], vector_clock_in[k])
        
        vector_clock_cache[order_id][0] = vector_clock_curr
        logging.info(f"Successfully updated vector clock: {vector_clock_curr}")
        return vector_clock_cache[order_id][0]
    
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

        return True, "OK"
    
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
        
        return True, "OK"
    
    def validate_cart(self, cart: transaction_verification.Items):
        if len(cart.items) == 0:
            return False, "Cart can not be empty."
        return True, "OK"
    
    def detect_fraud(self, order_id: str, vector_clock: dict):

        order_id_proto = fraud_detection.OrderUUID()
        order_id_proto.value = order_id

        vector_clock_proto = fraud_detection.VectorClock()
        vector_clock_proto.clocks.update(vector_clock)

        with grpc.insecure_channel('fraud_detection:50051') as channel:
            stub = fraud_detection_grpc.FraudDetectionServiceStub(channel)
            response: fraud_detection.FraudDetectionResponse = \
                stub.DetectFraud(fraud_detection.FraudDetectionRequest(
                    order_id=order_id_proto,
                    vector_clock=vector_clock_proto))
            
        return response

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