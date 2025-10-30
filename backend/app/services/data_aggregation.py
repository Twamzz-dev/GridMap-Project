from datetime import datetime, timedelta, timezone
from sqlalchemy.orm import Session
from app.models.energy import ProductionData
from app.models.installation import Installation
from typing import List, Dict
from collections import defaultdict

def aggregate_energy_over_interval(db: Session, start: datetime, end: datetime, interval: str = "hour") -> List[Dict]:
    """Aggregate total energy and power by hour or day in UTC."""
    q = db.query(ProductionData).filter(ProductionData.timestamp >= start).filter(ProductionData.timestamp <= end)
    rows = q.all()
    if not rows:
        return []
    buckets = defaultdict(lambda: {"energy_kwh": 0.0, "power_kw_sum": 0.0, "power_count": 0})
    def bucket_start(ts: datetime):
        if interval == "hour":
            return ts.replace(minute=0, second=0, microsecond=0, tzinfo=ts.tzinfo)
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
    return out

def get_energy_summary(db: Session):
    records = db.query(ProductionData).all()
    installations = db.query(Installation).all()
    if not records:
        return {"message": "No production data available"}
    total_energy = sum(record.energy_kwh for record in records if record.energy_kwh)
    total_power = sum(record.power_kw for record in records if record.power_kw)
    installation_count = len(installations)
    active_installations = len([inst for inst in installations if getattr(inst, 'status', None) == "active"])
    return {
        "total_energy_kwh": round(total_energy, 2),
        "total_power_kw": round(total_power, 2),
        "total_records": len(records),
        "total_installations": installation_count,
        "active_installations": active_installations,
        "average_energy_per_record": round(total_energy / len(records), 2) if records else 0,
    }

def group_energy_by_installation(db: Session, start: datetime = None, end: datetime = None) -> Dict[int, Dict]:
    from app.models.energy import ProductionData
    from app.models.installation import Installation
    query = db.query(ProductionData)
    if start:
        query = query.filter(ProductionData.timestamp >= start)
    if end:
        query = query.filter(ProductionData.timestamp <= end)
    rows = query.all()
    grouped = {}
    for r in rows:
        iid = r.installation_id
        if iid not in grouped:
            grouped[iid] = {
                'installation_id': iid,
                'total_energy_kwh': 0,
                'total_power_kw': 0,
                'count': 0
            }
        grouped[iid]['total_energy_kwh'] += float(r.energy_kwh or 0)
        grouped[iid]['total_power_kw'] += float(r.power_kw or 0)
        grouped[iid]['count'] += 1
    # Add average
    for val in grouped.values():
        if val['count']:
            val['avg_power_kw'] = val['total_power_kw'] / val['count']
        else:
            val['avg_power_kw'] = 0
    return grouped

def compute_performance_metrics(db: Session, start: datetime, end: datetime) -> dict:
    """
    - Optimization: Estimate gain if all faults/outages were caught.
    - CO2 savings: Use 5kW=1.2 tons/year baseline.
    - System uptime: % hours with power > 0 when sun is expected.
    - Cost savings: 30% avoided maintenance cost by reduced fault duration.
    """
    # Constants
    CO2_PER_KWH = 1.2 / (5 * 365 * 5.5)  # tons per kWh for 5kW, 5.5 sun hours/day
    COST_PER_FAULT = 50  # USD per fault (placeholder)
    COST_SAVING_PCT = 0.3
    #
    installations = db.query(Installation).all()
    out = []
    total_kwh = 0
    total_kwh_lost = 0
    total_uptime_hours = 0
    total_possible_hours = 0
    total_co2 = 0
    total_avoided_cost = 0
    # Benchmarking: by segment
    segments = defaultdict(lambda: {
        'energy_kwh': 0, 'kwh_lost_to_faults': 0, 'potential_kwh': 0,
        'uptime_percent_sum': 0, 'inst_count': 0, 'co2_savings_tons': 0, 'maintenance_avoided_cost': 0,
        'total_uptime_hours': 0, 'total_possible_hours': 0,
    })
    for inst in installations:
        segment = getattr(inst, 'owner_type', 'unknown') or 'unknown'
        # Only hours between sunrise and sunset (simulate 6am-6pm)
        hours_in_window = int(((end - start).total_seconds())//3600)
        expected_sun_hours = 12 * ((end - start).days)
        q = db.query(ProductionData).filter(
            ProductionData.installation_id == inst.id,
            ProductionData.timestamp >= start,
            ProductionData.timestamp <= end
        ).order_by(ProductionData.timestamp)
        rows = q.all()
        kwh = sum(r.energy_kwh or 0 for r in rows)
        # Outages: if hour is during sun, power_kw==0
        faults = [r for r in rows if (6 <= (r.timestamp.hour%24) < 18 and r.power_kw == 0)]
        # Estimate lost: if that hour matched system_capacity
        lost_kwh = len(faults) * (inst.capacity_kw or 0)
        # Uptime: count how many sun hours had power > 0
        up_hours = len([r for r in rows if (6 <= (r.timestamp.hour%24) < 18 and r.power_kw > 0)])
        poss_hours = len([r for r in rows if (6 <= (r.timestamp.hour%24) < 18)])
        uptime = (up_hours / poss_hours) * 100 if poss_hours else 0
        co2 = kwh * CO2_PER_KWH
        avoided = len(faults) * COST_PER_FAULT * COST_SAVING_PCT
        out.append({
            'installation_id': inst.id,
            'name': inst.name,
            'owner_type': segment,
            'energy_kwh': kwh,
            'kwh_lost_to_faults': lost_kwh,
            'potential_kwh': kwh + lost_kwh,
            'relative_gain_percent': (lost_kwh / (kwh + lost_kwh) * 100) if (kwh + lost_kwh) else 0,
            'co2_savings_tons': co2,
            'uptime_percent': uptime,
            'maintenance_avoided_cost': avoided,
            'outage_events': len(faults),
        })
        total_kwh += kwh
        total_kwh_lost += lost_kwh
        total_uptime_hours += up_hours
        total_possible_hours += poss_hours
        total_co2 += co2
        total_avoided_cost += avoided
        # per segment
        s = segments[segment]
        s['energy_kwh'] += kwh
        s['kwh_lost_to_faults'] += lost_kwh
        s['potential_kwh'] += (kwh + lost_kwh)
        s['co2_savings_tons'] += co2
        s['maintenance_avoided_cost'] += avoided
        s['inst_count'] += 1
        s['total_uptime_hours'] += up_hours
        s['total_possible_hours'] += poss_hours
    # finalize segment stats
    for s in segments.values():
        s['relative_gain_percent'] = (s['kwh_lost_to_faults'] / s['potential_kwh'] * 100) if s['potential_kwh'] else 0
        s['uptime_percent'] = (s['total_uptime_hours'] / s['total_possible_hours'] * 100) if s['total_possible_hours'] else 0
    global_stats = {
        'energy_kwh': total_kwh,
        'kwh_lost_to_faults': total_kwh_lost,
        'potential_kwh': total_kwh + total_kwh_lost,
        'relative_gain_percent': (total_kwh_lost / (total_kwh + total_kwh_lost) * 100) if (total_kwh + total_kwh_lost) else 0,
        'co2_savings_tons': total_co2,
        'uptime_percent': (total_uptime_hours / total_possible_hours * 100) if total_possible_hours else 0,
        'maintenance_avoided_cost': total_avoided_cost,
    }
    return {'global': global_stats, 'segments': segments, 'per_installation': out}