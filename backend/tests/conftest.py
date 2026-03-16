import os

os.environ["DATABASE_URL"] = "sqlite+pysqlite:///:memory:"

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from api.auth import router as auth_router
from api.recommendations import router as recommendations_router
from api.users import router as users_router
from api.usage import router as usage_router
from data.database import Base
from data.session import get_db
from models.cards import Card
from models.reward_rules import RewardRule
from models.user_cards import UserCard
from models.users import User
from models.spend_tracker import SpendTracker


@pytest.fixture()
def auth_headers(monkeypatch):
    def _verify_id_token(_: str):
        return {
            "uid": "firebase-user-123",
            "email": "user@example.com",
            "firebase": {"sign_in_provider": "google.com"},
        }

    monkeypatch.setattr("auth.firebase_auth.verify_id_token", _verify_id_token)
    return {"Authorization": "Bearer fake-firebase-token"}


@pytest.fixture()
def test_sessionmaker():
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    try:
        yield SessionLocal
    finally:
        engine.dispose()


@pytest.fixture()
def client(test_sessionmaker):
    app = FastAPI()
    app.include_router(auth_router)
    app.include_router(recommendations_router)
    app.include_router(users_router)
    app.include_router(usage_router)

    @app.get("/health")
    def health():
        return {"ok": True}

    def override_get_db():
        db = test_sessionmaker()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture()
def seeded_data(test_sessionmaker):
    db = test_sessionmaker()
    try:
        top_card = Card(
            issuer="Top Bank",
            name="Top Dining",
            network="Visa",
            annual_fee=95,
            fx_fee_bps=0,
            is_active=True,
        )
        base_card = Card(
            issuer="Base Bank",
            name="Base Everyday",
            network="Mastercard",
            annual_fee=0,
            fx_fee_bps=300,
            is_active=True,
        )
        db.add_all([top_card, base_card])
        db.flush()

        rules = [
                RewardRule(
                    card_id=top_card.id,
                    category="DINING",
                    channel="ANY",
                    country="US",
                    multiplier=3.0,
                    flat_points=0,
                    priority=10,
                    is_active=True,
                ),
                RewardRule(
                    card_id=base_card.id,
                    category="DINING",
                    channel="ANY",
                    country="ANY",
                    multiplier=2.0,
                    flat_points=0,
                    cap_amount=500.0,
                    cap_period="MONTHLY",
                    priority=20,
                    is_active=True,
                ),
                RewardRule(
                    card_id=top_card.id,
                    category="OTHER",
                    channel="ANY",
                    country="US",
                    multiplier=1.0,
                    flat_points=0,
                    priority=100,
                    is_active=True,
                ),
                RewardRule(
                    card_id=base_card.id,
                    category="OTHER",
                    channel="ANY",
                    country="US",
                    multiplier=1.0,
                    flat_points=0,
                    priority=100,
                    is_active=True,
                ),
            ]
        db.add_all(rules)

        user = User(email="user@example.com")
        db.add(user)
        db.flush()

        db.add(UserCard(user_id=user.id, card_id=base_card.id, nickname="Wallet Card", is_active=True))
        db.commit()

        top_dining_rule = next(r for r in rules if r.card_id == top_card.id and r.category == "DINING")
        base_dining_rule = next(r for r in rules if r.card_id == base_card.id and r.category == "DINING")

        return {
            "top_card_id": top_card.id,
            "base_card_id": base_card.id,
            "user_id": user.id,
            "top_dining_rule_id": top_dining_rule.id,
            "base_dining_rule_id": base_dining_rule.id,
        }
    finally:
        db.close()
