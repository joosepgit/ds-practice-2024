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
    
    def GenerateSuggestions(self, request: suggestions.GenerateSuggestionsRequest, context):
        logging.info(f"Generating suggestions for order {request.order_id.value}")

        self.update_vector_clock(request.order_id.value, dict(request.vector_clock.clocks))
        
        response = suggestions.GenerateSuggestionsResponse()

        cached_data: tuple[dict, suggestions.InitializationRequest] = vector_clock_cache[request.order_id.value]
        vector_clock, data = cached_data

        logging.info(f"Generating random suggestions based on data: {data}")
        generated_suggestions = suggestions.GetSuggestionsResponse()
        for _ in range(3):
            generated_suggestions.suggested_books.append(self.get_random_suggestion())
        logging.info(f"Generated suggestions: {generated_suggestions}")

        vector_clock_cache[request.order_id.value][1] = generated_suggestions

        vector_clock[SERVICE_IDENTIFIER] += 1
        vector_clock = self.update_vector_clock(request.order_id.value, vector_clock)

        response.vector_clock.clocks.update(vector_clock_cache[request.order_id.value][0])
        
        response.success = True
        response.additional_info = f'Suggestions:\n\
            \tOK;\n'

        return response

    def GetSuggestions(self, request: suggestions.GetSuggestionsRequest, context):
        logging.info(f'Fetching suggestions with request: {request}')

        self.update_vector_clock(request.order_id.value, dict(request.vector_clock.clocks))

        cached_data: tuple[dict, suggestions.GetSuggestionsResponse] = vector_clock_cache[request.order_id.value]
        vector_clock, response = cached_data

        logging.info(f'Got suggestions: {response}')

        vector_clock[SERVICE_IDENTIFIER] += 1
        vector_clock = self.update_vector_clock(request.order_id.value, vector_clock)

        response.vector_clock.clocks.update(vector_clock_cache[request.order_id.value][0])

        response.success = True
        response.additional_info = 'OK'
        return response
    
    def ClearData(self, request: suggestions.ClearDataRequest, context):
        logging.info(f"Clearing data for request {request}")
        curr_vector_clock: dict = vector_clock_cache[request.order_id.value][0]
        passed_vector_clock = dict(request.vector_clock.clocks)
        for k, _ in curr_vector_clock.items():
            if curr_vector_clock[k] > passed_vector_clock[k]:
                raise ValueError(f"Final vector clock has a smaller value  than local vector clock for service {k}")
        
        logging.debug(f"Current vector clock: {curr_vector_clock}")
        logging.debug(f"Passed vector clock: {passed_vector_clock}")
        del vector_clock_cache[request.order_id.value]
        return suggestions.ClearDataResponse()
    
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