import sys
from google.cloud import firestore

PROJECT_ID = "qwiklabs-gcp-01-b8db88e6dbe4"
COLLECTION_NAME = "plants"

SEED_PLANTS = [
    {
        "plant_id": "monstera",
        "plant_name": "Monstera Deliciosa",
        "species": "Monstera Deliciosa",
        "light_requirement": "Bright, indirect light",
        "watering_frequency_days": 10,
        "last_watered": "2026-09-25",
        "notes": "Loves humidity and tropical environments. Wipe leaves to clear dust.",
        "status": "Healthy",
    },
    {
        "plant_id": "pothos",
        "plant_name": "Golden Pothos",
        "species": "Epipremnum aureum",
        "light_requirement": "Medium to low indirect light",
        "watering_frequency_days": 7,
        "last_watered": "2026-09-28",
        "notes": "Trails gracefully. Easy to propagate in water.",
        "status": "Healthy",
    },
    {
        "plant_id": "snake_plant",
        "plant_name": "Snake Plant",
        "species": "Sansevieria trifasciata",
        "light_requirement": "Low to bright indirect light",
        "watering_frequency_days": 21,
        "last_watered": "2026-09-20",
        "notes": "Drought tolerant. Very hard to kill, avoid overwatering.",
        "status": "Thriving",
    },
    {
        "plant_id": "fiddle_leaf_fig",
        "plant_name": "Fiddle Leaf Fig",
        "species": "Ficus lyrata",
        "light_requirement": "Bright, direct to indirect light",
        "watering_frequency_days": 7,
        "last_watered": "2026-09-26",
        "notes": "Sensitive to drafts and moving. Keep in a consistent bright spot.",
        "status": "Needs Attention",
    },
]


def seed_database():
    print(f"Connecting to Firestore with project_id='{PROJECT_ID}'...")
    db = firestore.Client(project=PROJECT_ID)
    plants_ref = db.collection(COLLECTION_NAME)

    for plant in SEED_PLANTS:
        doc_id = plant["plant_id"]
        plants_ref.document(doc_id).set(plant)
        print(f"  [+] Seeded plant: {plant['plant_name']} (ID: {doc_id})")

    print(f"Successfully seeded {len(SEED_PLANTS)} plants into Firestore collection '{COLLECTION_NAME}'!")


if __name__ == "__main__":
    try:
        seed_database()
    except Exception as e:
        print(f"Error seeding Firestore: {e}", file=sys.stderr)
        sys.exit(1)
