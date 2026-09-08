"""
Tests the Gemini API connection using one fake customer enquiry.
This file does not modify the main AutoFlow workflow.
"""

import os

from dotenv import load_dotenv
from google import genai


# Load the private API key from .env
load_dotenv()

gemini_api_key = os.getenv("GEMINI_API_KEY")

if not gemini_api_key:
    print("Gemini test failed: GEMINI_API_KEY is missing.")

else:
    # Create a connection to the Gemini API
    client = genai.Client(api_key=gemini_api_key)

    try:
        # Ask Gemini to classify one fake customer message
        response = client.models.generate_content(
            model="gemini-3.5-flash-lite",
            contents=(
                "Classify this customer enquiry as Sales, Support, "
                "or Other. Return only the category.\n\n"
                "Message: I need help accessing my account."
            ),
        )

        print("Gemini classification:", response.text.strip())

    except Exception as error:
        print("Gemini test failed:", error)