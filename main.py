import csv
import requests
from pathlib import Path
from datetime import datetime

exchange_rate = None
rate_date = None

url = "https://api.frankfurter.dev/v1/latest?base=EUR&symbols=USD"

try:
    response = requests.get(url, timeout=30)
    response.raise_for_status()
    data = response.json()

    exchange_rate = data["rates"]["USD"]
    rate_date = data["date"]

    print(f"Reference rate: 1 EUR = {exchange_rate} USD")
    print("Rate date:", rate_date)

except (requests.RequestException, ValueError, KeyError) as error:
    print("Exchange rate unavailable:", error)
    print("Customer categorization will continue without quotes.")

file_path = Path(__file__).parent / "customers.csv"

processed_customers = []

with file_path.open("r", newline="", encoding="utf-8") as file:
    customers = csv.DictReader(file)

    for customer in customers:
        message = customer["message"].lower()

        if "price" in message:
            category = "Sales"
        elif "help" in message:
            category = "Support"
        else:
            category = "Other"

        print(customer["name"], "→", category)

        customer["category"] = category

        customer["quote_eur"] = ""
        customer["quote_usd"] = ""
        customer["rate_date"] = ""

        if category == "Sales" and exchange_rate is not None:
            customer["quote_eur"] = "100.00"
            customer["quote_usd"] = f"{100 * exchange_rate:.2f}"
            customer["rate_date"] = rate_date
        processed_customers.append(customer)

output_path = Path(__file__).parent / "processed_customers.csv"

with output_path.open("w", newline="", encoding="utf-8") as file:
    columns = [
        "id", "name", "email", "message", "category",
        "quote_eur", "quote_usd", "rate_date"
    ]
    writer = csv.DictWriter(file, fieldnames=columns)

    writer.writeheader()
    writer.writerows(processed_customers)

print("Results saved to:", output_path)

log_path = Path(__file__).parent / "activity.log"
timestamp = datetime.now().astimezone().isoformat(timespec="seconds")

with log_path.open("a", encoding="utf-8") as log:
    for customer in processed_customers:
        log.write(
            f"{timestamp} | ID: {customer['id']} | "
            f"Category: {customer['category']}\n"
        )

print("Activity log saved.")