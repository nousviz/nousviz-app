"""Entitlement contract validation (MC-001).

Proves the contract in contracts/ holds: the schema is valid JSON Schema
(draft 2020-12), every tier fixture validates against it, and the
additive-only promise works — a document with fields this consumer has
never seen must still validate.
"""
import copy
import json
from pathlib import Path

import pytest

jsonschema = pytest.importorskip("jsonschema")

CONTRACTS = Path(__file__).resolve().parent.parent / "contracts"
TIERS = ["free", "starter", "team", "business", "enterprise"]


def _load(name: str) -> dict:
    return json.loads((CONTRACTS / name).read_text())


@pytest.fixture(scope="module")
def schema() -> dict:
    return _load("entitlement.schema.json")


@pytest.fixture(scope="module")
def validator(schema):
    return jsonschema.Draft202012Validator(schema)


def test_schema_is_valid_json_schema(schema):
    jsonschema.Draft202012Validator.check_schema(schema)


@pytest.mark.parametrize("tier", TIERS)
def test_tier_fixture_validates(validator, tier):
    fixture = _load(f"entitlement.example.{tier}.json")
    validator.validate(fixture)
    assert fixture["tier"] == tier


def test_unknown_fields_are_tolerated(validator):
    # The forward-compat promise: a newer producer may add top-level
    # fields and feature flags this consumer has never heard of.
    fixture = copy.deepcopy(_load("entitlement.example.team.json"))
    fixture["a_field_from_the_future"] = {"anything": True}
    fixture["features"]["some_future_feature"] = True
    validator.validate(fixture)


def test_invalid_document_is_rejected(validator):
    fixture = copy.deepcopy(_load("entitlement.example.starter.json"))
    fixture["limits"]["max_users"] = "many"
    with pytest.raises(jsonschema.ValidationError):
        validator.validate(fixture)


def test_missing_required_block_is_rejected(validator):
    fixture = copy.deepcopy(_load("entitlement.example.starter.json"))
    del fixture["limits"]
    with pytest.raises(jsonschema.ValidationError):
        validator.validate(fixture)
