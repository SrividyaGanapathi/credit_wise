from .database import Base, engine
from models.users import User
from models.cards import Card
from models.reward_rules import RewardRule
from models.user_card import UserCard


def init_db() -> None:
    Base.metadata.create_all(bind=engine)
