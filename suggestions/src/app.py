import logging
import random

import grpc_gen.suggestions_pb2 as suggestions
import grpc_gen.suggestions_pb2_grpc as suggestions_grpc

import grpc
from concurrent import futures

from cachetools import TTLCache

SERVICE_IDENTIFIER = "SUGGESTIONS"

vector_clock_cache = TTLCache(maxsize=100, ttl=60)

class SuggestionService(suggestions_grpc.SuggestionServiceServicer):
    def Initialize(self, request: suggestions.InitializationRequest, context):
        logging.info("Initializing suggestions")

        response = suggestions.InitializationResponse()

        vector_clock = {SERVICE_IDENTIFIER : 0}
        vector_clock_cache[request.order_id.value] = [vector_clock, request]

        response.success = True
        response.additional_info = ""
        logging.info(f"Successfully initialized suggestions with vector clock: {vector_clock} \
                      and data: {request}")
        return response

    def GetSuggestions(self, request: suggestions.GetSuggestionsRequest, context):
        logging.info(f'Fetching suggestions with request: {request}')
        response = suggestions.GetSuggestionsResponse()
        for _ in range(3):
            response.suggested_books.append(self.get_random_suggestion())
        logging.info(f'Got suggestions: {response}')
        response.success = True
        response.additional_info = ""
        return response
    
    def get_random_suggestion(self):
        ids = [123, 234, 345, 456]
        titles = ['Big Finnish Fish', 'Beekeeping 1.0', 'Beekeeping 2.0', 'Moomin']
        authors = ['Joosep Tavits', 'Bernard Szeliga', 'Joe Biden', 'Barack Obama']
        suggested_book = suggestions.Book()
        suggested_book.book_id = random.choice(ids)
        suggested_book.title = random.choice(titles)
        suggested_book.author = random.choice(authors)
        return suggested_book


def serve():
    logging.basicConfig(format="%(asctime)s | %(levelname)s | %(processName)s| %(message)s", level=logging.INFO)
    server = grpc.server(futures.ThreadPoolExecutor())
    suggestions_grpc.add_SuggestionServiceServicer_to_server(SuggestionService(), server)
    port = "50053"
    server.add_insecure_port("[::]:" + port)
    server.start()
    print("Server started. Listening on port 50053.")
    server.wait_for_termination()

if __name__ == '__main__':
    serve()