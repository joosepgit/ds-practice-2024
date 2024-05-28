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
    expected_updated_stock = initial_stock - book_quantity * 1
    updated_stock = poll_until_value_updates(
        check_stock_updated, expected_updated_stock, mongo_query
    )
    assert updated_stock == expected_updated_stock


def test_javascript2():
    request_data, mongo_query = get_request_data_and_query(
        "JavaScript - The Good Parts"
    )
    initial_document = collection.find_one(mongo_query)
    initial_stock = int(initial_document["stock"])
    response = requests.post(request_url, json=request_data).json()
    assert response["status"] == "Order Accepted"
    assert is_valid_uuid(response["orderId"])
    expected_updated_stock = initial_stock - book_quantity * 2
    updated_stock = poll_until_value_updates(
        check_stock_updated, expected_updated_stock, mongo_query
    )
    assert updated_stock == expected_updated_stock


def test_javascript3():
    request_data, mongo_query = get_request_data_and_query(
        "JavaScript - The Good Parts"
    )
    initial_document = collection.find_one(mongo_query)
    initial_stock = int(initial_document["stock"])
    response = requests.post(request_url, json=request_data).json()
    assert response["status"] == "Order Accepted"
    assert is_valid_uuid(response["orderId"])
    expected_updated_stock = initial_stock - book_quantity * 3
    updated_stock = poll_until_value_updates(
        check_stock_updated, expected_updated_stock, mongo_query
    )
    assert updated_stock == expected_updated_stock


def test_javascript4():
    request_data, mongo_query = get_request_data_and_query(
        "JavaScript - The Good Parts"
    )
    initial_document = collection.find_one(mongo_query)
    initial_stock = int(initial_document["stock"])
    response = requests.post(request_url, json=request_data).json()
    assert response["status"] == "Order Accepted"
    assert is_valid_uuid(response["orderId"])
    expected_updated_stock = initial_stock - book_quantity * 4
    updated_stock = poll_until_value_updates(
        check_stock_updated, expected_updated_stock, mongo_query
    )
    assert updated_stock == expected_updated_stock
