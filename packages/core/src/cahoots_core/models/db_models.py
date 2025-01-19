"""Base database models."""
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

from sqlalchemy import Column, String, Integer, Boolean, JSON

class TeamConfiguration(Base):
    __tablename__ = "team_configurations"

    project_id = Column(String, primary_key=True)
    config = Column(JSON, nullable=False)
    created_at = Column(Integer, nullable=False)
    updated_at = Column(Integer, nullable=False) 