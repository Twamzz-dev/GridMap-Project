import json
from celery import Celery
from datetime import datetime
from app.models.installation import Installation
from app.database import SessionLocal
from app.models.energy import ProductionData
from data_simulator.solar_generator import SolarDataSimulator
import redis
from celery.schedules import crontab

# Redis Configuration
redis_client = redis.Redis(
    host='localhost',
    port=6379,
    db=0,
    decode_responses=True  # This ensures Redis returns strings instead of bytes
)

# Celery Configuration
celery_app = Celery('tasks', broker='redis://localhost:6379/0')
celery_app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
)

# Schedule configuration (run every hour at minute 0)
celery_app.conf.beat_schedule = {
    'simulate-and-store-realtime-data-hourly': {
        'task': 'app.tasks.simulate_and_store_realtime_data',
        'schedule': crontab(minute=0),  # Run at the start of every hour
    },
}

def cache_installation_data(installation_id: int, data: dict):
    """Cache installation data in Redis with proper serialization"""
    try:
        # Cache the latest data
        latest_key = f"installation:{installation_id}:latest"
        redis_client.set(latest_key, json.dumps(data))
        
        # Cache in a time-series list (keep last 24 hours)
        timeseries_key = f"installation:{installation_id}:hourly"
        redis_client.lpush(timeseries_key, json.dumps(data))
        redis_client.ltrim(timeseries_key, 0, 23)  # Keep only last 24 entries
        
        # Set expiration for keys (48 hours)
        redis_client.expire(latest_key, 172800)  # 48 hours in seconds
        redis_client.expire(timeseries_key, 172800)
        
    except redis.RedisError as e:
        print(f"Redis caching error: {str(e)}")
        # Continue execution even if caching fails

@celery_app.task(bind=True, max_retries=3)
def simulate_and_store_realtime_data(self):
    """Generate and store solar production data for all installations"""
    print("Simulation task started")
    
    try:
        db = SessionLocal()
        simulator = SolarDataSimulator()
        installations = db.query(Installation).all()
        now = datetime.utcnow()
        
        for inst in installations:
            try:
                # Generate production data
                data = simulator.generate_hourly_production(
                    inst.capacity_kw,
                    inst.location_name,
                    now,
                    installation_year=now.year
                )
                
                for hour_data in data:
                    # Create and store in database
                    record = ProductionData(
                        installation_id=inst.id,
                        timestamp=hour_data['timestamp'],
                        power_kw=hour_data['power_kw'],
                        weather=hour_data['weather'],
                        solar_elevation=hour_data['solar_elevation'],
                        energy_kwh=hour_data['power_kw'],  # Assuming 1-hour intervals
                        status=inst.status
                    )
                    db.add(record)
                    
                    # Cache in Redis
                    cache_data = {
                        'installation_id': inst.id,
                        'timestamp': hour_data['timestamp'].isoformat(),
                        'power_kw': hour_data['power_kw'],
                        'weather': hour_data['weather'],
                        'solar_elevation': hour_data['solar_elevation'],
                        'energy_kwh': hour_data['power_kw'],
                        'status': inst.status
                    }
                    cache_installation_data(inst.id, cache_data)
                
                # Update installation's last timestamp
                inst.last_data_timestamp = now
                db.add(inst)
                
            except Exception as e:
                print(f"Error processing installation {inst.id}: {str(e)}")
                continue  # Continue with next installation
        
        db.commit()
        print("Simulation task completed successfully")
        
    except Exception as e:
        print(f"Simulation task error: {str(e)}")
        self.retry(exc=e, countdown=60)  # Retry after 60 seconds
        
    finally:
        db.close()
 