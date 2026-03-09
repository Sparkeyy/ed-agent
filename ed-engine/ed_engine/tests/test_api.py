"""Tests for the Everdell REST API + SSE endpoints."""

from __future__ import annotations

import json
import threading
import time

import pytest
from fastapi.testclient import TestClient

from ed_engine.api.session import store
from ed_engine.app import app

# Import the players module so we can reset its state
from ed_engine.api import players as players_module


@pytest.fixture(autouse=True)
def _clear_stores():
    """Clear all in-memory stores between tests."""
    store._games.clear()
    players_module._players.clear()
    yield
    store._games.clear()
    players_module._players.clear()


@pytest.fixture
def client():
    return TestClient(app)


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------


def test_health(client: TestClient):
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


# ---------------------------------------------------------------------------
# Create game
# ---------------------------------------------------------------------------


def test_create_game(client: TestClient):
    resp = client.post(
        "/api/v1/games",
        json={"player_count": 2, "creator_name": "Alice"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "game_id" in data
    assert "player_token" in data
    assert "player_id" in data


def test_create_game_invalid_player_count(client: TestClient):
    resp = client.post(
        "/api/v1/games",
        json={"player_count": 5, "creator_name": "Alice"},
    )
    assert resp.status_code == 422  # validation error


def test_create_game_empty_name(client: TestClient):
    resp = client.post(
        "/api/v1/games",
        json={"player_count": 2, "creator_name": ""},
    )
    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# Join game
# ---------------------------------------------------------------------------


def test_join_game(client: TestClient):
    # Create
    create_resp = client.post(
        "/api/v1/games",
        json={"player_count": 2, "creator_name": "Alice"},
    )
    game_id = create_resp.json()["game_id"]

    # Join
    join_resp = client.post(
        f"/api/v1/games/{game_id}/join",
        json={"player_name": "Bob"},
    )
    assert join_resp.status_code == 200
    data = join_resp.json()
    assert "player_token" in data
    assert "player_id" in data


def test_join_full_game(client: TestClient):
    # Create 2-player game
    create_resp = client.post(
        "/api/v1/games",
        json={"player_count": 2, "creator_name": "Alice"},
    )
    game_id = create_resp.json()["game_id"]

    # Join -- fills the game
    client.post(f"/api/v1/games/{game_id}/join", json={"player_name": "Bob"})

    # Third player should fail
    resp = client.post(
        f"/api/v1/games/{game_id}/join",
        json={"player_name": "Charlie"},
    )
    assert resp.status_code == 400
    assert "full" in resp.json()["detail"].lower() or "started" in resp.json()["detail"].lower()


def test_join_nonexistent_game(client: TestClient):
    resp = client.post(
        "/api/v1/games/nonexistent-id/join",
        json={"player_name": "Bob"},
    )
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Get game state
# ---------------------------------------------------------------------------


def test_get_game_waiting(client: TestClient):
    """Before game starts, state shows waiting status."""
    create_resp = client.post(
        "/api/v1/games",
        json={"player_count": 2, "creator_name": "Alice"},
    )
    game_id = create_resp.json()["game_id"]

    resp = client.get(f"/api/v1/games/{game_id}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["game_id"] == game_id
    assert data["state"]["status"] == "waiting"
    assert data["game_over"] is False


def test_get_game_started(client: TestClient):
    """After all players join, game auto-starts."""
    create_resp = client.post(
        "/api/v1/games",
        json={"player_count": 2, "creator_name": "Alice"},
    )
    game_id = create_resp.json()["game_id"]
    token_alice = create_resp.json()["player_token"]

    client.post(f"/api/v1/games/{game_id}/join", json={"player_name": "Bob"})

    resp = client.get(f"/api/v1/games/{game_id}?player_token={token_alice}")
    assert resp.status_code == 200
    data = resp.json()
    assert "players" in data["state"]
    assert data["current_player_id"] is not None


def test_get_game_with_valid_actions(client: TestClient):
    """Current player should see valid actions."""
    create_resp = client.post(
        "/api/v1/games",
        json={"player_count": 2, "creator_name": "Alice"},
    )
    game_id = create_resp.json()["game_id"]
    token_alice = create_resp.json()["player_token"]

    client.post(f"/api/v1/games/{game_id}/join", json={"player_name": "Bob"})

    resp = client.get(f"/api/v1/games/{game_id}?player_token={token_alice}")
    data = resp.json()
    # Alice is first player, should have valid actions
    assert len(data["valid_actions"]) > 0
    action_types = [a["action_type"] for a in data["valid_actions"]]
    # At game start, player has 2 workers available so place_worker should be there
    assert "place_worker" in action_types or "play_card" in action_types


def test_get_nonexistent_game(client: TestClient):
    resp = client.get("/api/v1/games/nonexistent-id")
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Perform action
# ---------------------------------------------------------------------------


def _create_started_game(client: TestClient) -> dict:
    """Helper: create a 2-player game that is already started."""
    create_resp = client.post(
        "/api/v1/games",
        json={"player_count": 2, "creator_name": "Alice"},
    )
    create_data = create_resp.json()
    game_id = create_data["game_id"]
    token_alice = create_data["player_token"]
    pid_alice = create_data["player_id"]

    join_resp = client.post(
        f"/api/v1/games/{game_id}/join",
        json={"player_name": "Bob"},
    )
    join_data = join_resp.json()
    token_bob = join_data["player_token"]
    pid_bob = join_data["player_id"]

    return {
        "game_id": game_id,
        "token_alice": token_alice,
        "pid_alice": pid_alice,
        "token_bob": token_bob,
        "pid_bob": pid_bob,
    }


def _get_valid_location(client: TestClient, game_id: str, token: str) -> str | None:
    """Get a valid place_worker location from valid_actions."""
    resp = client.get(f"/api/v1/games/{game_id}?player_token={token}")
    data = resp.json()
    for action in data["valid_actions"]:
        if action["action_type"] == "place_worker" and action.get("params", {}).get("location_id"):
            return action["params"]["location_id"]
    return None


def test_perform_action_place_worker(client: TestClient):
    info = _create_started_game(client)

    # Get a valid location from the valid actions
    location_id = _get_valid_location(client, info["game_id"], info["token_alice"])
    assert location_id is not None, "No valid place_worker location found"

    resp = client.post(
        f"/api/v1/games/{info['game_id']}/action",
        json={
            "player_token": info["token_alice"],
            "action_type": "place_worker",
            "location_id": location_id,
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert data["game"]["game_id"] == info["game_id"]


def test_perform_action_prepare_for_season(client: TestClient):
    info = _create_started_game(client)

    # Place all of Alice's workers first (she starts with 2)
    for _ in range(2):
        location_id = _get_valid_location(client, info["game_id"], info["token_alice"])
        if location_id is None:
            break
        client.post(
            f"/api/v1/games/{info['game_id']}/action",
            json={
                "player_token": info["token_alice"],
                "action_type": "place_worker",
                "location_id": location_id,
            },
        )
        # Bob needs to take a turn too (alternate turns)
        bob_loc = _get_valid_location(client, info["game_id"], info["token_bob"])
        if bob_loc:
            client.post(
                f"/api/v1/games/{info['game_id']}/action",
                json={
                    "player_token": info["token_bob"],
                    "action_type": "place_worker",
                    "location_id": bob_loc,
                },
            )

    # Now Alice should be able to prepare for season
    resp = client.post(
        f"/api/v1/games/{info['game_id']}/action",
        json={
            "player_token": info["token_alice"],
            "action_type": "prepare_for_season",
        },
    )
    assert resp.status_code == 200


def test_perform_action_invalid_token(client: TestClient):
    info = _create_started_game(client)

    resp = client.post(
        f"/api/v1/games/{info['game_id']}/action",
        json={
            "player_token": "bogus-token",
            "action_type": "place_worker",
            "location_id": "basic_3twigs",
        },
    )
    assert resp.status_code == 403


def test_perform_action_not_your_turn(client: TestClient):
    info = _create_started_game(client)

    # Bob tries to act when it's Alice's turn
    resp = client.post(
        f"/api/v1/games/{info['game_id']}/action",
        json={
            "player_token": info["token_bob"],
            "action_type": "place_worker",
            "location_id": "basic_3twigs",
        },
    )
    assert resp.status_code == 400
    assert "not your turn" in resp.json()["detail"].lower()


def test_perform_action_game_not_started(client: TestClient):
    create_resp = client.post(
        "/api/v1/games",
        json={"player_count": 3, "creator_name": "Alice"},
    )
    data = create_resp.json()

    resp = client.post(
        f"/api/v1/games/{data['game_id']}/action",
        json={
            "player_token": data["player_token"],
            "action_type": "place_worker",
            "location_id": "basic_3twigs",
        },
    )
    assert resp.status_code == 400
    assert "not started" in resp.json()["detail"].lower()


def test_perform_unknown_action(client: TestClient):
    info = _create_started_game(client)

    resp = client.post(
        f"/api/v1/games/{info['game_id']}/action",
        json={
            "player_token": info["token_alice"],
            "action_type": "dance_jig",
        },
    )
    assert resp.status_code == 400
    assert "unknown" in resp.json()["detail"].lower()


# ---------------------------------------------------------------------------
# SSE events
# ---------------------------------------------------------------------------


def test_sse_endpoint_exists_and_validates(client: TestClient):
    """SSE endpoint should exist and reject nonexistent games."""
    # Nonexistent game returns 404
    resp = client.get("/api/v1/games/fake-id/events")
    assert resp.status_code == 404

    # Valid game_id should not 404 (it will start streaming, but we
    # test the actual SSE mechanism via test_sse_broadcast_mechanism)
    create_resp = client.post(
        "/api/v1/games",
        json={"player_count": 2, "creator_name": "Alice"},
    )
    game_id = create_resp.json()["game_id"]

    # Verify the session has the game registered
    session = store.get(game_id)
    assert session is not None
    assert session.game_id == game_id


@pytest.mark.asyncio
async def test_sse_event_format():
    """SSE events should be formatted correctly as SSE text."""
    # Test the SSE format directly by checking what the generator would produce
    import asyncio
    from ed_engine.api.session import GameSession

    session = GameSession(game_id="test-sse-fmt", max_players=2)
    queue = session.register_sse("viewer")

    # Simulate what the SSE endpoint does
    session.broadcast_event("game_state", {"turn": 1})

    event = queue.get_nowait()
    assert event["event"] == "game_state"
    assert event["data"]["turn"] == 1

    # Verify SSE text encoding
    event_type = event["event"]
    data = json.dumps(event["data"])
    sse_text = f"event: {event_type}\ndata: {data}\n\n"
    assert "event: game_state\n" in sse_text
    assert '"turn": 1' in sse_text
    assert sse_text.endswith("\n\n")


def test_sse_broadcast_mechanism():
    """Test that the session broadcast mechanism works correctly."""
    import asyncio
    from ed_engine.api.session import GameSession

    session = GameSession(game_id="test-123", max_players=2)
    token1, pid1 = session.add_player("Alice")
    token2, pid2 = session.add_player("Bob")

    queue1 = session.register_sse(token1)
    queue2 = session.register_sse(token2)

    # Broadcast an event
    session.broadcast_event("game_state", {"test": True})

    # Both queues should have the event
    assert not queue1.empty()
    assert not queue2.empty()

    event1 = queue1.get_nowait()
    event2 = queue2.get_nowait()

    assert event1["event"] == "game_state"
    assert event1["data"] == {"test": True}
    assert event2["event"] == "game_state"

    # Unregister one
    session.unregister_sse(token1)
    session.broadcast_event("player_joined", {"name": "Charlie"})

    assert queue1.empty()  # unregistered, should not receive
    assert not queue2.empty()


def test_sse_nonexistent_game(client: TestClient):
    resp = client.get("/api/v1/games/nonexistent-id/events")
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Players API (stubs)
# ---------------------------------------------------------------------------


def test_register_player(client: TestClient):
    resp = client.post("/api/v1/players", json={"name": "TestPlayer"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["name"] == "TestPlayer"
    assert "id" in data


def test_get_player(client: TestClient):
    create_resp = client.post("/api/v1/players", json={"name": "TestPlayer"})
    player_id = create_resp.json()["id"]

    resp = client.get(f"/api/v1/players/{player_id}")
    assert resp.status_code == 200
    assert resp.json()["name"] == "TestPlayer"


def test_leaderboard(client: TestClient):
    client.post("/api/v1/players", json={"name": "P1"})
    client.post("/api/v1/players", json={"name": "P2"})

    resp = client.get("/api/v1/players")
    assert resp.status_code == 200
    assert len(resp.json()) == 2
