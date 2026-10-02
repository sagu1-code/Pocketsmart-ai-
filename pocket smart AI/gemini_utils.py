import os
from dotenv import load_dotenv

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")


def fallback_recommendation(category, budget, details):
    """
    Demo recommendation used when a Gemini API key
    has not been configured.
    """

    if category == "Home Interior":
        return f"""
HOME INTERIOR RECOMMENDATION

Budget: ₹{budget:,.0f}

Based on your requirements:
{details}

Suggested plan:
• Divide the budget between furniture, decoration and lighting.
• Prioritize essential furniture first.
• Choose a style that matches the room size.
• Keep a portion of the budget for unexpected expenses.

Budget tip:
Try to keep approximately 10% of the budget as a reserve.

Note:
This is a demo recommendation. Add your Gemini API key
to enable AI-generated recommendations.
"""

    elif category == "Party Planning":
        return f"""
PARTY PLANNING RECOMMENDATION

Budget: ₹{budget:,.0f}

Based on your requirements:
{details}

Suggested plan:
• Allocate the largest portion to food and refreshments.
• Reserve part of the budget for decoration.
• Select entertainment according to the number of guests.
• Keep some money available for unexpected expenses.

Budget tip:
Create a guest-based spending limit before making purchases.

Note:
This is a demo recommendation. Add your Gemini API key
to enable AI-generated recommendations.
"""

    elif category == "Jewelry":
        return f"""
JEWELRY RECOMMENDATION

Budget: ₹{budget:,.0f}

Based on your requirements:
{details}

Suggested plan:
• Choose jewelry appropriate for the occasion.
• Consider matching the jewelry with the preferred color.
• Compare simple and statement designs within the budget.
• Keep the total purchase cost within the specified budget.

Style tip:
Choose pieces that complement the outfit rather than
overpowering it.

Note:
This is a demo recommendation. Add your Gemini API key
to enable AI-generated recommendations.
"""

    return f"""
POCKETSMART AI RECOMMENDATION

Budget: ₹{budget:,.0f}

Requirements:
{details}

Please choose products and services that fit within your
budget and keep some amount available for unexpected costs.
"""


def get_recommendation(category, budget, details):
    """
    Generate a recommendation using Gemini when an API key
    is available. Otherwise, use the built-in demo mode.
    """

    if not GEMINI_API_KEY:
        return fallback_recommendation(
            category,
            budget,
            details
        )

    try:
        from google import genai

        client = genai.Client(
            api_key=GEMINI_API_KEY
        )

        prompt = f"""
You are PocketSmart AI, a smart budget and recommendation assistant.

Category:
{category}

User Budget:
₹{budget:,.0f}

User Requirements:
{details}

Generate a practical and easy-to-understand recommendation.

Important instructions:
1. Respect the user's stated budget.
2. Break the budget into useful spending categories.
3. Suggest practical options.
4. Explain why the recommendations fit the requirements.
5. Do not claim live prices, inventory or availability.
6. Clearly mention that prices are approximate when discussing costs.
7. Give useful budget-saving tips.
8. Keep the answer organized with headings and bullet points.

Return only the recommendation.
"""

        response = client.models.generate_content(
            model=GEMINI_MODEL,
            contents=prompt
        )

        if response and response.text:
            return response.text

        return fallback_recommendation(
            category,
            budget,
            details
        )

    except Exception as error:
        print("Gemini API error:", error)

        return fallback_recommendation(
            category,
            budget,
            details
        )