"""
Uses Gemini to classify customer enquiries and explain its decision.

If AI is disabled or unavailable, AutoFlow returns to keyword rules.
"""

import os
from typing import Literal

from dotenv import load_dotenv
from google import genai
from google.genai import types
from pydantic import BaseModel, Field


# Define the exact structure Gemini must return
class ClassificationResult(BaseModel):
    category: Literal["Sales", "Support", "Other"]
    reason: str = Field(
        description="One short sentence explaining the category."
    )


load_dotenv()
gemini_api_key = os.getenv("GEMINI_API_KEY")


def classify_with_ai(message):
    """Return an AI classification dictionary or None."""

    ai_enabled = os.getenv(
        "AI_CLASSIFICATION_ENABLED", "false"
    ).lower()

    if ai_enabled != "true":
        return None

    if not gemini_api_key:
        print("AI classification skipped: API key is missing.")
        return None

    client = genai.Client(api_key=gemini_api_key)

    try:
        # Require Gemini to return JSON matching ClassificationResult
        response = client.models.generate_content(
            model="gemini-3.5-flash-lite",
            contents=(
                "Classify this customer enquiry as Sales, Support, "
                "or Other. Give one short reason.\n\n"
                f"Customer message: {message}"
            ),
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=ClassificationResult,
            ),
        )

        result = ClassificationResult.model_validate_json(
            response.text
        )

        return {
            "category": result.category,
            "reason": result.reason,
        }

    except Exception as error:
        print("AI classification unavailable:", error)
        return None