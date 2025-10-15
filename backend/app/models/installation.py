from sqlalchemy import Column, Integer, String, Float, DateTime
from sqlalchemy.orm import relationship
from app.database import Base


class Installation(Base):
    __tablename__ = "installations"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), index=True, nullable=False)
    capacity_kw = Column(Float, nullable=False)
    location_name = Column(String(50), nullable=False)  # e.g., "NAIROBI"
    location_lat = Column(Float, nullable=False)
    location_lng = Column(Float, nullable=False)
    owner_type = Column(String(50), nullable=False, default="residential")
    status = Column(String(50), default="active")
    last_data_timestamp = Column(DateTime, index=True)

    # Relationship with production data
    production_data = relationship("production_data", back_populates="installation")

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "capacity_kw": self.capacity_kw,
            "location_name": self.location_name,
            "location": {
                "lat": self.location_lat,
                "lng": self.location_lng
            },
            "owner_type": self.owner_type,
            "status": self.status,
            "last_data_timestamp": self.last_data_timestamp.isoformat() if self.last_data_timestamp else None
        }