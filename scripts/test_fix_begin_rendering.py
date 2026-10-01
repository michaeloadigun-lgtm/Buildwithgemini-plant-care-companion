# ruff: noqa
import json
import re
from google.genai import types
from google.adk.models.llm_response import LlmResponse

from app.a2ui_utils import _A2UI_KEYS, _TAG_RE, _iter_json_values, _surface_is_renderable, _wrap_a2ui_part

gemini_raw_output = """<a2ui-json>
  {
    "surfaceId": "monstera_care_card",
    "components": [
      {
        "id": "monstera_card",
        "component": {
          "Card": {
            "child": "monstera_column"
          }
        }
      },
      {
        "id": "monstera_column",
        "component": {
          "Column": {
            "children": {
              "explicitList": [
                "monstera_name",
                "monstera_status"
              ]
            }
          }
        }
      },
      {
        "id": "monstera_name",
        "component": {
          "Text": {
            "text": {
              "literalString": "Monstera Deliciosa"
            },
            "usageHint": "h2"
          }
        }
      },
      {
        "id": "monstera_status",
        "component": {
          "Text": {
            "text": {
              "literalString": "Status: Healthy"
            },
            "usageHint": "body"
          }
        }
      }
    ]
  }
</a2ui-json>"""

def _extract_a2ui_messages_enhanced(text: str) -> list[dict]:
    # Strip markdown fences.
    if text.startswith("```"):
        text = text.split("\n", 1)[-1]
        if text.endswith("```"):
            text = text[:-3]
    # Strip any wrapper tags so the JSON scanner sees clean payload.
    text = _TAG_RE.sub("", text).strip()

    values: list = []
    for value in _iter_json_values(text):
        if isinstance(value, list):
            values.extend(value)
        else:
            values.append(value)

    messages: list[dict] = []
    for value in values:
        if not isinstance(value, dict):
            continue
        # Unwrap {"kind":"data","data":{...}} envelopes the model may imitate.
        inner = value.get("data")
        if isinstance(inner, dict) and any(k in inner for k in _A2UI_KEYS):
            messages.append(inner)
        elif any(k in value for k in _A2UI_KEYS):
            messages.append(value)
        elif "components" in value or "surfaceId" in value:
            # Model emitted raw surfaceUpdate body without outer "surfaceUpdate" key
            messages.append({"surfaceUpdate": value})

    # Synthesize beginRendering if missing
    has_begin = any("beginRendering" in m for m in messages)
    if not has_begin:
        surface_msg = None
        for m in messages:
            if "surfaceUpdate" in m:
                surface_msg = m["surfaceUpdate"]
                break
        if surface_msg and isinstance(surface_msg, dict):
            surface_id = surface_msg.get("surfaceId", "default_surface")
            components = surface_msg.get("components") or []
            root_id = None
            for c in components:
                if isinstance(c, dict) and isinstance(c.get("component"), dict):
                    if "Card" in c["component"]:
                        root_id = c.get("id")
                        break
            if not root_id and components:
                root_id = components[0].get("id")
            if root_id:
                begin_msg = {"beginRendering": {"root": root_id, "surfaceId": surface_id}}
                messages = [begin_msg] + messages

    return messages

msgs = _extract_a2ui_messages_enhanced(gemini_raw_output)
print("Extracted messages count with enhanced parser:", len(msgs))
print("Messages:", json.dumps(msgs, indent=2))
print("Is renderable:", _surface_is_renderable(msgs))

wrapped = [_wrap_a2ui_part(m) for m in msgs]
print("Successfully created wrapped parts count:", len(wrapped))
