import logging

import grpc_gen.payment_pb2 as payment
import grpc_gen.payment_pb2_grpc as payment_grpc

import grpc

from concurrent import futures

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
resource = Resource(attributes={SERVICE_NAME: "payment"})

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


class PaymentService(payment_grpc.PaymentServiceServicer):

    def DoPayment(self, request, context):
        return super().DoPayment(request, context)


def serve():
    logging.basicConfig(
        format="%(asctime)s | %(levelname)s | %(processName)s| %(message)s",
        level=logging.DEBUG,
    )
    server = grpc.server(futures.ThreadPoolExecutor())
    payment_grpc.add_PaymentServiceServicer_to_server(PaymentService(), server)
    port = "50057"
    server.add_insecure_port("[::]:" + port)
    server.start()
    print("Server started. Listening on port 50057.")
    server.wait_for_termination()


if __name__ == "__main__":
    serve()
