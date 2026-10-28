"""Retrieves EUR-to-USD reference rates from the Frankfurter API."""

import requests


FRANKFURTER_URL = "https://api.frankfurter.dev/v1/latest?base=EUR&symbols=USD"


def fetch_eur_to_usd():
    """Return (exchange_rate, rate_date), or (None, None) if unavailable."""

    try:
        response = requests.get(FRANKFURTER_URL, timeout=30)
        response.raise_for_status()
        data = response.json()

        exchange_rate = data["rates"]["USD"]
        rate_date = data["date"]

        print(f"Reference rate: 1 EUR = {exchange_rate} USD")
        print("Rate date:", rate_date)

        return exchange_rate, rate_date

    except (requests.RequestException, ValueError, KeyError) as error:
        print("Exchange rate unavailable:", error)
        print("Customer categorization will continue without quotes.")

        return None, None
