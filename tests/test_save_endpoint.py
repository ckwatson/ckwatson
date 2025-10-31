import json
import os
from pathlib import Path

import pytest

from web.main import AUTH_CODE, app, limiter


@pytest.fixture()
def client(tmp_path, monkeypatch):
    # Redirect puzzles directory to a temp path for isolation
    monkeypatch.chdir(tmp_path)
    (tmp_path / "puzzles").mkdir()
    app.config["TESTING"] = True
    # Disable rate limiting for this test module to avoid hitting 5/min limit
    try:
        limiter.enabled = False  # type: ignore[attr-defined]
    except Exception:
        app.config["RATELIMIT_ENABLED"] = False
    with app.test_client() as c:
        yield c


def minimal_payload(**overrides):
    base = {
        "auth_code": AUTH_CODE,
        "puzzleName": "TestPuzzle",
        "reactions": [["A", "B", "C", ""]],
        "speciesNames": ["A", "B", "C"],
        "speciesIfReactants": [True, True, False],
        "speciesEnergies": [10.0, 12.0, 5.0],
        "reagentPERs": {"A": [True], "B": [False]},
    }
    base.update(overrides)
    return base


def post(client, payload):
    return client.post(
        "/save", data=json.dumps(payload), content_type="application/json"
    )


def test_successful_save(client):
    r = post(client, minimal_payload())
    data = r.get_json()
    assert data["status"] == "success"
    assert (Path("puzzles") / "TestPuzzle.json").exists()


def test_duplicate_save_rejected(client):
    post(client, minimal_payload())
    r = post(client, minimal_payload())
    assert r.get_json()["status"] == "danger"


def test_invalid_name(client):
    r = post(client, minimal_payload(puzzleName="../Bad"))
    assert r.get_json()["status"] == "danger"


def test_length_mismatch(client):
    r = post(client, minimal_payload(speciesIfReactants=[True]))
    assert r.get_json()["status"] == "danger"


def test_per_length_mismatch(client):
    r = post(client, minimal_payload(reagentPERs={"A": [True, False]}))
    assert r.get_json()["status"] == "danger"


def test_unknown_species_in_reaction(client):
    r = post(client, minimal_payload(reactions=[["A", "X", "C", ""]]))
    assert r.get_json()["status"] == "danger"


def test_too_many_species(client):
    big_species = [f"S{i}" for i in range(51)]
    energies = [float(i) for i in range(51)]
    ifReact = [True] * 51
    reactions = [
        [big_species[0], big_species[1], big_species[2], big_species[3]]
    ]  # still one reaction
    reagentPERs = {big_species[0]: [True]}
    r = post(
        client,
        minimal_payload(
            speciesNames=big_species,
            speciesIfReactants=ifReact,
            speciesEnergies=energies,
            reactions=reactions,
            reagentPERs=reagentPERs,
        ),
    )
    assert r.get_json()["status"] == "danger"
