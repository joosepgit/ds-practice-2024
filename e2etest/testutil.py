import uuid
import pytest

from pymongo import MongoClient
from tenacity import retry, stop_after_delay, wait_fixed, RetryError

# Assumes that the primary mongo node at port 27017 is alive
client = MongoClient("mongodb://mongo:mongo@localhost:27017/bookstore")
db = client["bookstore"]
collection = db["books"]


def build_simple_valid_order(user_first_name, user_surname, book_title, book_quantity):
    return {
        "user": {"name": user_first_name, "contact": user_surname},
        "creditCard": {
            "number": "5555555555554444",
            "expirationDate": "12/26",
            "cvv": "491",
        },
        "userComment": "Some test comment.",
        "items": [{"name": book_title, "quantity": book_quantity}],
        "discountCode": "123",
        "shippingMethod": "123",
        "giftMessage": "",
        "billingAddress": {
            "street": "Turu",
            "city": "Tartu",
            "state": "Tartumaa",
            "zip": "50701",
            "country": "Estonia",
        },
        "giftWrapping": False,
        "termsAndConditionsAccepted": True,
        "notificationPreferences": ["email"],
        "device": {
            "type": "Smartphone",
            "model": "Samsung Galaxy S10",
            "os": "Android 10.0.0",
        },
        "browser": {"name": "Chrome", "version": "85.0.4183.127"},
        "appVersion": "3.0.0",
        "screenResolution": "1440x3040",
        "referrer": "https://www.google.com",
        "deviceLanguage": "en-US",
    }


def build_simple_invalid_order(
    user_first_name,
    user_surname,
    book_title,
    book_quantity,
    zip_code,
    country,
    card_number,
    cvv,
    exp_date,
):
    return {
        "user": {"name": user_first_name, "contact": user_surname},
        "creditCard": {"number": card_number, "expirationDate": exp_date, "cvv": cvv},
        "userComment": "Some test comment.",
        "items": [{"name": book_title, "quantity": book_quantity}],
        "discountCode": "123",
        "shippingMethod": "123",
        "giftMessage": "",
        "billingAddress": {
            "street": "Turu",
            "city": "Tartu",
            "state": "Tartumaa",
            "zip": zip_code,
            "country": country,
        },
        "giftWrapping": False,
        "termsAndConditionsAccepted": True,
        "notificationPreferences": ["email"],
        "device": {
            "type": "Smartphone",
            "model": "Samsung Galaxy S10",
            "os": "Android 10.0.0",
        },
        "browser": {"name": "Chrome", "version": "85.0.4183.127"},
        "appVersion": "3.0.0",
        "screenResolution": "1440x3040",
        "referrer": "https://www.google.com",
        "deviceLanguage": "en-US",
    }


@retry(stop=stop_after_delay(10), wait=wait_fixed(1))
def poll_until_value_updates(check_function, expected, query):
    value = check_function(query)
    if value == expected:
        return value
    raise ValueError("Value has not changed yet.")


@retry(stop=stop_after_delay(10), wait=wait_fixed(1))
def poll_until_value_changes(check_function, query):
    value = check_function(query)
    if value:
        return value
    raise ValueError("Value has not changed yet.")


def is_valid_uuid(val):
    try:
        uuid.UUID(str(val))
        return True
    except ValueError:
        return False


def check_stock_updated(query):
    updated_document = collection.find_one(query)
    return int(updated_document["stock"])
