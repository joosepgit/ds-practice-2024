import requests

from ..testutil import *

request_url = "http://localhost:8081/checkout"
book_quantity = 2
user_first_name = "Thomas"
user_surname = "Eigenbaum"


def get_request_data_and_query(book_title):
    return (
        build_simple_valid_order(
            user_first_name, user_surname, book_title, book_quantity
        ),
        {"title": book_title},
    )


def test_javascript():
    request_data, mongo_query = get_request_data_and_query(
        "JavaScript - The Good Parts"
    )
    initial_document = collection.find_one(mongo_query)
    initial_stock = int(initial_document["stock"])
    response = requests.post(request_url, json=request_data).json()
    assert response["status"] == "Order Accepted"
    assert is_valid_uuid(response["orderId"])
    expected_updated_stock = initial_stock - book_quantity
    updated_stock = poll_until_value_updates(
        check_stock_updated, expected_updated_stock, mongo_query
    )
    assert updated_stock == expected_updated_stock


def test_dds():
    request_data, mongo_query = get_request_data_and_query(
        "Domain-Driven Design: Tackling Complexity in the Heart of Software"
    )
    initial_document = collection.find_one(mongo_query)
    initial_stock = int(initial_document["stock"])
    response = requests.post(request_url, json=request_data).json()
    assert response["status"] == "Order Accepted"
    assert is_valid_uuid(response["orderId"])
    expected_updated_stock = initial_stock - book_quantity
    updated_stock = poll_until_value_updates(
        check_stock_updated, expected_updated_stock, mongo_query
    )
    assert updated_stock == expected_updated_stock


def test_dp():
    request_data, mongo_query = get_request_data_and_query(
        "Design Patterns: Elements of Reusable Object-Oriented Software"
    )
    initial_document = collection.find_one(mongo_query)
    initial_stock = int(initial_document["stock"])
    response = requests.post(request_url, json=request_data).json()
    assert response["status"] == "Order Accepted"
    assert is_valid_uuid(response["orderId"])
    expected_updated_stock = initial_stock - book_quantity
    updated_stock = poll_until_value_updates(
        check_stock_updated, expected_updated_stock, mongo_query
    )
    assert updated_stock == expected_updated_stock
