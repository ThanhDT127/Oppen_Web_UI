# Open WebUI Stack

A fully-featured AI chat platform with middleware authentication, quota management, and multi-provider LLM support.

## 🚀 Quick Start

```bash
# Clone & setup
git clone https://github.com/your-org/oppen-web-ui.git
cd oppen-web-ui

# Configure
cp .env.example .env
# Edit .env with your API keys

# Run
docker compose up -d

# Access
open http://localhost:3000
```

## 📦 Architecture

```
User → Open WebUI (3000) → Middleware (5000) → LiteLLM (4000) → OpenAI/Gemini
                                                   ↓
                                            PostgreSQL (5432)
```

## 🤖 Supported Models

| Prefix | Type | Examples |
|--------|------|----------|
| `mm-` | Multimodal (text+vision) | `mm-gpt-5`, `mm-gemini-2.5-flash` |
| `img-` | Image Generation | `img-dalle-3`, `img-gemini-flash` |
| `tts-` | Text-to-Speech | `tts-gpt-4o-mini` |
| `stt-` | Speech-to-Text | `stt-gpt-4o`, `stt-gpt-4o-mini` |

## 📖 Documentation

| Document | Description |
|----------|-------------|
| [USER_GUIDE_VI.md](docs/USER_GUIDE_VI.md) | Hướng dẫn sử dụng (Vietnamese) |
| [DEPLOYMENT_VI.md](docs/DEPLOYMENT_VI.md) | Hướng dẫn triển khai (Vietnamese) |
| [ARCHITECTURE.md](docs/ARCHITECTURE.md) | System architecture |
| [API_REFERENCE.md](docs/API_REFERENCE.md) | API endpoints |
| [USER_MANAGEMENT.md](docs/USER_MANAGEMENT.md) | User & quota management |
| [DASHBOARD.md](docs/DASHBOARD.md) | Admin dashboard |

## ⚡ Commands

```bash
# Start all services
docker compose up -d

# Stop all services
docker compose down

# Rebuild after config changes
docker compose up -d --build

# View logs
docker compose logs -f middleware

# Health check
curl http://localhost:5000/health
```

## 🔑 API Keys Required

- **OpenAI**: [platform.openai.com](https://platform.openai.com)
- **Gemini**: [aistudio.google.com](https://aistudio.google.com)

## 📁 Project Structure

```
├── docker-compose.yml      # Main orchestration
├── .env.example            # Environment template
├── litellm/
│   └── litellm_config.yaml # Model definitions
├── llm-mw/                 # Middleware source
│   ├── api/                # API endpoints
│   ├── core/               # Auth, quota, cost
│   ├── data/               # users.json, prices.json
│   └── Dockerfile
├── docs/                   # Documentation
└── tests/                  # Playwright tests
```

## 🧪 Testing

```bash
cd tests
npm install
npx playwright test
```

## 📄 License

MIT
