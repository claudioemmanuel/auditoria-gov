.PHONY: dev dev-full dev-down logs

# Lightweight local stack (~2.8 GB RAM). Run web natively.
dev:
	docker compose -f docker-compose.yml -f docker-compose.dev-lite.yml up -d
	@echo ""
	@echo "  Backend running: http://localhost:8000"
	@echo "  Run frontend natively:"
	@echo "    cd web && NEXT_PUBLIC_API_URL=http://localhost:8000 npm run dev"
	@echo ""

# Full stack with all services (~7.5 GB RAM)
dev-full:
	docker compose up -d

dev-down:
	docker compose down

logs:
	docker compose logs -f --tail=100

test:
	uv run --extra test pytest -q

lint-web:
	cd web && npm run lint && npm run build
