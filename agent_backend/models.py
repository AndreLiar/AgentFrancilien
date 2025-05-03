#agent_backend/models.py
from sqlalchemy import Column, Integer, String, DateTime, func
from agent_backend.database import Base

class Summary(Base):
    __tablename__ = "summaries"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String)
    content = Column(String)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
