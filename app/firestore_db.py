import datetime
from typing import Dict, Any, List
from google.cloud import firestore
from google.api_core.exceptions import NotFound, GoogleAPIError

# Hardcoded project ID per lab instructions
PROJECT_ID = "qwiklabs-gcp-01-b8db88e6dbe4"
COLLECTION_NAME = "plants"

# In-memory fallback dataset in case Firestore database is not yet provisioned in GCP project
FALLBACK_PLANTS: Dict[str, Dict[str, Any]] = {
    "monstera": {
        "plant_id": "monstera",
        "plant_name": "Monstera Deliciosa",
        "species": "Monstera Deliciosa",
        "light_requirement": "Bright, indirect light",
        "watering_frequency_days": 10,
        "last_watered": "2026-09-25",
        "notes": "Loves humidity. Wipe leaves to clear dust.",
        "status": "Healthy",
    },
    "pothos": {
        "plant_id": "pothos",
        "plant_name": "Golden Pothos",
        "species": "Epipremnum aureum",
        "light_requirement": "Medium to low indirect light",
        "watering_frequency_days": 7,
        "last_watered": "2026-09-28",
        "notes": "Easy to propagate in water.",
        "status": "Healthy",
    },
    "snake_plant": {
        "plant_id": "snake_plant",
        "plant_name": "Snake Plant",
        "species": "Sansevieria trifasciata",
        "light_requirement": "Low to bright indirect light",
        "watering_frequency_days": 21,
        "last_watered": "2026-09-20",
        "notes": "Drought tolerant. Avoid overwatering.",
        "status": "Thriving",
    },
    "fiddle_leaf_fig": {
        "plant_id": "fiddle_leaf_fig",
        "plant_name": "Fiddle Leaf Fig",
        "species": "Ficus lyrata",
        "light_requirement": "Bright, direct to indirect light",
        "watering_frequency_days": 7,
        "last_watered": "2026-09-26",
        "notes": "Sensitive to drafts and moving.",
        "status": "Needs Attention",
    },
}


def _get_firestore_client() -> firestore.Client | None:
    """Instantiates a Firestore client with hardcoded project_id."""
    try:
        return firestore.Client(project=PROJECT_ID)
    except Exception as e:
        print(f"Firestore client initialization warning: {e}")
        return None


def db_read_plants(plant_name: str = "") -> List[Dict[str, Any]]:
    """Reads all plants or a specific plant from Firestore (or fallback storage)."""
    client = _get_firestore_client()
    if client:
        try:
            coll = client.collection(COLLECTION_NAME)
            if plant_name:
                # Filter by name match
                docs = coll.stream()
                results = []
                query_lower = plant_name.lower()
                for doc in docs:
                    data = doc.to_dict()
                    if query_lower in data.get("plant_name", "").lower() or query_lower in data.get("plant_id", "").lower():
                        results.append(data)
                return results
            else:
                docs = coll.stream()
                return [doc.to_dict() for doc in docs]
        except (NotFound, GoogleAPIError) as e:
            print(f"Firestore read fallback active: {e}")

    # Fallback to in-memory store
    if plant_name:
        query_lower = plant_name.lower().replace(" ", "_")
        matches = []
        for key, data in FALLBACK_PLANTS.items():
            if query_lower in key or query_lower in data["plant_name"].lower():
                matches.append(data)
        return matches
    return list(FALLBACK_PLANTS.values())


def db_add_plant(
    plant_name: str,
    species: str,
    light_requirement: str = "Bright, indirect light",
    watering_frequency_days: int = 7,
    last_watered: str = "",
    notes: str = "",
    status: str = "Healthy",
) -> Dict[str, Any]:
    """Adds a new plant record to Firestore (or fallback storage)."""
    doc_id = plant_name.lower().replace(" ", "_")
    if not last_watered:
        last_watered = datetime.date.today().strftime("%Y-%m-%d")

    record = {
        "plant_id": doc_id,
        "plant_name": plant_name,
        "species": species,
        "light_requirement": light_requirement,
        "watering_frequency_days": watering_frequency_days,
        "last_watered": last_watered,
        "notes": notes,
        "status": status,
    }

    client = _get_firestore_client()
    if client:
        try:
            client.collection(COLLECTION_NAME).document(doc_id).set(record)
            return record
        except (NotFound, GoogleAPIError) as e:
            print(f"Firestore write fallback active: {e}")

    FALLBACK_PLANTS[doc_id] = record
    return record


def db_update_watering(plant_name: str, date: str = "") -> Dict[str, Any] | None:
    """Updates the last_watered date for a plant in Firestore (or fallback storage)."""
    if not date:
        date = datetime.date.today().strftime("%Y-%m-%d")

    doc_id = plant_name.lower().replace(" ", "_")
    client = _get_firestore_client()

    if client:
        try:
            doc_ref = client.collection(COLLECTION_NAME).document(doc_id)
            doc = doc_ref.get()
            if doc.exists:
                doc_ref.update({"last_watered": date})
                updated = doc.to_dict()
                updated["last_watered"] = date
                return updated
            else:
                # Search by display name
                docs = client.collection(COLLECTION_NAME).stream()
                for d in docs:
                    data = d.to_dict()
                    if plant_name.lower() in data.get("plant_name", "").lower():
                        client.collection(COLLECTION_NAME).document(d.id).update({"last_watered": date})
                        data["last_watered"] = date
                        return data
        except (NotFound, GoogleAPIError) as e:
            print(f"Firestore update fallback active: {e}")

    # Fallback storage update
    for key, data in FALLBACK_PLANTS.items():
        if doc_id in key or plant_name.lower() in data["plant_name"].lower():
            data["last_watered"] = date
            return data
    return None


def db_get_watering_alerts() -> List[Dict[str, Any]]:
    """Calculates which plants are due or overdue for watering based on last_watered and watering_frequency_days."""
    all_plants = db_read_plants()
    today = datetime.date.today()
    alerts = []

    for plant in all_plants:
        last_watered_str = plant.get("last_watered", "")
        freq_days = plant.get("watering_frequency_days", 7)

        if not last_watered_str:
            continue

        try:
            last_watered_date = datetime.datetime.strptime(last_watered_str, "%Y-%m-%d").date()
        except ValueError:
            continue

        due_date = last_watered_date + datetime.timedelta(days=freq_days)
        days_diff = (today - due_date).days

        if days_diff >= 0:
            alerts.append({
                "plant_name": plant.get("plant_name"),
                "species": plant.get("species"),
                "last_watered": last_watered_str,
                "due_date": due_date.strftime("%Y-%m-%d"),
                "days_overdue": days_diff,
                "is_due_today": (days_diff == 0),
                "status": plant.get("status"),
            })

    return alerts

