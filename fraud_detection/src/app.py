import grpc
import logging

import grpc_gen.fraud_detection_pb2 as fraud_detection
import grpc_gen.fraud_detection_pb2_grpc as fraud_detection_grpc

from concurrent import futures


class FraudDetectionService(fraud_detection_grpc.FraudDetectionServiceServicer):
    def DetectFraud(self, request: fraud_detection.FraudDetectionRequest, context):
        logging.info(f"Checking for fraud for {request}")
        response = fraud_detection.FraudDetectionResponse()
        
        logging.info(f'Attempting to detect fraud')
        if request.card_information.cvv == '000':
            response.success = False
            response.additional_info = 'Suspicious CVV code, potentially fradulent transaction!'
            return response
        if request.billing_address.country == 'Finland':
            response.success = False
            response.additional_info = 'Finland can not be trusted, potentially fradulent transaction!'
            return response
        
        response.success = True
        response.additional_info = ''
        logging.info(f'Did not detect fraud, response {response}')
        return response


def serve():
    logging.basicConfig(format="%(asctime)s | %(levelname)s | %(processName)s | %(message)s", level=logging.INFO)
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
