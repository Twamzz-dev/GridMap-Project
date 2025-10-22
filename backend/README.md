# 🌍 GridMap MVP – Green Energy Data Platform

GridMap is a real-time dashboard for visualizing solar energy production across Kenya. Built in 4 weeks by a cross-functional team, it aggregates simulated data from 20+ installations and presents it through a clean, interactive UI.

## 🚀 Project Goals

- ✅ Deployed application accessible via public URL
- ✅ Dashboard displays real-time energy data
- ✅ 20+ simulated installations with 7 days of historical data
- ✅ Clean, professional UI matching pitch deck aesthetic
- ✅ Complete documentation for demo and future development

---

## 🧰 Tech Stack

| Layer       | Technology                     |
|------------|--------------------------------|
| Backend     | Python, FastAPI, SQLAlchemy, Alembic |
| Database    | PostgreSQL                     |
| Data Engine | Custom Solar Simulator, Celery, Redis |
| Frontend    | React (Vite), Tailwind CSS, Recharts, Leaflet |
| Deployment  | Railway (Backend), Vercel (Frontend) |

---

## 📁 Project Structure

```text
gridmap-mvp/
├── backend/
│   ├── app/                # FastAPI app
│   ├── data_simulator/     # Solar data generator
│   ├── requirements.txt
│   ├── .env.example
│   └── README.md
├── frontend/
│   └── src/                # React components
└── README.md

```

---

## ⚙️ Setup Instructions

### 1. Clone the Repository

```bash
git clone https://github.com/your-org/gridmap-mvp.git
cd gridmap-mvp
```

### 2. Backend Setup

```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Start Redis Server
```bash
# Install Redis (Ubuntu/Debian)
sudo apt update
sudo apt install redis-server

# Start Redis
sudo systemctl start redis
# or
redis-server

# Verify Redis is running
redis-cli ping  # Should return "PONG"
```

### Run Celery Workers
You need two terminals for Celery:

```bash
# Terminal 1: Start Celery Worker
cd backend
celery -A app.tasks worker --loglevel=info

# Terminal 2: Start Celery Beat (for scheduled tasks)
cd backend
celery -A app.tasks beat --loglevel=info
```

The simulation will now run automatically every hour. To manually trigger a simulation:
```bash
celery -A app.tasks call app.tasks.simulate_and_store_realtime_data
```

- Create `.env` file from `.env.example` and configure PostgreSQL credentials
- Run Alembic migrations
- Seed database with installations and historical data

### 3. Frontend Setup

```bash
cd frontend
npm install
npm run dev
```

- Configure `VITE_API_URL` in `.env` to point to backend

---

## 🧪 API Endpoints

| Endpoint                     | Description                          |
|-----------------------------|--------------------------------------|
| `/installations`            | List all solar installations         |
| `/dashboard/realtime`       | Real-time dashboard metrics          |
| `/dashboard/timeseries`     | Hourly production data               |
| `/dashboard/regions`        | Regional breakdown of metrics        |

Auto-generated docs available at `/docs` (FastAPI Swagger UI)

---

## 📦 Deployment

### Backend (Railway)

```bash
railway login
railway init
railway up
```

### Frontend (Vercel)

```bash
vercel login
vercel --prod
```

---

## 📚 Documentation

- [FastAPI Docs](https://fastapi.tiangolo.com)
- [React Docs](https://react.dev)
- [Tailwind CSS](https://tailwindcss.com/docs)
- [Recharts Examples](https://recharts.org/en-US/examples)
- [Leaflet Tutorials](https://leafletjs.com/examples.html)

---

## 👥 Team Roles

- Backend Lead – Daniel Gatimu
- Full-Stack Developer
- Data Engineer
- Frontend Developer
- UI/UX Designer

---

## 📈 Impact

GridMap aligns with SDGs 7, 9, and 13 by enabling data-driven grid management and unlocking carbon trading potential in Africa’s renewable energy sector.

---

## 📄 License

MIT License – Free to use, modify, and distribute.

---

## 🙌 Acknowledgements

Thanks to Power Learn Project and the team for inspiration and support.

---
