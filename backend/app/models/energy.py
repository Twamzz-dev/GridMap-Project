from sqlalchemy import Column, Float, String, DateTime, Integer, ForeignKey
from sqlalchemy.orm import relationship
from app.database import Base

class ProductionData(Base):
    __tablename__ = "production_data"
    
    id = Column(Integer, primary_key=True, index=True)
    installation_id = Column(Integer, ForeignKey("installations.id"), nullable=False, index=True)
    timestamp = Column(DateTime, nullable=False, index=True)
    power_kw = Column(Float, nullable=False)
    weather = Column(String(50))  # e.g., "sunny", "cloudy"
    solar_elevation = Column(Float)  # in degrees
    energy_kwh = Column(Float)
    status = Column(String(50), default="active")

    # Relationship with installation
    installation = relationship("app.models.installation.Installation", back_populates="production_data")

    def to_dict(self):
        return {
            "id": self.id,
            "installation_id": self.installation_id,
            "timestamp": self.timestamp.isoformat(),
            "power_kw": self.power_kw,
            "weather": self.weather,
            "solar_elevation": self.solar_elevation,
            "energy_kwh": self.energy_kwh,
            "status": self.status
        }