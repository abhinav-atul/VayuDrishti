"""
Chat Service — LLM-powered air quality advisory via OpenRouter.

Provides contextual health advice using real AQI data from the model.
"""

from openai import AsyncOpenAI
from app.config import settings

_client = None


def _get_client() -> AsyncOpenAI:
    """Lazily initialize the OpenRouter client."""
    global _client
    if _client is None:
        _client = AsyncOpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=settings.OPENROUTER_API_KEY,
        )
    return _client


SYSTEM_PROMPT = """You are VayuDrishti, an AI air quality advisor for Delhi, India.

You help citizens understand air quality conditions in their area and provide
health-protective advice. You are precise, evidence-based, and caring.

IMPORTANT RULES:
- Always cite the actual AQI/PM2.5 data provided to you. Never invent numbers.
- Use the Indian National AQI scale: Good (0-50), Satisfactory (51-100), 
  Moderate (101-200), Poor (201-300), Very Poor (301-400), Severe (401-500).
- Give specific, actionable health advice based on the AQI category.
- For sensitive groups (children, elderly, asthma/COPD patients), be extra cautious.
- If asked about a specific location, use the nearest station data provided.
- You can respond in English, Hindi, Kannada, or Tamil based on user preference.
- Keep responses concise (2-3 paragraphs max). No fluff.
- Be honest about uncertainty — say "estimated" when using model predictions vs ground truth.
"""


async def get_advisory(
    message: str,
    aqi_context: dict | None = None,
    language: str = "en",
) -> dict:
    """Generate an air quality advisory response.
    
    Args:
        message: User's question
        aqi_context: Current AQI data for context (from model/stations)
        language: Response language code
    
    Returns:
        dict with reply text and sources
    """
    api_key = settings.OPENROUTER_API_KEY
    if not api_key or api_key == "your_openrouter_key_here":
        return _fallback_response(message, aqi_context)

    # Build context message with real data
    context_parts = []
    if aqi_context:
        context_parts.append(f"Current conditions at queried location:")
        context_parts.append(f"- Predicted PM2.5: {aqi_context.get('predicted_pm25', 'N/A')} µg/m³")
        context_parts.append(f"- Predicted AQI: {aqi_context.get('predicted_aqi', 'N/A')}")
        context_parts.append(f"- Category: {aqi_context.get('aqi_category', 'N/A')}")
        context_parts.append(f"- Confidence: {aqi_context.get('confidence', 'N/A')}")
        context_parts.append(f"- Nearest station: {aqi_context.get('nearest_station_name', 'N/A')} ({aqi_context.get('nearest_station_dist_km', 'N/A')} km away)")

        if aqi_context.get("city_stats"):
            stats = aqi_context["city_stats"]
            context_parts.append(f"\nDelhi city-wide:")
            context_parts.append(f"- Average AQI: {stats.get('avg_aqi', 'N/A')}")
            context_parts.append(f"- Worst area: {stats.get('worst_station', 'N/A')}")
            context_parts.append(f"- Best area: {stats.get('best_station', 'N/A')}")

    language_instruction = ""
    if language == "hi":
        language_instruction = "\n\nPlease respond in Hindi (Devanagari script)."
    elif language == "kn":
        language_instruction = "\n\nPlease respond in Kannada."
    elif language == "ta":
        language_instruction = "\n\nPlease respond in Tamil."

    context_str = "\n".join(context_parts) if context_parts else "No specific location data available."

    try:
        client = _get_client()
        response = await client.chat.completions.create(
            model="google/gemini-2.5-flash",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT + language_instruction},
                {"role": "user", "content": f"CURRENT DATA:\n{context_str}\n\nUSER QUESTION:\n{message}"},
            ],
            max_tokens=500,
            temperature=0.3,
        )

        reply = response.choices[0].message.content
        return {
            "reply": reply,
            "aqi_context": aqi_context,
            "sources": ["WAQI/CPCB Station Network", "VayuDrishti ML Model", "NASA VIIRS"],
        }

    except Exception as e:
        print(f"OpenRouter chat failed: {e}")
        return _fallback_response(message, aqi_context)


def _fallback_response(message: str, aqi_context: dict | None) -> dict:
    """Fallback response when LLM is unavailable."""
    if aqi_context:
        aqi = aqi_context.get("predicted_aqi", 0)
        category = aqi_context.get("aqi_category", "Unknown")
        pm25 = aqi_context.get("predicted_pm25", 0)

        reply = (
            f"Based on our model's prediction, the estimated PM2.5 at your location is "
            f"**{pm25} µg/m³** (AQI: {aqi}, **{category}**).\n\n"
        )

        if aqi <= 50:
            reply += "Air quality is good. It's a great time for outdoor activities!"
        elif aqi <= 100:
            reply += "Air quality is satisfactory. Sensitive individuals should consider limiting prolonged outdoor exertion."
        elif aqi <= 200:
            reply += "Air quality is moderate. Consider reducing outdoor activities, especially if you have respiratory conditions."
        elif aqi <= 300:
            reply += "Air quality is poor. Avoid prolonged outdoor activities. Keep windows closed. Children and elderly should stay indoors."
        elif aqi <= 400:
            reply += "Air quality is very poor. Avoid all outdoor physical activities. Use an N95 mask if you must go outside."
        else:
            reply += "Air quality is severe. Stay indoors with windows closed. Use an air purifier if available. Seek medical attention if you experience breathing difficulty."
    else:
        reply = (
            "I can help you understand air quality in Delhi. Try asking about a "
            "specific area — click on the map to see the estimated AQI at any location, "
            "then ask me for health advice!"
        )

    return {
        "reply": reply,
        "aqi_context": aqi_context,
        "sources": ["VayuDrishti ML Model"],
    }
