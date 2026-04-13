# 🌐 RL Environment Simulator for B2B Workflows

[![FastAPI](https://img.shields.io/badge/FastAPI-005571?style=for-the-badge&logo=fastapi)](https://fastapi.tiangolo.com/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-4169E1?style=for-the-badge&logo=postgresql&logoColor=white)](https://www.postgresql.org/)
[![Docker](https://img.shields.io/badge/Docker-2496ED?style=for-the-badge&logo=docker&logoColor=white)](https://www.docker.com/)
[![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)

A production-ready, sandboxed **Reinforcement Learning (RL) environment** designed to simulate complex B2B CRM workflows. Built with a high-performance asynchronous architecture, this project provides a realistic sandbox for training AI agents to manage support tickets, tasks, and users effectively.

---

## ✨ Key Features

- 🏗️ **Gym-Style RL Endpoints**: Native implementation of `/rl/reset` and `/rl/step` loops for seamless agent integration.
- ⚡ **Asynchronous Architecture**: End-to-end `asyncio` support with `SQLAlchemy 2.0` and `asyncpg` for high-concurrency simulation.
- 📂 **CRM Sandbox**: Pre-configured logic for Users, Tickets, and Tasks with simulated role distributions and statuses.
- 🔐 **Secure by Default**: JWT-based authentication for both API users and AI agents.
- 🐳 **Containerized Deployment**: Ready-to-use Docker and Docker Compose configurations for instant environment setup.
- 📊 **Dynamic Rewards**: Native reward calculation logic based on environment constraints and task resolution.

---

## 🏗️ Project Architecture

```plaintext
.
├── alembic/           # Database migration scripts
├── app/
│   ├── api/           # API routes (Auth, CRM, RL)
│   ├── core/          # Configuration and security settings
│   ├── db/            # Database session and base model
│   ├── models/        # SQLAlchemy ORM models
│   ├── schemas/       # Pydantic data validation schemas
│   └── services/      # Business logic and RL engine
├── test_agent.py      # Example AI Agent (Stochastic Policy)
├── Dockerfile         # App container definition
├── docker-compose.yml # Full environment orchestration
└── requirements.txt   # Project dependencies
```

---

## 🚀 Getting Started

### 📦 Option 1: Docker (Recommended)

Spin up the entire stack (FastAPI + PostgreSQL) with a single command:

```bash
docker-compose up --build -d
```
> The API will be available at `http://localhost:8000`. Tables are automatically created on startup.

### 🐍 Option 2: Local Setup

1. **Clone & Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Configure Environment Variables**:
   Copy `.env.example` to `.env` and update your database credentials.

3. **Run the Server**:
   ```bash
   uvicorn app.main:app --reload
   ```

---

## 🤖 Testing the RL Integration

We provide a `test_agent.py` script that demonstrates how an AI agent interacts with the environment.

```bash
python test_agent.py
```

**How it works:**
1. **Reset**: Calls `/rl/reset` to initialize a new episode and fetch the baseline observation.
2. **Observe**: Parses the current state (CRM tickets, agent availability).
3. **Act**: Periodically calls `/rl/step` with actions like `CREATE_TASK` or `RESOLVE_TICKET`.
4. **Learn**: Receives rewards and state updates to optimize its policy.

---

## 🛠️ API Reference

| Endpoint | Method | Description |
| :--- | :--- | :--- |
| `/auth/token` | `POST` | Login and retrieve JWT access token |
| `/rl/reset` | `POST` | Reset the simulation to a clean state |
| `/rl/step` | `POST` | Execute an action and advance the environment |
| `/crm/tickets` | `GET` | Retrieve current ticket lists |
| `/health` | `GET` | Service status check |

> Visit `http://localhost:8000/docs` for the interactive Swagger UI.

---

## 📜 Database Migrations

This project uses **Alembic** for schema management. To generate and apply migrations:

```bash
# Generate a new migration
alembic revision --autogenerate -m "Add feature X"

# Apply migrations
alembic upgrade head
```

---

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request or open an issue for any bugs or feature requests.

---

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

---

*Built with ❤️ for AI System Architects.*
