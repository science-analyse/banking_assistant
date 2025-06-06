# 🏛️ Kapital Bank AI Assistant - Makefile
# Easy project management and development commands

.PHONY: help install install-dev start start-dev stop test test-api test-load clean build deploy health check-env lint format docker-build docker-run docker-stop backup

# Default target
.DEFAULT_GOAL := help

# Variables
PYTHON := python3
PIP := pip3
PORT := 8000
HOST := 0.0.0.0
PROJECT_NAME := kapital-bank-ai-assistant
DOCKER_IMAGE := $(PROJECT_NAME):latest

# Colors for output
RED := \033[0;31m
GREEN := \033[0;32m
YELLOW := \033[0;33m
BLUE := \033[0;34m
PURPLE := \033[0;35m
CYAN := \033[0;36m
NC := \033[0m # No Color

# Help target
help: ## Show this help message
	@echo "🏛️  $(GREEN)Kapital Bank AI Assistant$(NC) - Development Commands"
	@echo "=================================================================="
	@echo ""
	@echo "$(CYAN)Setup Commands:$(NC)"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | grep -E "(install|setup|init)" | awk 'BEGIN {FS = ":.*?## "}; {printf "  $(GREEN)%-20s$(NC) %s\n", $$1, $$2}'
	@echo ""
	@echo "$(CYAN)Development Commands:$(NC)"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | grep -E "(start|dev|run|stop)" | awk 'BEGIN {FS = ":.*?## "}; {printf "  $(GREEN)%-20s$(NC) %s\n", $$1, $$2}'
	@echo ""
	@echo "$(CYAN)Testing Commands:$(NC)"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | grep -E "(test|check|health)" | awk 'BEGIN {FS = ":.*?## "}; {printf "  $(GREEN)%-20s$(NC) %s\n", $$1, $$2}'
	@echo ""
	@echo "$(CYAN)Docker Commands:$(NC)"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | grep -E "(docker|build|deploy)" | awk 'BEGIN {FS = ":.*?## "}; {printf "  $(GREEN)%-20s$(NC) %s\n", $$1, $$2}'
	@echo ""
	@echo "$(CYAN)Utility Commands:$(NC)"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | grep -vE "(install|setup|init|start|dev|run|stop|test|check|health|docker|build|deploy)" | awk 'BEGIN {FS = ":.*?## "}; {printf "  $(GREEN)%-20s$(NC) %s\n", $$1, $$2}'
	@echo ""
	@echo "$(YELLOW)Examples:$(NC)"
	@echo "  make install      # Install dependencies"
	@echo "  make start        # Start development server"
	@echo "  make test         # Run all tests"
	@echo "  make docker-build # Build Docker image"

# Environment setup
check-env: ## Check environment setup
	@echo "$(BLUE)🔍 Checking environment...$(NC)"
	@command -v $(PYTHON) >/dev/null 2>&1 || { echo "$(RED)❌ Python 3 not found$(NC)"; exit 1; }
	@$(PYTHON) --version
	@command -v $(PIP) >/dev/null 2>&1 || { echo "$(RED)❌ pip3 not found$(NC)"; exit 1; }
	@test -f .env || { echo "$(YELLOW)⚠️  .env file not found. Copy .env.example to .env$(NC)"; }
	@test -f requirements.txt || { echo "$(RED)❌ requirements.txt not found$(NC)"; exit 1; }
	@echo "$(GREEN)✅ Environment check passed$(NC)"

# Installation
install: check-env ## Install production dependencies
	@echo "$(BLUE)📦 Installing production dependencies...$(NC)"
	$(PIP) install --upgrade pip
	$(PIP) install -r requirements.txt
	@echo "$(GREEN)✅ Production dependencies installed$(NC)"

install-dev: install ## Install development dependencies
	@echo "$(BLUE)📦 Installing development dependencies...$(NC)"
	@test -f requirements-dev.txt && $(PIP) install -r requirements-dev.txt || echo "$(YELLOW)⚠️  requirements-dev.txt not found$(NC)"
	@echo "$(GREEN)✅ Development dependencies installed$(NC)"

# Database setup
init-db: ## Initialize database
	@echo "$(BLUE)🗄️  Initializing database...$(NC)"
	$(PYTHON) scripts/init_db.py
	@echo "$(GREEN)✅ Database initialized$(NC)"

setup: install init-db ## Complete setup (install + init database)
	@echo "$(GREEN)🎉 Setup completed! Run 'make start' to begin$(NC)"

# Development server
start: ## Start development server
	@echo "$(BLUE)🚀 Starting Kapital Bank AI Assistant...$(NC)"
	$(PYTHON) run.py --host $(HOST) --port $(PORT)

start-dev: ## Start development server with auto-reload
	@echo "$(BLUE)🔄 Starting development server with auto-reload...$(NC)"
	$(PYTHON) run.py --host $(HOST) --port $(PORT) --no-init

start-prod: ## Start production server
	@echo "$(BLUE)🏭 Starting production server...$(NC)"
	$(PYTHON) run.py --production --host $(HOST) --port $(PORT) --workers 4

# Stop server (for Docker or background processes)
stop: ## Stop running server
	@echo "$(YELLOW)🛑 Stopping server...$(NC)"
	@pkill -f "run.py" || echo "No server process found"

# Testing
test: ## Run all tests
	@echo "$(BLUE)🧪 Running all tests...$(NC)"
	$(PYTHON) scripts/test_apis.py --all
	@echo "$(GREEN)✅ All tests completed$(NC)"

test-api: ## Test API endpoints only
	@echo "$(BLUE)🔗 Testing API endpoints...$(NC)"
	$(PYTHON) scripts/test_apis.py --internal

test-external: ## Test external APIs only
	@echo "$(BLUE)🌐 Testing external APIs...$(NC)"
	$(PYTHON) scripts/test_apis.py --external

test-mcp: ## Test MCP servers only
	@echo "$(BLUE)🔧 Testing MCP servers...$(NC)"
	$(PYTHON) scripts/test_apis.py --mcp

test-load: ## Run load test (30 seconds)
	@echo "$(BLUE)⚡ Running load test...$(NC)"
	$(PYTHON) scripts/test_apis.py --load 30

# Health monitoring
health: ## Check application health
	@echo "$(BLUE)🏥 Checking application health...$(NC)"
	$(PYTHON) scripts/health_check.py

health-continuous: ## Run continuous health monitoring
	@echo "$(BLUE)🔄 Starting continuous health monitoring...$(NC)"
	$(PYTHON) scripts/health_check.py --continuous 60

# Code quality
lint: ## Run code linting
	@echo "$(BLUE)🔍 Running code linting...$(NC)"
	@command -v flake8 >/dev/null 2>&1 && flake8 . --count --select=E9,F63,F7,F82 --show-source --statistics || echo "$(YELLOW)⚠️  flake8 not installed$(NC)"
	@command -v mypy >/dev/null 2>&1 && mypy . --ignore-missing-imports || echo "$(YELLOW)⚠️  mypy not installed$(NC)"
	@echo "$(GREEN)✅ Linting completed$(NC)"

format: ## Format code with black and isort
	@echo "$(BLUE)✨ Formatting code...$(NC)"
	@command -v black >/dev/null 2>&1 && black . || echo "$(YELLOW)⚠️  black not installed$(NC)"
	@command -v isort >/dev/null 2>&1 && isort . || echo "$(YELLOW)⚠️  isort not installed$(NC)"
	@echo "$(GREEN)✅ Code formatted$(NC)"

# Docker commands
docker-build: ## Build Docker image
	@echo "$(BLUE)🐳 Building Docker image...$(NC)"
	docker build -t $(DOCKER_IMAGE) .
	@echo "$(GREEN)✅ Docker image built: $(DOCKER_IMAGE)$(NC)"

docker-build-dev: ## Build Docker image for development
	@echo "$(BLUE)🐳 Building development Docker image...$(NC)"
	docker build --target development -t $(PROJECT_NAME):dev .
	@echo "$(GREEN)✅ Development Docker image built$(NC)"

docker-run: docker-build ## Run application in Docker container
	@echo "$(BLUE)🐳 Running Docker container...$(NC)"
	docker run -d --name $(PROJECT_NAME) -p $(PORT):8000 --env-file .env $(DOCKER_IMAGE)
	@echo "$(GREEN)✅ Container started at http://localhost:$(PORT)$(NC)"

docker-run-dev: docker-build-dev ## Run development container with volume mounting
	@echo "$(BLUE)🐳 Running development Docker container...$(NC)"
	docker run -d --name $(PROJECT_NAME)-dev -p 8001:8000 -v $(PWD):/app --env-file .env $(PROJECT_NAME):dev
	@echo "$(GREEN)✅ Development container started at http://localhost:8001$(NC)"

docker-stop: ## Stop Docker container
	@echo "$(YELLOW)🛑 Stopping Docker container...$(NC)"
	@docker stop $(PROJECT_NAME) || echo "Container not running"
	@docker rm $(PROJECT_NAME) || echo "Container not found"
	@docker stop $(PROJECT_NAME)-dev || echo "Dev container not running"
	@docker rm $(PROJECT_NAME)-dev || echo "Dev container not found"

docker-logs: ## Show Docker container logs
	@echo "$(BLUE)📝 Showing Docker logs...$(NC)"
	@docker logs -f $(PROJECT_NAME) || docker logs -f $(PROJECT_NAME)-dev

# Docker Compose commands
compose-up: ## Start all services with Docker Compose
	@echo "$(BLUE)🐳 Starting services with Docker Compose...$(NC)"
	docker-compose up -d
	@echo "$(GREEN)✅ Services started$(NC)"

compose-up-dev: ## Start development services
	@echo "$(BLUE)🐳 Starting development services...$(NC)"
	docker-compose --profile development up -d
	@echo "$(GREEN)✅ Development services started$(NC)"

compose-up-full: ## Start all services including monitoring
	@echo "$(BLUE)🐳 Starting all services including monitoring...$(NC)"
	docker-compose --profile postgres --profile monitoring up -d
	@echo "$(GREEN)✅ All services started$(NC)"

compose-down: ## Stop all Docker Compose services
	@echo "$(YELLOW)🛑 Stopping Docker Compose services...$(NC)"
	docker-compose down
	@echo "$(GREEN)✅ Services stopped$(NC)"

compose-logs: ## Show Docker Compose logs
	@echo "$(BLUE)📝 Showing Docker Compose logs...$(NC)"
	docker-compose logs -f

# Database management
backup-db: ## Backup SQLite database
	@echo "$(BLUE)💾 Backing up database...$(NC)"
	@test -f kapital_assistant.db && cp kapital_assistant.db backups/kapital_assistant_$(shell date +%Y%m%d_%H%M%S).db || echo "$(YELLOW)⚠️  Database file not found$(NC)"
	@test -d data && cp data/kapital_assistant.db backups/kapital_assistant_$(shell date +%Y%m%d_%H%M%S).db || echo "$(YELLOW)⚠️  Data directory not found$(NC)"
	@echo "$(GREEN)✅ Database backed up$(NC)"

restore-db: ## Restore database from backup (specify BACKUP_FILE)
	@echo "$(BLUE)🔄 Restoring database...$(NC)"
	@test -n "$(BACKUP_FILE)" || { echo "$(RED)❌ Please specify BACKUP_FILE=path/to/backup.db$(NC)"; exit 1; }
	@test -f "$(BACKUP_FILE)" || { echo "$(RED)❌ Backup file not found: $(BACKUP_FILE)$(NC)"; exit 1; }
	cp "$(BACKUP_FILE)" kapital_assistant.db
	@echo "$(GREEN)✅ Database restored from $(BACKUP_FILE)$(NC)"

# Deployment helpers
deploy-check: ## Check deployment readiness
	@echo "$(BLUE)🔍 Checking deployment readiness...$(NC)"
	@test -f .env || { echo "$(RED)❌ .env file missing$(NC)"; exit 1; }
	@grep -q "GEMINI_API_KEY=" .env || { echo "$(RED)❌ GEMINI_API_KEY not set$(NC)"; exit 1; }
	@grep -q "ENVIRONMENT=production" .env || echo "$(YELLOW)⚠️  ENVIRONMENT not set to production$(NC)"
	@grep -q "DEBUG=False" .env || echo "$(YELLOW)⚠️  DEBUG not set to False$(NC)"
	@echo "$(GREEN)✅ Deployment check passed$(NC)"

generate-secret: ## Generate a secure secret key
	@echo "$(BLUE)🔐 Generating secret key...$(NC)"
	@$(PYTHON) -c "import secrets; print('SECRET_KEY=' + secrets.token_urlsafe(32))"

# Monitoring and logs
logs: ## Show application logs
	@echo "$(BLUE)📝 Showing application logs...$(NC)"
	@test -f logs/app.log && tail -f logs/app.log || echo "$(YELLOW)⚠️  Log file not found$(NC)"

monitor: ## Start monitoring dashboard
	@echo "$(BLUE)📊 Starting monitoring...$(NC)"
	@echo "Visit http://localhost:3000 for Grafana (admin/admin)"
	@echo "Visit http://localhost:9090 for Prometheus"
	docker-compose --profile monitoring up -d grafana prometheus

# Cleanup
clean: ## Clean up generated files and caches
	@echo "$(BLUE)🧹 Cleaning up...$(NC)"
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	find . -type f -name "*.pyo" -delete 2>/dev/null || true
	find . -type f -name ".coverage" -delete 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "htmlcov" -exec rm -rf {} + 2>/dev/null || true
	rm -f test_results.json 2>/dev/null || true
	@echo "$(GREEN)✅ Cleanup completed$(NC)"

clean-docker: ## Remove Docker images and containers
	@echo "$(BLUE)🐳 Cleaning Docker resources...$(NC)"
	@docker stop $(PROJECT_NAME) $(PROJECT_NAME)-dev 2>/dev/null || true
	@docker rm $(PROJECT_NAME) $(PROJECT_NAME)-dev 2>/dev/null || true
	@docker rmi $(DOCKER_IMAGE) $(PROJECT_NAME):dev 2>/dev/null || true
	@echo "$(GREEN)✅ Docker cleanup completed$(NC)"

# Reset everything
reset: clean clean-docker ## Reset everything (clean + remove database)
	@echo "$(YELLOW)⚠️  This will delete all data. Continue? [y/N]$(NC)"
	@read -r confirm && [ "$$confirm" = "y" ] || { echo "$(GREEN)Cancelled$(NC)"; exit 1; }
	rm -f kapital_assistant.db kapital_assistant_dev.db 2>/dev/null || true
	rm -rf data/ logs/ cache/ 2>/dev/null || true
	@echo "$(GREEN)✅ Reset completed$(NC)"

# Quick development workflow
dev: install-dev init-db start-dev ## Quick development setup and start

# Quick production workflow  
prod: install deploy-check start-prod ## Quick production setup and start

# Create necessary directories
init-dirs: ## Create necessary directories
	@echo "$(BLUE)📁 Creating directories...$(NC)"
	mkdir -p data logs backups cache static/dist
	@echo "$(GREEN)✅ Directories created$(NC)"

# Version info
version: ## Show version information
	@echo "$(BLUE)ℹ️  Version Information:$(NC)"
	@echo "Application: Kapital Bank AI Assistant v1.0.0"
	@echo "Python: $(shell $(PYTHON) --version)"
	@echo "pip: $(shell $(PIP) --version)"
	@test -f .git/HEAD && echo "Git: $(shell git rev-parse --short HEAD)" || echo "Git: Not a git repository"
	@echo "Docker: $(shell docker --version 2>/dev/null || echo 'Not installed')"

# Show useful URLs
urls: ## Show useful application URLs
	@echo "$(BLUE)🔗 Application URLs:$(NC)"
	@echo "Main App:      http://localhost:$(PORT)"
	@echo "API Docs:      http://localhost:$(PORT)/docs"
	@echo "Health Check:  http://localhost:$(PORT)/api/health"
	@echo "Currency API:  http://localhost:$(PORT)/api/currency/rates"
	@echo "Chat API:      http://localhost:$(PORT)/api/chat"