import sys
import os
import logging

import grpc_gen.suggestions_pb2 as suggestions
import grpc_gen.suggestions_pb2_grpc as suggestions_grpc

import grpc
from concurrent import futures

# Create a class to derive the server functions
class SuggestionService(suggestions_grpc.SuggestionServiceServicer):
    # Create an RPC function to say hello
    def GetSuggestions(self, request, context):
        # Create a response object
        response = suggestions.GetSuggestionsResponse()
        suggested_book = suggestions.Book()
        suggested_book.title = "Example Suggested Book"
        response.suggestedBooks = [suggested_book]
        # Return the response object
        return response

def serve():
    # Create a gRPC server
    server = grpc.server(futures.ThreadPoolExecutor())
    suggestions_grpc.add_SuggestionServiceServicer_to_server(SuggestionService(), server)
    # Listen on port 50053
    port = "50053"
    server.add_insecure_port("[::]:" + port)
    # Start the server
    server.start()
    print("Server started. Listening on port 50053.")
    # Keep thread alive
    server.wait_for_termination()

if __name__ == '__main__':
    serve()