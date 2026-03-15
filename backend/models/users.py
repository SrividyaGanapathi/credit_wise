from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column
from data.database import Base
from typing import Optional

class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(String, unique=True, index=True)
    firebase_uid: Mapped[Optional[str]] = mapped_column(String, unique=True, index=True, nullable=True)
