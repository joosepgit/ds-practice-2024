import grpc
import logging

import grpc_gen.suggestions_pb2 as suggestions
import grpc_gen.suggestions_pb2_grpc as suggestions_grpc
import grpc_gen.fraud_detection_pb2 as fraud_detection
import grpc_gen.fraud_detection_pb2_grpc as fraud_detection_grpc

from concurrent import futures

from cachetools import TTLCache

SERVICE_IDENTIFIER = "FRAUD_DETECTION"

from opentelemetry.sdk.resources import SERVICE_NAME, Resource

from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

from opentelemetry import metrics
from opentelemetry.exporter.otlp.proto.http.metric_exporter import OTLPMetricExporter
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader

# Service name is required for most backends
resource = Resource(attributes={SERVICE_NAME: SERVICE_IDENTIFIER.lower()})

traceProvider = TracerProvider(resource=resource)
processor = BatchSpanProcessor(
    OTLPSpanExporter(endpoint="http://observability:4318/v1/metrics")
)
traceProvider.add_span_processor(processor)
trace.set_tracer_provider(traceProvider)

reader = PeriodicExportingMetricReader(
    OTLPMetricExporter(endpoint="http://observability:4318/v1/metrics")
)
meterProvider = MeterProvider(resource=resource, metric_readers=[reader])
metrics.set_meter_provider(meterProvider)


vector_clock_cache = TTLCache(maxsize=100, ttl=60)


class FraudDetectionService(fraud_detection_grpc.FraudDetectionServiceServicer):
    def Initialize(self, request: fraud_detection.InitializationRequest, context):
        logging.info("Initializing fraud detection")

        response = fraud_detection.InitializationResponse()

        vector_clock = {SERVICE_IDENTIFIER: 0}
        vector_clock_cache[request.order_id.value] = [vector_clock, request]

        response.success = True
        response.additional_info = "OK"
        logging.info(
            f"Successfully initialized fraud detection with vector clock: {vector_clock} \
                      and data: {request}"
        )
        return response

    def DetectFraud(self, request: fraud_detection.FraudDetectionRequest, context):
        logging.info(f"Checking for fraud for {request}")

        self.update_vector_clock(
            request.order_id.value, dict(request.vector_clock.clocks)
        )

        response = fraud_detection.FraudDetectionResponse()

        cached_data: tuple[dict, fraud_detection.InitializationRequest] = (
            vector_clock_cache[request.order_id.value]
        )
        vector_clock, data = cached_data

        logging.info(f"Attempting to detect fraud in credit card data")
        if data.card_information.cvv == "000":
            response.success = False
            response.additional_info = (
                "Suspicious CVV code, potentially fradulent transaction!"
            )
            return response

        vector_clock[SERVICE_IDENTIFIER] += 1
        vector_clock = self.update_vector_clock(request.order_id.value, vector_clock)

        logging.info(f"Attempting to detect fraud in billing address data")
        if data.billing_address.country == "Finland":
            response.success = False
            response.additional_info = (
                "Finland can not be trusted, potentially fradulent transaction!"
            )
            return response

        vector_clock[SERVICE_IDENTIFIER] += 1
        vector_clock = self.update_vector_clock(request.order_id.value, vector_clock)

        suggestions_response: suggestions.GenerateSuggestionsResponse = (
            self.generate_suggestions(request.order_id.value, vector_clock)
        )

        # Increment self after sending a message to suggestions
        vector_clock[SERVICE_IDENTIFIER] += 1
        vector_clock = self.update_vector_clock(request.order_id.value, vector_clock)

        # Update based on suggestions response
        vector_clock = self.update_vector_clock(
            request.order_id.value, dict(suggestions_response.vector_clock.clocks)
        )

        response.vector_clock.clocks.update(
            vector_clock_cache[request.order_id.value][0]
        )

        response.success = suggestions_response.success
        response.additional_info = f"Fraud detection:\n\
            \tOK;\n\
            {suggestions_response.additional_info}"
        logging.info(f"Did not detect fraud, response {response}")
        return response

    def ClearData(self, request: fraud_detection.ClearDataRequest, context):
        logging.info(f"Clearing data for request {request}")
        curr_vector_clock: dict = vector_clock_cache[request.order_id.value][0]
        passed_vector_clock = dict(request.vector_clock.clocks)

        # Only verify if a vector clock was actually passed, otherwise assume initialization
        # failure and simply clear all data
        if passed_vector_clock:
            for k, _ in curr_vector_clock.items():
                if curr_vector_clock[k] > passed_vector_clock[k]:
                    raise ValueError(
                        f"Final vector clock has a smaller value than local vector clock for service {k}"
                    )

        logging.debug(f"Current vector clock: {curr_vector_clock}")
        logging.debug(f"Passed vector clock: {passed_vector_clock}")
        del vector_clock_cache[request.order_id.value]
        return fraud_detection.ClearDataResponse()

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

    def generate_suggestions(self, order_id: str, vector_clock: dict):

        order_id_proto = suggestions.OrderUUID()
        order_id_proto.value = order_id

        vector_clock_proto = suggestions.VectorClock()
        vector_clock_proto.clocks.update(vector_clock)

        with grpc.insecure_channel("suggestions:50053") as channel:
            stub = suggestions_grpc.SuggestionServiceStub(channel)
            response: suggestions.GenerateSuggestionsResponse = (
                stub.GenerateSuggestions(
                    suggestions.GenerateSuggestionsRequest(
                        order_id=order_id_proto, vector_clock=vector_clock_proto
                    )
                )
            )

        return response


def serve():
    logging.basicConfig(
        format="%(asctime)s | %(levelname)s | %(processName)s| %(message)s",
        level=logging.INFO,
    )
    logging.info("Starting the fraud detection server")
    server = grpc.server(futures.ThreadPoolExecutor())
    fraud_detection_grpc.add_FraudDetectionServiceServicer_to_server(
        FraudDetectionService(), server
    )
    port = "50051"
    server.add_insecure_port("[::]:" + port)
    server.start()
    logging.info(f"Server started. Listening on port {port}.")
    server.wait_for_termination()


if __name__ == "__main__":
    serve()
