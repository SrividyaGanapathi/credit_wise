def test_health(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"ok": True}


def test_recommend_picks_highest_scoring_card(client, seeded_data):
    response = client.post(
        "/recommend",
        json={
            "amount": 100,
            "category": "restaurants",
            "channel": "in store",
            "country": "United States of America",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["best_card"]["card_id"] == seeded_data["top_card_id"]
    assert payload["best_card"]["score"] == 300.0
    assert payload["best_card"]["net_value"] == 300.0
    assert len(payload["top_3"]) == 2
    assert payload["top_3"][0]["net_value"] >= payload["top_3"][1]["net_value"]
    assert len(payload["explanations"]) > 0


def test_recommend_respects_user_wallet_filter(client, seeded_data):
    response = client.post(
        "/recommend",
        json={
            "amount": 50,
            "category": "dining",
            "channel": "online",
            "country": "US",
            "user_id": seeded_data["user_id"],
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["best_card"]["card_id"] == seeded_data["base_card_id"]
    assert len(payload["top_3"]) == 1


def test_auth_login_is_idempotent(client):
    first = client.post("/auth/login", json={"email": "repeat@example.com"})
    second = client.post("/auth/login", json={"email": "repeat@example.com"})

    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json()["message"] == second.json()["message"]


def test_usage_log_creates_and_accumulates_spend(client, seeded_data):
    payload = {
        "user_id": seeded_data["user_id"],
        "rule_id": seeded_data["base_dining_rule_id"],
        "amount": 120,
        "period_start": "2026-03-01",
    }

    first = client.post("/usage/log", json=payload)
    assert first.status_code == 200
    first_body = first.json()
    assert first_body["spent_amount"] == 120.0
    assert first_body["cap_amount"] == 500.0
    assert first_body["cap_remaining"] == 380.0

    second = client.post("/usage/log", json={**payload, "amount": 50})
    assert second.status_code == 200
    second_body = second.json()
    assert second_body["id"] == first_body["id"]
    assert second_body["spent_amount"] == 170.0
    assert second_body["cap_remaining"] == 330.0


def test_recommend_applies_cap_exhaustion_for_user_usage(client, seeded_data):
    usage = client.post(
        "/usage/log",
        json={
            "user_id": seeded_data["user_id"],
            "rule_id": seeded_data["base_dining_rule_id"],
            "amount": 500,
        },
    )
    assert usage.status_code == 200
    assert usage.json()["cap_remaining"] == 0.0

    response = client.post(
        "/recommend",
        json={
            "amount": 100,
            "category": "dining",
            "channel": "online",
            "country": "US",
            "user_id": seeded_data["user_id"],
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["best_card"]["card_id"] == seeded_data["base_card_id"]
    assert payload["best_card"]["score"] == 100.0
    assert payload["best_card"]["net_value"] == 100.0
    assert payload["best_card"]["cap_remaining"] == 0.0
    assert any("exhausted" in warning.lower() for warning in payload["best_card"]["warnings"])


def test_recommend_applies_fx_fee_to_net_value(client, seeded_data):
    response = client.post(
        "/recommend",
        json={
            "amount": 100,
            "category": "dining",
            "channel": "online",
            "country": "IN",
            "user_id": seeded_data["user_id"],
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["best_card"]["card_id"] == seeded_data["base_card_id"]
    assert payload["best_card"]["score"] == 200.0
    assert payload["best_card"]["net_value"] == 197.0
    assert any("fx fee" in warning.lower() for warning in payload["best_card"]["warnings"])


def test_recommend_handles_partial_cap_for_user_usage(client, seeded_data):
    usage = client.post(
        "/usage/log",
        json={
            "user_id": seeded_data["user_id"],
            "rule_id": seeded_data["base_dining_rule_id"],
            "amount": 450,
        },
    )
    assert usage.status_code == 200
    assert usage.json()["cap_remaining"] == 50.0

    response = client.post(
        "/recommend",
        json={
            "amount": 100,
            "category": "dining",
            "channel": "online",
            "country": "US",
            "user_id": seeded_data["user_id"],
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["best_card"]["card_id"] == seeded_data["base_card_id"]
    assert payload["best_card"]["score"] == 150.0
    assert payload["best_card"]["net_value"] == 150.0
    assert payload["best_card"]["cap_remaining"] == 0.0
    assert any("part of the transaction qualifies" in w.lower() for w in payload["best_card"]["warnings"])


def test_usage_log_returns_404_for_unknown_user(client, seeded_data):
    response = client.post(
        "/usage/log",
        json={
            "user_id": 999999,
            "rule_id": seeded_data["base_dining_rule_id"],
            "amount": 25,
        },
    )
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


def test_usage_log_returns_404_for_unknown_rule(client, seeded_data):
    response = client.post(
        "/usage/log",
        json={
            "user_id": seeded_data["user_id"],
            "rule_id": 999999,
            "amount": 25,
        },
    )
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


def test_usage_log_rolls_over_by_period(client, seeded_data):
    first_period = client.post(
        "/usage/log",
        json={
            "user_id": seeded_data["user_id"],
            "rule_id": seeded_data["base_dining_rule_id"],
            "amount": 200,
            "period_start": "2026-03-01",
        },
    )
    assert first_period.status_code == 200
    first = first_period.json()
    assert first["spent_amount"] == 200.0
    assert first["cap_remaining"] == 300.0

    second_period = client.post(
        "/usage/log",
        json={
            "user_id": seeded_data["user_id"],
            "rule_id": seeded_data["base_dining_rule_id"],
            "amount": 150,
            "period_start": "2026-04-01",
        },
    )
    assert second_period.status_code == 200
    second = second_period.json()
    assert second["id"] != first["id"]
    assert second["spent_amount"] == 150.0
    assert second["cap_remaining"] == 350.0

    second_period_again = client.post(
        "/usage/log",
        json={
            "user_id": seeded_data["user_id"],
            "rule_id": seeded_data["base_dining_rule_id"],
            "amount": 50,
            "period_start": "2026-04-01",
        },
    )
    assert second_period_again.status_code == 200
    second_again = second_period_again.json()
    assert second_again["id"] == second["id"]
    assert second_again["spent_amount"] == 200.0
    assert second_again["cap_remaining"] == 300.0
