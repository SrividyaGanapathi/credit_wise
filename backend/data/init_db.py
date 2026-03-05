from .database import Base, engine
from models.users import User

def init_db() -> None:
    Base.metadata.create_all(bind=engine)