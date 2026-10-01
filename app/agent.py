# ruff: noqa
# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import json
import os
import time
import urllib.parse
import requests

from a2ui.basic_catalog.provider import BasicCatalog
from a2ui.schema.manager import A2uiSchemaManager

from google import genai
from google.cloud import storage
from google.adk.agents import Agent
from google.adk.agents.callback_context import CallbackContext
from google.adk.apps import App
from google.adk.code_executors import AgentEngineSandboxCodeExecutor
from google.adk.memory import VertexAiMemoryBankService
from google.adk.models import Gemini
from google.adk.tools import ToolContext
from google.adk.tools.preload_memory_tool import PreloadMemoryTool
from google.genai import types

from app.a2ui_utils import a2ui_callback
from app.firestore_db import db_read_plants, db_add_plant, db_update_watering, db_get_watering_alerts

PROJECT_ID = "qwiklabs-gcp-01-b8db88e6dbe4"
BUCKET_NAME = "plant-care-companion-assets-b8db88e6dbe4"

# Read Agent Engine resource name from deployment_metadata.json
AGENT_ENGINE_ID = "projects/816205890724/locations/us-central1/reasoningEngines/102095701952954368"
metadata_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "deployment_metadata.json")
if os.path.exists(metadata_path):
    try:
        with open(metadata_path, "r") as f:
            meta = json.load(f)
            AGENT_ENGINE_ID = meta.get("remote_agent_runtime_id", AGENT_ENGINE_ID)
    except Exception:
        pass

MEMORY_BANK_ID = AGENT_ENGINE_ID.split("/")[-1]

# Initialize Agent Engine Sandbox Code Executor
code_executor = AgentEngineSandboxCodeExecutor(
    agent_engine_resource_name=AGENT_ENGINE_ID
)

# Initialize Vertex AI Memory Bank Service for durable user preferences
memory_service = VertexAiMemoryBankService(
    project=PROJECT_ID,
    location="us-central1",
    agent_engine_id=MEMORY_BANK_ID,
)


async def generate_memories_callback(callback_context: CallbackContext):
    """Callback to extract durable user facts and preferences to Memory Bank after each turn."""
    try:
        await callback_context.add_session_to_memory()
    except Exception as e:
        print(f"Memory Bank extraction notice: {e}")
    return None


def read_plants(plant_name: str = "") -> str:
    """Reads all plants or a specific plant from the Firestore database.

    Args:
        plant_name: Optional plant name or ID to filter by. Leave empty to retrieve all plants.

    Returns:
        Formatted summary of plant records stored in Firestore.
    """
    records = db_read_plants(plant_name=plant_name)
    if not records:
        if plant_name:
            return f"No plant record found matching '{plant_name}' in Firestore."
        return "No plants found in the Firestore collection."

    lines = [f"Found {len(records)} plant record(s) in Firestore:"]
    for idx, p in enumerate(records, 1):
        lines.append(
            f"{idx}. {p.get('plant_name')} ({p.get('species')})\n"
            f"   - Status: {p.get('status')}\n"
            f"   - Light: {p.get('light_requirement')}\n"
            f"   - Watering Frequency: Every {p.get('watering_frequency_days')} days\n"
            f"   - Last Watered: {p.get('last_watered')}\n"
            f"   - Notes: {p.get('notes')}"
        )
    return "\n".join(lines)


def add_plant(
    plant_name: str,
    species: str,
    light_requirement: str = "Bright, indirect light",
    watering_frequency_days: int = 7,
    last_watered: str = "",
    notes: str = "",
    status: str = "Healthy",
) -> str:
    """Adds a new plant record to the Firestore database.

    Args:
        plant_name: Display name of the plant (e.g. Fiddle Leaf Fig, Monstera).
        species: Botanical/species name (e.g. Ficus lyrata).
        light_requirement: Lighting needs (e.g. Bright, indirect light).
        watering_frequency_days: Days between waterings (e.g. 7, 14).
        last_watered: Last watered date (YYYY-MM-DD). Defaults to today if omitted.
        notes: Special care notes or location hints.
        status: Health status (e.g. Healthy, Thriving, Needs Attention).

    Returns:
        Confirmation message with the created record details.
    """
    record = db_add_plant(
        plant_name=plant_name,
        species=species,
        light_requirement=light_requirement,
        watering_frequency_days=watering_frequency_days,
        last_watered=last_watered,
        notes=notes,
        status=status,
    )
    return (
        f"Successfully added plant '{record['plant_name']}' to Firestore!\n"
        f"- ID: {record['plant_id']}\n"
        f"- Species: {record['species']}\n"
        f"- Last Watered: {record['last_watered']}\n"
        f"- Status: {record['status']}"
    )


def update_watering_info(plant_name: str, date: str = "") -> str:
    """Updates the last_watered date for a plant in the Firestore database.

    Args:
        plant_name: Name of the plant to update (e.g., Monstera, Snake Plant).
        date: Date string (YYYY-MM-DD). Defaults to today's date if omitted.

    Returns:
        Confirmation message of the updated record.
    """
    updated = db_update_watering(plant_name=plant_name, date=date)
    if updated:
        return (
            f"Successfully updated watering date for '{updated['plant_name']}' to {updated['last_watered']} in Firestore."
        )
    return f"Plant matching '{plant_name}' was not found in Firestore."


def check_watering_alerts() -> str:
    """Checks Firestore plant records to find plants that are due or overdue for watering today.

    Returns:
        A formatted list of plants requiring watering today, including due date and days overdue.
    """
    alerts = db_get_watering_alerts()
    if not alerts:
        return "All your plants are up to date on watering! No plants are due today."

    lines = [f"Watering Alert: {len(alerts)} plant(s) need attention today:"]
    for idx, a in enumerate(alerts, 1):
        if a["is_due_today"]:
            status_text = "DUE TODAY"
        else:
            status_text = f"OVERDUE by {a['days_overdue']} day(s)"

        lines.append(
            f"{idx}. {a['plant_name']} ({a['species']})\n"
            f"   - Status: {status_text} (Due: {a['due_date']})\n"
            f"   - Last Watered: {a['last_watered']}"
        )
    return "\n".join(lines)


def get_weather_recommendation(location: str) -> str:
    """Fetches real-time weather data from Open-Meteo API and provides plant-care watering recommendations.

    Args:
        location: City or location name to check weather for (e.g. Silver Spring, Maryland, Austin, TX).

    Returns:
        Real weather summary and specific plant-care recommendation based on live temperature and humidity.
    """
    try:
        city_query = location.split(",")[0].strip() if "," in location else location.strip()
        geo_url = f"https://geocoding-api.open-meteo.com/v1/search?name={urllib.parse.quote(city_query)}&count=1&language=en&format=json"
        geo_resp = requests.get(geo_url, timeout=5).json()

        if not geo_resp.get("results"):
            geo_url = f"https://geocoding-api.open-meteo.com/v1/search?name={urllib.parse.quote(location)}&count=1&language=en&format=json"
            geo_resp = requests.get(geo_url, timeout=5).json()

        if not geo_resp.get("results"):
            return f"Could not find geographic coordinates for location '{location}' via Open-Meteo."

        match = geo_resp["results"][0]
        lat = match["latitude"]
        lon = match["longitude"]
        city_name = match.get("name", location)
        admin1 = match.get("admin1", "")

        loc_label = f"{city_name}, {admin1}" if admin1 else city_name

        weather_url = (
            f"https://api.open-meteo.com/v1/forecast?"
            f"latitude={lat}&longitude={lon}&current=temperature_2m,relative_humidity_2m,weather_code&temperature_unit=fahrenheit"
        )
        weather_resp = requests.get(weather_url, timeout=5).json()
        current = weather_resp.get("current", {})

        temp_f = current.get("temperature_2m", 70.0)
        humidity = current.get("relative_humidity_2m", 50)
        weather_code = current.get("weather_code", 0)

        code_desc = "Clear"
        if weather_code in [1, 2, 3]:
            code_desc = "Partly Cloudy / Overcast"
        elif weather_code in [45, 48]:
            code_desc = "Foggy"
        elif weather_code in [51, 53, 55, 61, 63, 65, 80, 81, 82]:
            code_desc = "Rainy / Showers"
        elif weather_code in [71, 73, 75, 85, 86]:
            code_desc = "Snowy"
        elif weather_code >= 95:
            code_desc = "Thunderstorm"

        if temp_f >= 85 or humidity < 40:
            rec = (
                f"High temperature ({temp_f}°F) and low humidity ({humidity}%) will cause rapid soil drying. "
                f"Recommendation: Increase watering frequency by 20-30%, check soil moisture frequently, and mist tropical foliage."
            )
        elif temp_f <= 55 or humidity > 75 or "Rain" in code_desc:
            rec = (
                f"Cooler temperature ({temp_f}°F) or high humidity ({humidity}%). Evaporation is low. "
                f"Recommendation: Reduce watering frequency and ensure top 2 inches of soil are dry before watering to prevent root rot."
            )
        else:
            rec = (
                f"Moderate conditions ({temp_f}°F, {humidity}% humidity). "
                f"Recommendation: Maintain your standard watering schedule. Check soil dryness before watering."
            )

        return (
            f"Live Weather for {loc_label} (via Open-Meteo):\n"
            f"- Temperature: {temp_f}°F\n"
            f"- Relative Humidity: {humidity}%\n"
            f"- Condition: {code_desc}\n\n"
            f"Plant Care Recommendation:\n{rec}"
        )

    except Exception as e:
        return f"Error fetching live weather from Open-Meteo for '{location}': {e}"


def generate_plant_portrait(
    plant_name: str,
    tool_context: ToolContext = None,
) -> str:
    """Generates a visual portrait or care illustration for a requested houseplant using gemini-3.1-flash-lite-image.

    Saves the image to the Playground Artifacts panel (if tool_context available) and uploads it to the public Cloud Storage bucket.

    Args:
        plant_name: Name of the plant to generate a portrait or illustration for (e.g. Monstera, Pothos, Fiddle Leaf Fig).

    Returns:
        Public HTTPS URL of the generated plant image in Cloud Storage.
    """
    try:
        client = genai.Client(vertexai=True, project=PROJECT_ID, location="global")

        prompt = (
            f"A vibrant, high-quality, healthy plant portrait of a {plant_name} houseplant in a decorative ceramic pot "
            f"with clean ambient light, suitable for a plant care catalog."
        )

        response = client.models.generate_content(
            model="gemini-3.1-flash-lite-image",
            contents=prompt,
            config=types.GenerateContentConfig(response_modalities=["IMAGE"]),
        )

        image_bytes = None
        for part in response.candidates[0].content.parts:
            if part.inline_data:
                image_bytes = part.inline_data.data
                break

        if not image_bytes:
            return f"Failed to generate image bytes for '{plant_name}'."

        doc_id = plant_name.lower().replace(" ", "_")
        filename = f"plant_portraits/{doc_id}_{int(time.time())}.jpg"

        if tool_context and hasattr(tool_context, "save_artifact"):
            try:
                tool_context.save_artifact(filename=f"{doc_id}.jpg", content=image_bytes, mime_type="image/jpeg")
            except Exception as art_err:
                print(f"Artifact save notice: {art_err}")

        storage_client = storage.Client(project=PROJECT_ID)
        bucket = storage_client.bucket(BUCKET_NAME)
        blob = bucket.blob(filename)
        blob.upload_from_string(image_bytes, content_type="image/jpeg")

        public_url = f"https://storage.googleapis.com/{BUCKET_NAME}/{filename}"
        return (
            f"Successfully generated plant portrait for '{plant_name}' using gemini-3.1-flash-lite-image!\n"
            f"Public Image URL: {public_url}"
        )

    except Exception as e:
        return f"Error generating plant portrait for '{plant_name}': {e}"


# Build A2UI v0.8 System Prompt
schema_manager = A2uiSchemaManager(
    version="0.8",
    catalogs=[BasicCatalog.get_config("0.8")],
)

a2ui_instruction = schema_manager.generate_system_prompt(
    role_description="You are the Plant Care Companion, an expert AI botanist and houseplant care assistant.",
    workflow_description=(
        "You use a Firestore database backend to manage plant records, read user plants, add new plants, "
        "check watering alerts, and update watering records. You fetch live real-time weather from Open-Meteo, "
        "and generate high-quality plant portraits using `gemini-3.1-flash-lite-image`. You have an "
        "Agent Engine sandbox (`code_executor`) enabled for Python calculation blocks. "
        "You also store and recall durable user preferences from Vertex AI Memory Bank (such as gardening experience level, "
        "indoor/outdoor preference, preferred maintenance level, light/environment preferences, and care preferences). "
        "Always personalize your plant care recommendations based on the user's durable memory preferences while keeping plant records and care activity in Firestore."
    ),
    ui_description=(
        "Keep every surface tiny and flat: ONE Card > ONE Column > a few Text rows. "
        "Never nest a Card inside a Card. "
        "Use ONLY these components: Card, Column, Row, Text, and Image. Do not use "
        "Table or Heading (unsupported), or Buttons, actions, or forms (they do "
        "nothing in adk web). "
        "You may include one Image component, but only when you have a public https "
        "URL for the image (for example the URL an image tool returns after uploading "
        "to a public bucket). Set the Image url to that exact https link, for example "
        "{\"Image\": {\"url\": {\"literalString\": \"https://...\"}}}. Never point an "
        "Image at a bare filename, an artifact name, or a non-http(s) path. If you do "
        "not have a public URL, add a short Text line noting the image instead. "
        "No markdown in text; use the usageHint property ('h1', 'h2', 'body') for "
        "headings and emphasis. "
        "Output ONLY the raw A2UI JSON array — no prose, and never wrap it in "
        "<a2a_datapart_json> tags or 'kind'/'data'/'metadata' objects."
    ),
    include_schema=True,
    include_examples=True,
)

root_agent = Agent(
    name="root_agent",
    model=Gemini(
        model="gemini-2.5-flash",
        retry_options=types.HttpRetryOptions(attempts=3),
    ),
    code_executor=code_executor,
    instruction=a2ui_instruction,
    tools=[
        read_plants,
        add_plant,
        update_watering_info,
        check_watering_alerts,
        get_weather_recommendation,
        generate_plant_portrait,
        PreloadMemoryTool(),
    ],
    after_agent_callback=generate_memories_callback,
    after_model_callback=a2ui_callback,
)

app = App(
    root_agent=root_agent,
    name="app",
)
