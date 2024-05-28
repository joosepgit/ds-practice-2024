import requests

from ..testutil import *

request_url = "http://localhost:8081/checkout"
book_quantity = 2
user_first_name = "Thomas"
user_surname = "Eigenbaum"


def get_valid_request_data_and_query(book_title):
    return (
        build_simple_valid_order(
            user_first_name, user_surname, book_title, book_quantity
        ),
        {"title": book_title},
    )


def get_invalid_request_data_and_query(
    book_title,
    zip_code="50701",
    country="Estonia",
    card_number="5555555555554444",
    cvv="491",
    exp_date="12/26",
):
    return (
        build_simple_invalid_order(
            user_first_name,
            user_surname,
            book_title,
            book_quantity,
            zip_code,
            country,
            card_number,
            cvv,
            exp_date,
        ),
        {"title": book_title},
    )


def test_python():
    request_data, mongo_query = get_valid_request_data_and_query("Learning Python")
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


def test_javascript():
    request_data, mongo_query = get_valid_request_data_and_query(
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


def test_dds_ziperror():
    request_data, mongo_query = get_invalid_request_data_and_query(
        "Domain-Driven Design: Tackling Complexity in the Heart of Software",
        zip_code="5070",
    )
    initial_document = collection.find_one(mongo_query)
    initial_stock = int(initial_document["stock"])
    response = requests.post(request_url, json=request_data).json()
    assert "error" in response
    e_id, e_info = list(response["error"].items())[0]
    assert is_valid_uuid(e_id)
    assert e_info == "ZIP code should contain exactly 5 numbers."
    expected_updated_stock = initial_stock - book_quantity
    with pytest.raises(RetryError):
        poll_until_value_updates(
            check_stock_updated, expected_updated_stock, mongo_query
        )


def test_dp_countryerror():
    request_data, mongo_query = get_invalid_request_data_and_query(
        "Design Patterns: Elements of Reusable Object-Oriented Software",
        country="Finland",
    )
    initial_document = collection.find_one(mongo_query)
    initial_stock = int(initial_document["stock"])
    response = requests.post(request_url, json=request_data).json()
    assert "error" in response
    e_id, e_info = list(response["error"].items())[0]
    assert is_valid_uuid(e_id)
    print(e_info)
    assert "Finland can not be trusted, potentially fradulent transaction!" in e_info
    expected_updated_stock = initial_stock - book_quantity
    with pytest.raises(RetryError):
        poll_until_value_updates(
            check_stock_updated, expected_updated_stock, mongo_query
        )
