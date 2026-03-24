# КОД-агент

AI-агент анализа кредитной обеспечительной документации.

## Quick Start

```bash
cp .env.example .env
docker compose up -d
docker compose exec app alembic upgrade head
docker compose exec ollama ollama pull qwen2.5:7b
cd frontend && npm install && npm run dev
```

Backend: http://localhost:8080
Frontend: http://localhost:3000
MinIO Console: http://localhost:9001
Qdrant Dashboard: http://localhost:6333/dashboard

## Documentation

See [CLAUDE.md](CLAUDE.md) for full project documentation.
