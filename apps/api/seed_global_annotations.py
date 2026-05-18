#!/usr/bin/env python3
"""
Seed a small number of generic example annotations so a fresh install has
something to render in the annotation timeline.

Run once: python3 apps/api/seed_global_annotations.py

Replace, extend, or delete these entries to suit your own deployment.
"""

import sys
sys.path.insert(0, ".")

ANNOTATIONS = [
    {
        "title": "Initial deploy",
        "summary": "First production deploy of NousViz on this server.",
        "description": "An example annotation. Annotations tag points in time so widget charts can correlate spikes / dips with known events. Replace this entry with your own real events.",
        "scope": "global",
        "vendor": "nousviz",
        "start_time": "2026-01-01T00:00:00Z",
        "end_time": None,
        "products": [],
        "categories": ["deploy"],
        "industries": [],
        "tags": ["deploy", "release"],
        "related_plugins": [],
        "related_datasets": [],
        "sources": [],
    },
    {
        "title": "Quarterly review window",
        "summary": "Demo annotation spanning a typical reporting window.",
        "description": "Demonstrates a multi-day annotation range. Use ranges to mark campaigns, incident windows, freeze periods, or any other interval that should overlay on dashboards.",
        "scope": "global",
        "vendor": "nousviz",
        "start_time": "2026-03-01T00:00:00Z",
        "end_time": "2026-03-31T00:00:00Z",
        "products": [],
        "categories": ["business"],
        "industries": [],
        "tags": ["reporting"],
        "related_plugins": [],
        "related_datasets": [],
        "sources": [],
    },
]


def main():
    import requests

    print(f"Seeding {len(ANNOTATIONS)} example annotations...")

    for ann in ANNOTATIONS:
        try:
            res = requests.post("http://localhost:8000/api/global-annotations", json=ann)
            data = res.json()
            annotation = data.get("annotation", data)
            slug = annotation.get("slug", "?")
            warnings = data.get("duplicate_warnings", [])
            print(f"  - {slug}")
            if warnings:
                print(f"    duplicate warnings: {[w['title'] for w in warnings]}")
        except Exception as e:
            print(f"  failed: {e}")

    print("Done.")


if __name__ == "__main__":
    main()
