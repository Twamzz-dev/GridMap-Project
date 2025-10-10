from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.database import get_db
from app.models.energy import ProductionData
from app.models.installation import Installation
from typing import List, Dict, Any
from datetime import datetime, timedelta, timezone
import os
import json
from collections import defaultdict

router = APIRouter()

@router.get("/energy")
def get_energy_output(db: Session = Depends(get_db)):
    """Get all production data records."""
    return db.query(ProductionData).all()

@router.get("/energy/installation/{installation_id}")
def get_energy_by_installation(installation_id: int, db: Session = Depends(get_db)):
    """Get production data for a specific installation."""
    return db.query(ProductionData).filter(ProductionData.installation_id == installation_id).all()

@router.get("/energy/installations")
def get_installations(db: Session = Depends(get_db)):
    """Get all installations."""
    return db.query(Installation).all()

@router.get("/energy/stats/summary")
def get_energy_summary(db: Session = Depends(get_db)):
    """Get summary statistics of production data."""
    records = db.query(ProductionData).all()
    installations = db.query(Installation).all()
    
    if not records:
        return {"message": "No production data available"}
    
    total_energy = sum(record.energy_kwh for record in records if record.energy_kwh)
    total_power = sum(record.power_kw for record in records if record.power_kw)
    installation_count = len(installations)
    active_installations = len([inst for inst in installations if inst.status.value == "active"])
    
    return {
        "total_energy_kwh": round(total_energy, 2),
        "total_power_kw": round(total_power, 2),
        "total_records": len(records),
        "total_installations": installation_count,
        "active_installations": active_installations,
        "average_energy_per_record": round(total_energy / len(records), 2) if records else 0
    }


@router.get("/energy/aggregate")
def aggregate_energy(
    start: datetime = Query(None),
    end: datetime = Query(None),
    interval: str = Query("hour", regex="^(hour|day)$"),
    db: Session = Depends(get_db),
):
    """Aggregate total energy and power by hour or day in UTC.
    - energy_kwh: sum per bucket
    - power_kw: average of last known value in bucket (approx by average of values)
    """
    if end is None:
        end = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0)
    if start is None:
        start = end - timedelta(days=1)

    q = (
        db.query(ProductionData)
        .filter(ProductionData.timestamp >= start)
        .filter(ProductionData.timestamp <= end)
    )
    rows = q.all()

    if not rows:
        return {"buckets": [], "interval": interval}

    buckets: Dict[datetime, Dict[str, float]] = defaultdict(lambda: {"energy_kwh": 0.0, "power_kw_sum": 0.0, "power_count": 0})

    def bucket_start(ts: datetime) -> datetime:
        if interval == "hour":
            return ts.replace(minute=0, second=0, microsecond=0, tzinfo=ts.tzinfo)
        # day
        return ts.replace(hour=0, minute=0, second=0, microsecond=0, tzinfo=ts.tzinfo)

    for r in rows:
        b = bucket_start(r.timestamp)
        buckets[b]["energy_kwh"] += float(r.energy_kwh or 0.0)
        if r.power_kw is not None:
            buckets[b]["power_kw_sum"] += float(r.power_kw)
            buckets[b]["power_count"] += 1

    out = []
    for b_start, agg in sorted(buckets.items()):
        avg_power_kw = (agg["power_kw_sum"] / agg["power_count"]) if agg["power_count"] else 0.0
        out.append({
            "bucket_start": b_start.isoformat(),
            "total_energy_kwh": round(agg["energy_kwh"], 3),
            "avg_power_kw": round(avg_power_kw, 3),
        })

    return {"interval": interval, "buckets": out, "start": start.isoformat(), "end": end.isoformat()}


@router.get("/energy/today")
def energy_today(db: Session = Depends(get_db)):
    """Return KPIs: total power (MW), energy today (MWh), systems total, systems active."""
    now = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0)
    midnight = now.replace(hour=0)

    # Energy today
    today_rows = (
        db.query(ProductionData)
        .filter(ProductionData.timestamp >= midnight)
        .filter(ProductionData.timestamp <= now)
        .all()
    )
    energy_today_kwh = sum(float(r.energy_kwh or 0.0) for r in today_rows)

    # Latest power per installation
    # Get max timestamp per installation
    subq = (
        db.query(
            ProductionData.installation_id.label("installation_id"),
            func.max(ProductionData.timestamp).label("max_ts"),
        )
        .group_by(ProductionData.installation_id)
        .subquery()
    )
    latest = (
        db.query(ProductionData)
        .join(subq, (ProductionData.installation_id == subq.c.installation_id) & (ProductionData.timestamp == subq.c.max_ts))
        .all()
    )

    total_power_kw = sum(float(r.power_kw or 0.0) for r in latest)
    systems_total = len(latest)
    systems_active = sum(1 for r in latest if (r.status or "").lower() == "active")

    return {
        "total_power_mw": round(total_power_kw / 1000.0, 3),
        "energy_today_mwh": round(energy_today_kwh / 1000.0, 3),
        "systems_total": systems_total,
        "systems_active": systems_active,
        "timestamp": now.isoformat(),
    }


@router.get("/map/installations")
def map_installations(db: Session = Depends(get_db)):
    """Return GeoJSON FeatureCollection with latest per-panel properties joined with coordinates from panel_map.geojson."""
    # Load panel positions
    root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
    geojson_path = os.path.join(root, "data_pipeline", "data", "panel_map.geojson")
    with open(geojson_path, "r") as f:
        panel_geo = json.load(f)

    # Latest readings per installation
    subq = (
        db.query(
            ProductionData.installation_id.label("installation_id"),
            func.max(ProductionData.timestamp).label("max_ts"),
        )
        .group_by(ProductionData.installation_id)
        .subquery()
    )
    latest = (
        db.query(ProductionData)
        .join(subq, (ProductionData.installation_id == subq.c.installation_id) & (ProductionData.timestamp == subq.c.max_ts))
        .all()
    )
    latest_map = {r.installation_id: r for r in latest}

    # Get installations with their data
    installations = db.query(Installation).all()
    installation_map = {inst.id: inst for inst in installations}
    
    features = []
    for feat in panel_geo.get("features", []):
        props = feat.get("properties", {})
        pid = props.get("panel_id")
        
        # Find matching installation by name pattern
        matching_installation = None
        for inst in installations:
            if pid in inst.name:
                matching_installation = inst
                break
        
        if matching_installation:
            r = latest_map.get(matching_installation.id)
            properties = {
                "installation_id": matching_installation.id,
                "name": matching_installation.name,
                "panel_id": pid,
                "region": props.get("region"),
                "capacity_kw": props.get("capacity_kw"),
                "status": getattr(r, "status", None),
                "current_power_kw": getattr(r, "power_kw", None),
                "timestamp": getattr(r, "timestamp", None).isoformat() if r and r.timestamp else None,
            }
            features.append({
                "type": "Feature",
                "geometry": feat.get("geometry"),
                "properties": properties,
            })

    return {"type": "FeatureCollection", "features": features}