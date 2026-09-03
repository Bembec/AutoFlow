import requests

url = "https://api.frankfurter.dev/v1/latest?base=EUR&symbols=USD"

try:
    response = requests.get(url, timeout=30)
    response.raise_for_status()
    data = response.json()

    print("Rate date:", data["date"])
    print("1 EUR =", data["rates"]["USD"], "USD")

except (requests.RequestException, ValueError) as error:
    print("Could not retrieve exchange rates:", error)