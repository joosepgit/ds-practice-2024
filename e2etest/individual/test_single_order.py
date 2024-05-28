import requests

from ..testutil import *

request_url = "http://localhost:8081/checkout"
request_book_title = "Learning Python"
request_book_quantity = 1
request_user_first_name = "Thomas"
request_user_surname = "Eigenbaum"
request_data = build_simple_valid_order(
    request_user_first_name,
    request_user_surname,
    request_book_title,
    request_book_quantity,
)

mongo_query = {"title": request_book_title}


def test_single_valid():
    mongo_query = {"title": request_book_title}
    initial_document = collection.find_one(mongo_query)
    initial_stock = int(initial_document["stock"])
    response = requests.post(request_url, json=request_data).json()
    assert response["status"] == "Order Accepted"
    assert is_valid_uuid(response["orderId"])
    expected_updated_stock = initial_stock - request_book_quantity
    updated_stock = poll_until_value_updates(
        check_stock_updated, expected_updated_stock, mongo_query
    )
    assert updated_stock == expected_updated_stock
