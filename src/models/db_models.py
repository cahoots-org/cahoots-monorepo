from sqlalchemy import Column, String, Integer, Boolean, JSON
from src.db.database import Base

class TeamConfiguration(Base):
    __tablename__ = "team_configurations"

    project_id = Column(String, primary_key=True)
    config = Column(JSON, nullable=False)
    created_at = Column(Integer, nullable=False)
    updated_at = Column(Integer, nullable=False) 