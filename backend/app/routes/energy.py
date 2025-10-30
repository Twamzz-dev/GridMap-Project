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
from app.services.data_aggregation import aggregate_energy_over_interval
from app.services.cache import get_cache, set_cache
from app.services.data_aggregation import get_energy_summary
from app.services.data_aggregation import group_energy_by_installation
from app.services.data_aggregation import compute_performance_metrics

router = APIRouter()

@router.get("/energy")
def get_energy_output(db: Session = Depends(get_db)):
    cache_key = "energy:all"
    data = get_cache(cache_key)
    if data is not None:
        return data
    result = db.query(ProductionData).all()
    # convert to dict for json serializability (if needed)
    out = [r.to_dict() for r in result]
    set_cache(cache_key, out, ex=30)  # cache for 30s
    return out

@router.get("/energy/installation/{installation_id}")
def get_energy_by_installation(installation_id: int, db: Session = Depends(get_db)):
    cache_key = f"energy:installation:{installation_id}"
    data = get_cache(cache_key)
    if data is not None:
        return data
    result = db.query(ProductionData).filter(ProductionData.installation_id == installation_id).all()
    out = [r.to_dict() for r in result]
    set_cache(cache_key, out, ex=60)  # cache per install 1 minute
    return out

@router.get("/energy/installations")
def get_installations(db: Session = Depends(get_db)):
    """Get all installations."""
    return db.query(Installation).all()

@router.get("/energy/stats/summary")
def get_energy_summary_endpoint(db: Session = Depends(get_db)):
    return get_energy_summary(db)


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
    # Compose cache key
    cache_key = f"agg:{interval}:{start.isoformat()}:{end.isoformat()}"
    data = get_cache(cache_key)
    if data is not None:
        return data
    buckets = aggregate_energy_over_interval(db, start, end, interval)
    out = {"interval": interval, "buckets": buckets, "start": start.isoformat(), "end": end.isoformat()}
    set_cache(cache_key, out, ex=600)
    return out


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


@router.get("/energy/leaderboard")
def get_energy_leaderboard(
    start: datetime = Query(None),
    end: datetime = Query(None),
    limit: int = Query(10),
    db: Session = Depends(get_db),
):
    # Defaults to last 24 hours
    if end is None:
        end = datetime.now(timezone.utc)
    if start is None:
        start = end - timedelta(days=1)
    agg = group_energy_by_installation(db, start, end)
    leaderboard = sorted(agg.values(), key=lambda x: x["total_energy_kwh"], reverse=True)
    return leaderboard[:limit]


@router.get("/performance/metrics")
def get_performance_metrics(
    start: datetime = Query(None),
    end: datetime = Query(None),
    db: Session = Depends(get_db),
):
    # Default to last 365 days
    if end is None:
        end = datetime.now(timezone.utc)
    if start is None:
        start = end - timedelta(days=365)
    return compute_performance_metrics(db, start, end)


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

@router.get("/map/installations_mini")
def map_installations_mini(db: Session = Depends(get_db)):
    """Lightweight endpoint for map rendering: returns minimal fields for each installation as GeoJSON Features."""
    installations = db.query(Installation).all()
    features = []
    for inst in installations:
        feature = {
            "type": "Feature",
            "geometry": {
                "type": "Point",
                "coordinates": [inst.location_lng, inst.location_lat]
            },
            "properties": {
                "installation_id": inst.id,
                "name": inst.name,
                "capacity_kw": inst.capacity_kw,
                "status": inst.status,
            }
        }
        features.append(feature)
    return {"type": "FeatureCollection", "features": features}