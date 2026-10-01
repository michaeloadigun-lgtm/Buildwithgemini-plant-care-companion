# 🪴 Plant Care Companion

**Plant Care Companion** is an intelligent, agentic houseplant management assistant built with the Google Agent Development Kit (ADK) and deployed to Vertex AI Agent Platform. It combines real-time database tracking, environmental weather integration, generative AI plant portraits, remote sandbox code execution, long-term memory, and dynamic A2UI (Agent-to-User Interface) card rendering into a web-based chat experience.

---

## 🌟 Key Features

### 1. 🗄️ Firestore Plant Storage
- Direct integration with **Google Cloud Firestore** to persist houseplant inventory.
- Track plant names, species, lighting requirements, custom watering intervals (in days), last watered dates, notes, and health statuses.
- Supports reading all plants, querying specific species, adding new plant records, and updating watering timestamps.

### 2. 🚨 Watering Alert Tool
- Evaluates stored plant records against current dates and watering intervals.
- Computes whether plants are up to date, due today, or overdue (including exact days overdue).

### 3. ☀️ Open-Meteo Weather Recommendations
- Fetches live temperature, relative humidity, and weather conditions from the **Open-Meteo Geocoding & Forecast APIs**.
- Provides location-aware watering frequency adjustments (e.g., suggesting increased watering during hot/dry spells or reduced watering during cool/rainy weather).

### 4. 🎨 Gemini Image Generation
- Generates high-quality houseplant portraits and care illustrations on demand using `gemini-3.1-flash-lite-image` via the Vertex AI GenAI SDK.

### 5. ☁️ Google Cloud Storage Integration
- Automatically uploads generated plant portraits to a dedicated **Google Cloud Storage** bucket (`gs://...`).
- Serves public HTTPS image URLs directly embedded in agent responses and A2UI cards.

### 6. 🐍 Sandbox Code Execution
- Integrated with `AgentEngineSandboxCodeExecutor` to safely run Python calculation blocks in a remote sandbox environment.
- Allows the agent to compute adaptive watering intervals, mathematical adjustments, and environmental formulas safely isolated from host infrastructure.

### 7. 🧠 Vertex AI Memory Bank
- Leverages `VertexAiMemoryBankService` to store and recall long-term user preferences across sessions.
- Automatically captures durable user facts such as gardening experience level, indoor/outdoor preferences, light setup, and care routines without mixing them into Firestore plant records.

### 8. 🃏 A2UI (Agent-to-User Interface) Card Rendering
- Configured with `A2uiSchemaManager` (version 0.8) and `BasicCatalog`.
- Transforms raw text outputs into structured, visual UI components (`Card`, `Column`, `Row`, `Text`, `Image`) rendered cleanly in the chat interface via an `after_model_callback`.

### 9. 🚀 Agent Platform Deployment
- Packaged and deployed to **Vertex AI Agent Engine (Reasoning Engines)** using the Google Agent Development Kit (ADK).
- Implements the **A2A (Agent-to-Agent)** protocol for standardized API interaction.

### 10. 🌐 Cloud Run Frontend
- A clean, plant-themed frontend featuring a lightweight **FastAPI proxy** (`frontend/main.py`) and a responsive **HTML/JS chat UI** (`frontend/static/index.html`).
- Deployed to **Google Cloud Run** with IAM authentication (`roles/aiplatform.user`) for secure communication with the Reasoning Engine.

---

## 📁 Architecture & Project Structure

```
plant-care-companion/
├── app/
│   ├── agent.py               # Main ADK Agent setup, tools, memory, code executor, A2UI
│   ├── firestore_db.py        # Firestore CRUD operations for plant records & alerts
│   ├── a2ui_utils.py          # A2UI callback transformer for model output
│   └── fast_api_app.py        # FastAPI server entry point
├── frontend/
│   ├── main.py                # FastAPI proxy forwarding frontend requests over A2A
│   ├── static/
│   │   └── index.html         # Plant-themed web UI with built-in A2UI mini-renderer
│   ├── Dockerfile             # Container configuration for Cloud Run deployment
│   └── requirements.txt       # Frontend proxy dependencies
├── deployment_metadata.json   # Deployed Reasoning Engine resource metadata
├── pyproject.toml             # Python dependencies and project settings
└── README.md                  # Project documentation
```

---

## 🛠️ Setup & Configuration

### Prerequisites
- Python 3.11+
- [uv](https://docs.astral.sh/uv/) Python package manager
- `google-agents-cli` (`uv tool install google-agents-cli`)
- [Google Cloud SDK (`gcloud`)](https://cloud.google.com/sdk/docs/install) authenticated to your GCP project.

### Environment Variables
Configure the following variables in `.env` or your deployment environment:
```bash
PROJECT_ID="<your-gcp-project-id>"
BUCKET_NAME="<your-cloud-storage-bucket-name>"
AGENT_ENGINE_RESOURCE_NAME="projects/<project-number>/locations/<region>/reasoningEngines/<engine-id>"
AGENT_DIRECTORY="app"
```

---

## 🚀 Running & Testing

### 1. Local Agent Testing with ADK
Run the local ADK dev server with Memory Bank enabled:
```bash
uv run adk web . --port 8080 --allow_origins "*" --reload_agents --memory_service_uri=agentengine://<MEMORY_BANK_ID>
```

### 2. Local Frontend Proxy
Run the frontend server locally from the `frontend/` directory:
```bash
cd frontend
uv run python -m uvicorn main:app --port 8080 --host 0.0.0.0
```

### 3. Deploy Agent to Vertex AI
Deploy the reasoning engine to Agent Platform:
```bash
agents-cli deploy
```

### 4. Deploy Frontend to Cloud Run
Deploy the frontend container to Cloud Run and set environment variables:
```bash
cd frontend
gcloud run deploy plant-care-companion-frontend \
  --source . \
  --region us-central1 \
  --allow-unauthenticated \
  --set-env-vars AGENT_ENGINE_RESOURCE_NAME="<AGENT_ENGINE_RESOURCE_NAME>",AGENT_DIRECTORY="app"
```

---

## 🔒 IAM Permissions

Ensure the following IAM roles are granted:
- **Agent Service Account**: `roles/datastore.user` (Firestore access) and `roles/storage.objectAdmin` (GCS bucket image uploads).
- **Cloud Run Service Account**: `roles/aiplatform.user` (Vertex AI Reasoning Engine access).

---

## 📜 License

Licensed under the Apache License, Version 2.0.
