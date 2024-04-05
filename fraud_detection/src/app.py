import grpc
import logging

import grpc_gen.fraud_detection_pb2 as fraud_detection
import grpc_gen.fraud_detection_pb2_grpc as fraud_detection_grpc

from concurrent import futures

from cachetools import TTLCache

SERVICE_IDENTIFIER = "FRAUD_DETECTION"

vector_clock_cache = TTLCache(maxsize=100, ttl=60)

class FraudDetectionService(fraud_detection_grpc.FraudDetectionServiceServicer):
    def Initialize(self, request: fraud_detection.InitializationRequest, context):
        logging.info("Initializing fraud detection")

        response = fraud_detection.InitializationResponse()

        vector_clock = {SERVICE_IDENTIFIER : 0}
        vector_clock_cache[request.order_id.value] = [vector_clock, request]

        response.success = True
        response.additional_info = ""
        logging.info(f"Successfully initialized fraud detection with vector clock: {vector_clock} \
                      and data: {request}")
        return response


    def DetectFraud(self, request: fraud_detection.FraudDetectionRequest, context):
        logging.info(f"Checking for fraud for {request}")

        self.update_vector_clock(request.order_id.value, dict(request.vector_clock.clocks))
        
        response = fraud_detection.FraudDetectionResponse()

        cached_data: tuple[dict, fraud_detection.InitializationRequest] = vector_clock_cache[request.order_id.value]
        vector_clock, data = cached_data
        
        logging.info(f'Attempting to detect fraud in credit card data')
        if data.card_information.cvv == '000':
            response.success = False
            response.additional_info = 'Suspicious CVV code, potentially fradulent transaction!'
            return response
        
        vector_clock[SERVICE_IDENTIFIER] += 1
        vector_clock = self.update_vector_clock(request.order_id.value, vector_clock)

        logging.info(f'Attempting to detect fraud in billing address data')
        if data.billing_address.country == 'Finland':
            response.success = False
            response.additional_info = 'Finland can not be trusted, potentially fradulent transaction!'
            return response
        
        vector_clock[SERVICE_IDENTIFIER] += 1
        vector_clock = self.update_vector_clock(request.order_id.value, vector_clock)

        response.vector_clock.clocks.update(vector_clock_cache[request.order_id.value][0])
        
        response.success = True
        response.additional_info = 'OK'
        logging.info(f'Did not detect fraud, response {response}')
        return response
    
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


def serve():
    logging.basicConfig(format="%(asctime)s | %(levelname)s | %(processName)s| %(message)s", level=logging.INFO)
    logging.info("Starting the fraud detection server")
    server = grpc.server(futures.ThreadPoolExecutor())
    fraud_detection_grpc.add_FraudDetectionServiceServicer_to_server(FraudDetectionService(), server)
    port = "50051"
    server.add_insecure_port("[::]:" + port)
    server.start()
    logging.info(f"Server started. Listening on port {port}.")
    server.wait_for_termination()


if __name__ == '__main__':
    serve()
