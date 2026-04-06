from sqlalchemy import Column, Integer, String
from database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, String)
    email = Column(String, unique=True, index=True)
    name = Column(String)
    number = Column(Integer)
    password = Column(String)
