{
  "name": "coreappointment-backend",
  "version": "1.0.0",
  "description": "Backend API para gestión de servicios y horarios de negocio",
  "main": "app/main.py",
  "scripts": {
    "dev": "uvicorn app.main:app --reload --host 0.0.0.0 --port 8002",
    "start": "source venv/bin/activate && uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 1",
    "dev:reload": "source venv/bin/activate && uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload",
    "setup:dev": "./setup.sh development",
    "setup:prod": "./setup.sh production",
    "test": "source venv/bin/activate && python -m pytest tests/ -v",
    "lint": "source venv/bin/activate && flake8 app/ --max-line-length=100",
    "format": "source venv/bin/activate && black app/ --line-length=100",
    "docker:build": "docker build -t coreappointment-api .",
    "docker:run": "docker run -p 8000:8000 --env-file .env coreappointment-api",
    
    "/* --- 📦 COMANDOS DE BASE DE DATOS (ALEMBIC) --- */": "",
    "db:plan": "source venv/bin/activate && alembic revision --autogenerate -m",
    "db:migrate": "source venv/bin/activate && alembic upgrade head",
    "db:rollback": "source venv/bin/activate && alembic downgrade -1",
    "db:history": "source venv/bin/activate && alembic history --verbose"
  },
  "keywords": [
    "fastapi",
    "sqlalchemy",
    "postgresql",
    "pydantic",
    "python",
    "api",
    "backend"
  ],
  "author": "CoreAppointment Team",
  "license": "MIT",
  "engines": {
    "node": ">=18.0.0",
    "pnpm": ">=8.0.0"
  },
  "devDependencies": {
    "@types/node": "^20.0.0"
  },
  "repository": {
    "type": "git",
    "url": "https://github.com/tu-usuario/coreappointment-backend.git"
  },
  "bugs": {
    "url": "https://github.com/tu-usuario/coreappointment-backend/issues"
  },
  "homepage": "https://github.com/tu-usuario/coreappointment-backend#readme"
}
