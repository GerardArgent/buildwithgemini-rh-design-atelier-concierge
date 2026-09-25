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

import time
from typing import Any, Dict, List, Optional
from google import genai
from google.cloud import firestore, storage
from google.adk.agents import Agent
from google.adk.agents.context import Context
from google.adk.apps import App
from google.adk.models import Gemini
from google.adk.tools import google_search
from google.genai import types

MODEL = "gemini-3.6-flash"
IMAGE_MODEL = "gemini-3.1-flash-lite-image"

# Hardcoded GCP resources
PROJECT_ID = "qwiklabs-gcp-03-b12e4132c215"
COLLECTION_NAME = "rh_products"
BUCKET_NAME = "rh-atelier-catalog-5142"


def _get_db() -> firestore.Client:
    return firestore.Client(project=PROJECT_ID)


def _get_storage_bucket() -> storage.Bucket:
    client = storage.Client(project=PROJECT_ID)
    return client.bucket(BUCKET_NAME)


def list_products(
    category: Optional[str] = None,
    room: Optional[str] = None,
    in_stock_only: bool = False,
) -> List[Dict[str, Any]]:
    """List or search products in the RH catalog.

    Args:
        category: Optional category filter (e.g. 'Living', 'Dining', 'Lighting', 'Bedroom').
        room: Optional room filter (e.g. 'Living Room', 'Dining Room', 'Bedroom').
        in_stock_only: If True, only returns items currently in stock.

    Returns:
        A list of product dictionaries matching the criteria.
    """
    db = _get_db()
    query = db.collection(COLLECTION_NAME)

    if category:
        query = query.where("category", "==", category)
    if room:
        query = query.where("room", "==", room)
    if in_stock_only:
        query = query.where("in_stock", "==", True)

    docs = query.stream()
    results = []
    for doc in docs:
        data = doc.to_dict()
        results.append(data)
    return results


def get_product_details(product_id: str) -> Dict[str, Any]:
    """Retrieve full details for a specific RH product by its ID or slug.

    Args:
        product_id: The unique ID or slug of the product (e.g. 'cloud-sofa-classic').

    Returns:
        The product details dictionary if found, or an error message dict.
    """
    db = _get_db()
    doc_ref = db.collection(COLLECTION_NAME).document(product_id)
    doc = doc_ref.get()
    if not doc.exists:
        return {"error": f"Product with ID '{product_id}' was not found in the catalog."}
    return doc.to_dict()


def save_product(
    product_id: str,
    name: str,
    category: str,
    room: str,
    style: str,
    material: str,
    finish_color: str,
    dimensions: str,
    regular_price: int,
    member_price: int,
    in_stock: bool = True,
    lead_time_weeks: int = 2,
    description: str = "",
) -> Dict[str, Any]:
    """Add or update an RH product in the Firestore catalog.

    Args:
        product_id: Unique slug/identifier for the product (e.g., 'strada-round-chandelier').
        name: Full product name.
        category: Broad category (e.g., 'Living', 'Dining', 'Lighting', 'Bedroom', 'Outdoor').
        room: Intended room (e.g., 'Living Room', 'Dining Room', 'Bedroom').
        style: Aesthetic style (e.g., 'Modern Minimalist', 'French Contemporary', 'Modern Classic').
        material: Primary material (e.g., 'Belgian Linen', 'Reclaimed Oak', 'Italian Leather').
        finish_color: Color or finish designation (e.g., 'Burnished Brass', 'Natural Salvaged').
        dimensions: Dimensions description (e.g., '84"W x 45"D x 31.5"H').
        regular_price: Standard retail price in USD.
        member_price: RH Member price in USD (typically ~20-25% off regular).
        in_stock: Whether the item is immediately available.
        lead_time_weeks: Estimated delivery / crafting lead time in weeks.
        description: Detailed product narrative.

    Returns:
        A confirmation dict with the saved product details.
    """
    db = _get_db()
    data = {
        "id": product_id,
        "name": name,
        "category": category,
        "room": room,
        "style": style,
        "material": material,
        "finish_color": finish_color,
        "dimensions": dimensions,
        "regular_price": regular_price,
        "member_price": member_price,
        "in_stock": in_stock,
        "lead_time_weeks": lead_time_weeks,
        "description": description,
    }
    db.collection(COLLECTION_NAME).document(product_id).set(data)
    return {"status": "success", "message": f"Product '{name}' successfully saved.", "product": data}


async def generate_product_image(
    prompt: str,
    filename: Optional[str] = None,
    previous_artifact_name: Optional[str] = None,
    tool_context: Optional[Context] = None,
) -> Dict[str, Any]:
    """Generate or update an image for an RH furniture piece or room scene using gemini-3.1-flash-lite-image.

    If previous_artifact_name is provided, this tool will load the existing image artifact and edit/update it
    according to prompt (e.g. changing the fabric, color, finish, or styling).
    The generated image is saved as an artifact in the session and uploaded to public Cloud Storage.

    Args:
        prompt: Detailed description of the RH furniture or styling request (e.g. 'A luxury RH Cloud sofa in Belgian linen white in a bright minimalist living room' or 'Change the sofa upholstery finish to burnished charcoal leather').
        filename: Optional name for the output image file (e.g. 'rh_cloud_sofa.jpg'). If omitted, one is generated automatically.
        previous_artifact_name: Optional name of a previously saved artifact in this session to update or colorize/re-finish.
        tool_context: Execution context provided automatically by the ADK framework.

    Returns:
        A dictionary containing the public image URL, artifact filename, and status.
    """
    timestamp = int(time.time())
    if not filename:
        clean_prompt = "".join(c if c.isalnum() else "_" for c in prompt[:24]).strip("_")
        filename = f"rh_image_{clean_prompt}_{timestamp}.jpg"
    elif not filename.lower().endswith((".jpg", ".jpeg", ".png")):
        filename = f"{filename}.jpg"

    genai_client = genai.Client(
        vertexai=True,
        project=PROJECT_ID,
        location="global",
    )

    contents: List[Any] = []

    # Check if this is an image edit/update request based on a previous artifact
    if previous_artifact_name and tool_context:
        try:
            prev_part = await tool_context.load_artifact(filename=previous_artifact_name)
            if prev_part and hasattr(prev_part, "inline_data") and prev_part.inline_data:
                contents.append(
                    types.Part.from_bytes(
                        data=prev_part.inline_data.data,
                        mime_type=prev_part.inline_data.mime_type or "image/jpeg",
                    )
                )
        except Exception as e:
            pass

    contents.append(prompt)

    # Call gemini-3.1-flash-lite-image in global region
    response = genai_client.models.generate_content(
        model=IMAGE_MODEL,
        contents=contents,
    )

    candidate = response.candidates[0]
    image_part = None
    for part in candidate.content.parts:
        if hasattr(part, "inline_data") and part.inline_data and part.inline_data.mime_type.startswith("image/"):
            image_part = part
            break

    if not image_part:
        return {"error": "Model did not return image data."}

    image_bytes = image_part.inline_data.data
    mime_type = image_part.inline_data.mime_type or "image/jpeg"

    # 1. Save with tool_context.save_artifact so it shows in Playground Artifacts panel
    if tool_context:
        try:
            artifact_part = types.Part.from_bytes(data=image_bytes, mime_type=mime_type)
            await tool_context.save_artifact(
                filename=filename,
                artifact=artifact_part,
                custom_metadata={"prompt": prompt, "model": IMAGE_MODEL, "timestamp": timestamp},
            )
        except Exception as e:
            pass

    # 2. Upload to public Cloud Storage bucket and return public URL
    bucket = _get_storage_bucket()
    blob = bucket.blob(filename)
    blob.upload_from_string(image_bytes, content_type=mime_type)

    public_url = f"https://storage.googleapis.com/{BUCKET_NAME}/{filename}"

    return {
        "status": "success",
        "public_url": public_url,
        "artifact_filename": filename,
        "prompt": prompt,
        "message": f"Image successfully generated and uploaded to {public_url}",
    }


from google.adk.code_executors.agent_engine_sandbox_code_executor import AgentEngineSandboxCodeExecutor
from google.adk.tools.preload_memory_tool import PreloadMemoryTool
from google.adk.agents.callback_context import CallbackContext
from google.adk.memory import VertexAiMemoryBankService

# Agent Engine & Memory Bank resources from deployment_metadata.json
AGENT_ENGINE_ID = "6969379796983742464"
AGENT_ENGINE_LOCATION = "us-east1"
AGENT_ENGINE_RESOURCE = f"projects/566235946140/locations/{AGENT_ENGINE_LOCATION}/reasoningEngines/{AGENT_ENGINE_ID}"
SANDBOX_RESOURCE_NAME = f"{AGENT_ENGINE_RESOURCE}/sandboxEnvironments/4552136468667039744"

sandbox_executor = AgentEngineSandboxCodeExecutor(
    sandbox_resource_name=SANDBOX_RESOURCE_NAME,
    agent_engine_resource_name=AGENT_ENGINE_RESOURCE,
)


# WRITE: after each turn, send the session to Memory Bank for extraction.
async def generate_memories_callback(callback_context: CallbackContext):
    try:
        await callback_context.add_session_to_memory()
    except (ValueError, Exception):
        pass
    return None


# Memory service builder for deployed Agent Runtime
def memory_bank_service_builder():
    return VertexAiMemoryBankService(
        project=PROJECT_ID,
        location=AGENT_ENGINE_LOCATION,
        agent_engine_id=AGENT_ENGINE_ID,
    )


from a2ui.schema.manager import A2uiSchemaManager
from a2ui.basic_catalog.provider import BasicCatalog
from .a2ui_utils import a2ui_callback

# Build A2UI v0.8 Schema Prompt with Basic Catalog
schema_manager = A2uiSchemaManager(
    version="0.8",
    catalogs=[BasicCatalog.get_config("0.8")],
)

a2ui_instruction = schema_manager.generate_system_prompt(
    role_description=(
        "You are the RH Design Atelier Concierge, a luxury interior design and furnishing assistant "
        "supporting clients on rh.com. You help clients discover, inspect, configure, and visualize luxury furniture, "
        "architectural lighting, and styled room spaces. You remember the client's stated preferences, past selections, "
        "aesthetic tastes, and room dimensions across conversations to deliver a tailored atelier experience."
    ),
    workflow_description=(
        "Analyze the client's request. Query the RH Firestore catalog, perform web searches, generate visualized pieces, "
        "or compute room clearance dimensions as needed. When presenting furniture recommendations, catalog items, "
        "or room configurations, return structured UI when appropriate."
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
        '{"Image": {"url": {"literalString": "https://..."}}}. Never point an '
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
        model=MODEL,
        retry_options=types.HttpRetryOptions(attempts=3),
    ),
    code_executor=sandbox_executor,
    instruction=a2ui_instruction,
    tools=[
        PreloadMemoryTool(),
        list_products,
        get_product_details,
        save_product,
        google_search,
        generate_product_image,
    ],
    after_agent_callback=generate_memories_callback,
    after_model_callback=a2ui_callback,
)

app = App(
    root_agent=root_agent,
    name="app",
)


