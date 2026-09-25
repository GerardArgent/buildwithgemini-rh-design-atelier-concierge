#!/usr/bin/env python3
"""Seed script for RH Design Atelier Concierge product collection in Firestore."""

from google.cloud import firestore

PROJECT_ID = "qwiklabs-gcp-03-b12e4132c215"
COLLECTION_NAME = "rh_products"

SAMPLE_PRODUCTS = [
    {
        "id": "cloud-sofa-classic",
        "name": "Cloud Classic Slipcovered Sofa",
        "collection": "Cloud",
        "category": "Living",
        "room": "Living Room",
        "style": "Modern Classic",
        "material": "Belgian Linen",
        "finish_color": "Perennials Classic Linen White",
        "dimensions": "84\"W x 45\"D x 31.5\"H",
        "regular_price": 5495,
        "member_price": 4121,
        "in_stock": True,
        "lead_time_weeks": 2,
        "description": "The world's most comfortable sofa, featuring down-filled cushions and artisan hand-tailored Belgian linen slipcovers.",
    },
    {
        "id": "salvaged-wood-trestle-table",
        "name": "Salvaged Wood Trestle Dining Table",
        "collection": "Salvaged Wood",
        "category": "Dining",
        "room": "Dining Room",
        "style": "Industrial Rustic",
        "material": "Reclaimed Solid Pine",
        "finish_color": "Natural Salvaged",
        "dimensions": "96\"L x 40\"W x 30\"H",
        "regular_price": 4295,
        "member_price": 3221,
        "in_stock": True,
        "lead_time_weeks": 4,
        "description": "Crafted from uncommitted timbers reclaimed from century-old American buildings, each table is unique with hand-hewn character.",
    },
    {
        "id": "french-barrel-chair",
        "name": "1940s French Barrel Leather Chair",
        "collection": "French Contemporary",
        "category": "Living",
        "room": "Living Room",
        "style": "French Contemporary",
        "material": "Italian Berkshire Leather",
        "finish_color": "Burnished Walnut Leather",
        "dimensions": "32\"W x 34\"D x 30\"H",
        "regular_price": 3195,
        "member_price": 2396,
        "in_stock": True,
        "lead_time_weeks": 1,
        "description": "Inspired by 1940s French salon club chairs, upholstered in supple full-grain Italian leather that patinas gracefully.",
    },
    {
        "id": "harlow-crystal-chandelier",
        "name": "Harlow Linear Crystal Chandelier",
        "collection": "Harlow",
        "category": "Lighting",
        "room": "Dining / Great Room",
        "style": "Art Deco Modern",
        "material": "Hand-Cut K9 Crystal & Brass",
        "finish_color": "Lacquered Burnished Brass",
        "dimensions": "60\"L x 18\"W x 24\"H",
        "regular_price": 4895,
        "member_price": 3671,
        "in_stock": False,
        "lead_time_weeks": 6,
        "description": "Precision-faceted prism crystals suspended from a solid brass geometric frame evoke 1920s Parisian glamor.",
    },
    {
        "id": "reclaimed-oak-platform-bed",
        "name": "Russian Oak Platform Bed with Headboard",
        "collection": "Russian Oak",
        "category": "Bedroom",
        "room": "Bedroom",
        "style": "Architectural Minimalist",
        "material": "Reclaimed Russian White Oak",
        "finish_color": "Black Oak Drift",
        "dimensions": "King: 86\"W x 92\"L x 48\"H",
        "regular_price": 5895,
        "member_price": 4421,
        "in_stock": True,
        "lead_time_weeks": 3,
        "description": "Bold cantilevered proportions celebrate the dramatic grain, knots, and splits of reclaimed Russian oak timbers.",
    },
]


def seed():
    print(f"Connecting to Firestore for project '{PROJECT_ID}'...")
    db = firestore.Client(project=PROJECT_ID)
    col = db.collection(COLLECTION_NAME)

    for item in SAMPLE_PRODUCTS:
        doc_id = item["id"]
        doc_ref = col.document(doc_id)
        doc_ref.set(item)
        print(f"  ✓ Seeded {doc_id}: {item['name']}")

    print(f"\nSuccessfully seeded {len(SAMPLE_PRODUCTS)} products into '{COLLECTION_NAME}' collection!")


if __name__ == "__main__":
    seed()
