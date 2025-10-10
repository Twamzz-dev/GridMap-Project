
from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Float
from app.database import Base


class AggregatedStats(Base):
    __tablename__ = "aggregated_stats"

    timestamp = Column(DateTime, primary_key=True)
    total_systems = Column(Integer, nullable=False)
    active_systems = Column(Integer, nullable=False)
    current_power_kw = Column(Float, nullable=False)
    today_energy_kwh = Column(Float, nullable=False)
    peak_power_today_kw = Column(Float, nullable=False)
    capacity_factor = Column(Float, nullable=False)

