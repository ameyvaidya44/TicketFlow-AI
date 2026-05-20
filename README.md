# TicketFlow AI 🎫🤖

> An intelligent Human-in-the-Loop (HITL) ticket management system powered by a 10-agent AI pipeline for automated ticket classification, resolution, and continuous learning.

[![Python](https://img.shields.io/badge/Python-3.11-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.104-green.svg)](https://fastapi.tiangolo.com/)
[![React](https://img.shields.io/badge/React-18.2-61dafb.svg)](https://reactjs.org/)
[![MongoDB](https://img.shields.io/badge/MongoDB-7.0-green.svg)](https://www.mongodb.com/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

## 📋 Table of Contents

- [Overview](#overview)
- [Key Features](#key-features)
- [System Architecture](#system-architecture)
- [Tech Stack](#tech-stack)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Configuration](#configuration)
- [Usage](#usage)
- [AI Pipeline](#ai-pipeline)
- [Dashboards](#dashboards)
- [API Documentation](#api-documentation)
- [Project Structure](#project-structure)
- [Contributing](#contributing)
- [License](#license)

## 🌟 Overview

TicketFlow AI is an enterprise-grade ticket management system that combines machine learning, natural language processing, and large language models to automate IT support workflows. The system intelligently classifies tickets, predicts priorities and SLA deadlines, generates AI-powered responses, and continuously learns from human feedback.

### What Makes It Special?

- **10-Agent AI Pipeline**: Specialized agents handle classification, sentiment analysis, duplicate detection, response generation, and more
- **Human-in-the-Loop**: Agents review and approve AI suggestions, providing feedback for continuous improvement
- **RAG-Powered Responses**: Retrieval-Augmented Generation using ChromaDB and Mistral-Nemo LLM
- **Real-time Analytics**: Live dashboards with WebSocket updates
- **Explainable AI**: LIME explanations and confidence scores for every prediction
- **Auto-Retraining**: Models automatically retrain when accuracy drops below threshold

## ✨ Key Features

### 🤖 AI-Powered Automation
- **Smart Classification**: Automatically categorizes tickets into 10 categories (Auth, Network, Hardware, etc.)
- **Priority Prediction**: ML-based priority assignment (Low, Medium, High, Critical)
- **SLA Prediction**: Intelligent deadline estimation based on ticket complexity
- **Sentiment Analysis**: Detects frustrated users for priority escalation
- **Duplicate Detection**: Finds similar resolved tickets using semantic search

### 🧠 Intelligent Response Generation
- **RAG Architecture**: Combines ChromaDB vector store with Mistral-Nemo LLM
- **Context-Aware**: Retrieves relevant knowledge base articles for accurate responses
- **Auto-Resolve**: High-confidence tickets (≥78%) get automatic responses
- **Human Review**: Medium-confidence tickets (55-78%) require agent approval

> **🎯 NEW: Confidence Score Improvements**  
> We've optimized the confidence scoring algorithm to reduce unnecessary escalations by 20%. The system now achieves 72% average confidence (up from 56%) through improved ML model tuning, better feature weighting (60/25/20), and smarter routing thresholds. See `CONFIDENCE_IMPROVEMENTS.md` for details.

### 📊 Advanced Analytics
- **Real-time Metrics**: Live ticket volume, resolution rates, and agent workload
- **ML Performance**: Confusion matrices, feature importance, calibration plots
- **Root Cause Analysis**: Pattern detection across similar incidents
- **SLA Monitoring**: Risk alerts for tickets approaching deadlines

### 🔄 Continuous Learning
- **Feedback Loop**: Agent approvals/rejections improve model accuracy
- **Auto-Retraining**: Triggers when accuracy drops below 80%
- **Model Versioning**: Track performance across model iterations
- **Explainability**: LIME explanations for every prediction

## 🏗️ System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         USER SUBMITS TICKET                      │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                    AGENT 1: NLP PREPROCESSING                    │
│  • Text cleaning & normalization                                 │
│  • Tokenization & lemmatization                                  │
│  • Feature extraction (TF-IDF)                                   │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│              AGENT 2: CATEGORY CLASSIFICATION                    │
│  • Random Forest classifier                                      │
│  • 10 categories: Auth, Network, Hardware, Software, etc.        │
│  • Confidence score + LIME explanation                           │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│               AGENT 3: PRIORITY CLASSIFICATION                   │
│  • Gradient Boosting classifier                                  │
│  • 4 levels: Low, Medium, High, Critical                         │
│  • Considers urgency keywords & sentiment                        │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                  AGENT 4: SLA PREDICTION                         │
│  • Random Forest regressor                                       │
│  • Predicts resolution time in hours                             │
│  • Calculates deadline timestamp                                 │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                 AGENT 5: SENTIMENT ANALYSIS                      │
│  • TextBlob polarity analysis                                    │
│  • Detects frustrated users (polarity < -0.3)                    │
│  • Triggers escalation override                                  │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                AGENT 6: DUPLICATE DETECTION                      │
│  • ChromaDB semantic search                                      │
│  • Finds similar resolved tickets (>70% similarity)              │
│  • Provides resolution history                                   │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                 AGENT 7: CONFIDENCE SCORING                      │
│  • Aggregates prediction confidence                              │
│  • Applies business rules & overrides                            │
│  • Determines routing: AUTO_RESOLVE vs SUGGEST_TO_AGENT          │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│            AGENT 8: RESPONSE GENERATION (RAG)                    │
│  • Retrieves top 3 relevant KB articles from ChromaDB            │
│  • Sends context to Mistral-Nemo LLM via Ollama                  │
│  • Generates personalized resolution steps                       │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                  AGENT 9: HITL ROUTING                           │
│  • High confidence (≥78%): AUTO_RESOLVE                          │
│  • Medium confidence (55-78%): SUGGEST_TO_AGENT                  │
│  • Low confidence (<55%): ESCALATE_TO_HUMAN                      │
│  • Security/Database: Always escalate                            │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│              AGENT 10: FEEDBACK & RETRAINING                     │
│  • Collects agent approvals/rejections                           │
│  • Stores feedback in MongoDB                                    │
│  • Triggers retraining when accuracy < 80%                       │
│  • Updates models with new training data                         │
└─────────────────────────────────────────────────────────────────┘
```

## 🛠️ Tech Stack

### Backend
- **Framework**: FastAPI (Python 3.11)
- **Database**: MongoDB (Motor async driver)
- **Vector Store**: ChromaDB (embeddings & semantic search)
- **ML Models**: scikit-learn (Random Forest, Gradient Boosting)
- **LLM**: Mistral-Nemo via Ollama
- **NLP**: TextBlob, NLTK, spaCy
- **Explainability**: LIME
- **Real-time**: WebSockets

### Frontend
- **Framework**: React 18.2
- **Styling**: Tailwind CSS
- **Charts**: Recharts
- **HTTP Client**: Axios
- **State Management**: React Context API
- **Routing**: React Router v6

### DevOps
- **Containerization**: Docker (optional)
- **API Docs**: Swagger/OpenAPI (auto-generated)
- **Logging**: Loguru
- **Environment**: python-dotenv

## 📦 Prerequisites

Before installation, ensure you have:

- **Python 3.11+** ([Download](https://www.python.org/downloads/))
- **Node.js 18+** and npm ([Download](https://nodejs.org/))
- **MongoDB 7.0+** ([Download](https://www.mongodb.com/try/download/community))
- **Ollama** with Mistral-Nemo model ([Install Guide](https://ollama.ai/))
- **Git** ([Download](https://git-scm.com/))

### Install Ollama & Mistral-Nemo

```bash
# Install Ollama (Linux/Mac)
curl -fsSL https://ollama.ai/install.sh | sh

# Windows: Download from https://ollama.ai/download

# Pull Mistral-Nemo model
ollama pull mistral-nemo
```

## 🚀 Installation

### 1. Clone Repository

```bash
git clone https://github.com/jayshinde0/TicketFlow-AI.git
cd TicketFlow-AI
```

### 2. Backend Setup

```bash
cd backend

# Create virtual environment
python -m venv venv

# Activate virtual environment
# Windows:
venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Create .env file
cp .env.example .env
# Edit .env with your MongoDB URI and settings
```

### 3. Frontend Setup

```bash
cd ../frontend

# Install dependencies
npm install

# Create .env file (optional)
echo "REACT_APP_API_URL=http://localhost:8000" > .env
```

### 4. Train ML Models

```bash
cd ../backend

# Train initial models (generates synthetic data)
python ml/train.py

# This creates models in ml/artifacts/:
# - category_model.pkl
# - priority_model.pkl
# - sla_model.pkl
# - tfidf_vectorizer.pkl
```

### 5. Seed Database

```bash
# Create default users (admin, agent, user)
python seed_users.py
```

## ⚙️ Configuration

### Backend (.env)

```env
# MongoDB
MONGODB_URI=mongodb://localhost:27017
DATABASE_NAME=ticketflow_ai

# JWT Authentication
SECRET_KEY=your-secret-key-here-change-in-production
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# Ollama LLM
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=mistral-nemo

# ChromaDB
CHROMA_PERSIST_DIR=./chroma_data

# ML Settings
CONFIDENCE_THRESHOLD=0.85
RETRAINING_THRESHOLD=0.80
MIN_FEEDBACK_SAMPLES=50

# CORS
CORS_ORIGINS=http://localhost:3000,http://localhost:3001
```

### Frontend (.env)

```env
REACT_APP_API_URL=http://localhost:8000
REACT_APP_WS_URL=ws://localhost:8000
```

## 🎯 Usage

### Start Services

#### Option 1: Manual Start

```bash
# Terminal 1: Start MongoDB
mongod --dbpath /path/to/data

# Terminal 2: Start Ollama
ollama serve

# Terminal 3: Start Backend
cd backend
source venv/bin/activate  # or venv\Scripts\activate on Windows
uvicorn main:app --reload --port 8000

# Terminal 4: Start Frontend
cd frontend
npm start
```

#### Option 2: Use Helper Scripts

**Windows (PowerShell):**
```powershell
.\check_services.ps1
```

**Linux/Mac:**
```bash
chmod +x check_services.sh
./check_services.sh
```

### Access Application

- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs
- **MongoDB**: mongodb://localhost:27017

### Default Credentials

| Role  | Email              | Password |
|-------|-------------------|----------|
| Admin | admin@company.com | admin123 |
| Agent | agent@company.com | agent123 |
| User  | user@company.com  | user123  |

## 🤖 AI Pipeline

### 1. Ticket Submission Flow

```python
# User submits ticket
POST /api/tickets/
{
  "title": "Cannot access VPN",
  "description": "VPN client shows error 800...",
  "user_email": "user@company.com"
}
```

### 2. AI Processing

```
NLP Preprocessing → Category (Network, 92%) → Priority (High, 88%) 
→ SLA (4 hours) → Sentiment (Neutral) → Duplicates (2 similar)
→ Confidence (89%) → RAG Response → AUTO_RESOLVE
```

### 3. Response Generation (RAG)

```python
# 1. Embed ticket description
embedding = embedding_service.generate(description)

# 2. Search ChromaDB for similar KB articles
results = chroma.query(embedding, n_results=3)

# 3. Build context for LLM
context = "\n".join([doc["content"] for doc in results])

# 4. Generate response with Mistral-Nemo
prompt = f"""
Based on this knowledge:
{context}

Resolve this ticket:
{description}
"""
response = ollama.generate(model="mistral-nemo", prompt=prompt)
```

### 4. HITL Decision

- **≥85% confidence + no overrides**: Auto-resolve (send response to user)
- **60-85% confidence**: Suggest to agent (requires approval)
- **<60% confidence**: Escalate to human (manual handling)
- **Security/Database category**: Always escalate (business rule)

## 📊 Dashboards

### 1. User Dashboard
- Submit new tickets
- View my tickets (open, resolved, closed)
- Track SLA deadlines
- View AI-generated responses

### 2. Agent Dashboard
- Review queue (tickets needing approval)
- Approve/reject AI suggestions
- Edit AI responses before sending
- Escalate complex tickets
- View similar resolved tickets

### 3. Analytics Dashboard
- **Ticket Metrics**: Volume trends, resolution rates, avg resolution time
- **Category Distribution**: Pie chart of ticket categories
- **Priority Breakdown**: Bar chart of priority levels
- **Sentiment Analysis**: Positive/neutral/negative distribution
- **Agent Workload**: Tickets per agent, avg handling time
- **SLA Compliance**: On-time vs breached tickets
- **Resolution Funnel**: Auto-resolved → Agent-approved → Escalated

### 4. ML Performance Dashboard
- **Confusion Matrices**: Category, priority, SLA predictions
- **Feature Importance**: Top features driving predictions
- **Calibration Plots**: Confidence vs actual accuracy
- **Model Metrics**: Precision, recall, F1-score per class
- **Training History**: Accuracy trends across model versions

## 📚 API Documentation

### Authentication

```bash
# Login
POST /api/auth/login
{
  "email": "agent@company.com",
  "password": "agent123"
}

# Response
{
  "access_token": "eyJhbGc...",
  "token_type": "bearer",
  "user": {...}
}

# Use token in headers
Authorization: Bearer eyJhbGc...
```

### Tickets

```bash
# Create ticket
POST /api/tickets/
{
  "title": "Password reset issue",
  "description": "Cannot reset my password...",
  "user_email": "user@company.com"
}

# Get ticket details
GET /api/tickets/{ticket_id}

# Get my tickets
GET /api/tickets/my-tickets

# Get agent queue
GET /api/tickets/agent-queue
```

### Feedback (HITL)

```bash
# Approve AI suggestion
POST /api/feedback/{ticket_id}/approve
{
  "edited_response": "Optional edited response"
}

# Reject AI suggestion
POST /api/feedback/{ticket_id}/reject
{
  "reason": "Incorrect category",
  "correct_category": "Hardware"
}

# Escalate ticket
POST /api/feedback/{ticket_id}/escalate
{
  "reason": "Requires senior engineer"
}
```

### Analytics

```bash
# Get dashboard stats
GET /api/analytics/stats

# Get ticket volume over time
GET /api/analytics/ticket-volume?days=30

# Get category distribution
GET /api/analytics/category-distribution

# Get ML performance metrics
GET /api/analytics/ml-performance
```

### Admin

```bash
# Trigger model retraining
POST /api/admin/retrain

# Get model info
GET /api/admin/model-info

# Get system health
GET /api/admin/health
```

## 📁 Project Structure

```
TicketFlow-AI/
├── backend/
│   ├── core/
│   │   ├── config.py              # Configuration settings
│   │   ├── database.py            # MongoDB connection
│   │   ├── security.py            # JWT authentication
│   │   └── websocket_manager.py   # WebSocket connections
│   ├── ml/
│   │   ├── models/
│   │   │   ├── category_classifier.py
│   │   │   ├── priority_classifier.py
│   │   │   └── sla_predictor.py
│   │   ├── artifacts/             # Trained models (.pkl)
│   │   ├── data_loader.py         # Synthetic data generation
│   │   ├── train.py               # Model training script
│   │   ├── evaluate.py            # Model evaluation
│   │   └── feature_engineering.py # Feature extraction
│   ├── models/
│   │   ├── ticket.py              # Ticket schema
│   │   ├── user.py                # User schema
│   │   ├── feedback.py            # Feedback schema
│   │   └── audit.py               # Audit log schema
│   ├── routers/
│   │   ├── tickets.py             # Ticket endpoints
│   │   ├── auth.py                # Authentication
│   │   ├── feedback.py            # HITL feedback
│   │   ├── analytics.py           # Analytics endpoints
│   │   ├── agents.py              # Agent queue
│   │   └── admin.py               # Admin operations
│   ├── services/
│   │   ├── classifier_service.py  # ML classification
│   │   ├── llm_service.py         # Ollama integration
│   │   ├── embedding_service.py   # Text embeddings
│   │   ├── retrieval_service.py   # ChromaDB search
│   │   ├── sentiment_service.py   # Sentiment analysis
│   │   ├── duplicate_service.py   # Duplicate detection
│   │   ├── confidence_service.py  # Confidence scoring
│   │   ├── hitl_service.py        # HITL routing
│   │   ├── explainability_service.py # LIME explanations
│   │   ├── retraining_service.py  # Auto-retraining
│   │   └── notification_service.py # Notifications
│   ├── tasks/
│   │   ├── ticket_tasks.py        # Background tasks
│   │   └── background_tasks.py    # Scheduled jobs
│   ├── utils/
│   │   ├── helpers.py             # Utility functions
│   │   ├── metrics.py             # Performance metrics
│   │   └── text_cleaner.py        # Text preprocessing
│   ├── main.py                    # FastAPI app
│   ├── requirements.txt           # Python dependencies
│   └── .env.example               # Environment template
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── ticket/            # Ticket components
│   │   │   ├── agent/             # Agent review components
│   │   │   ├── dashboard/         # Dashboard widgets
│   │   │   ├── ml/                # ML visualization
│   │   │   └── ui/                # Shared UI components
│   │   ├── pages/
│   │   │   ├── Dashboard.jsx      # User dashboard
│   │   │   ├── AgentQueue.jsx     # Agent review queue
│   │   │   ├── Analytics.jsx      # Analytics dashboard
│   │   │   ├── SubmitTicket.jsx   # Ticket submission
│   │   │   └── Login.jsx          # Authentication
│   │   ├── contexts/
│   │   │   ├── AuthContext.jsx    # Auth state
│   │   │   └── NotificationContext.jsx
│   │   ├── hooks/
│   │   │   ├── useTickets.js      # Ticket operations
│   │   │   ├── useWebSocket.js    # Real-time updates
│   │   │   └── useAnalytics.js    # Analytics data
│   │   ├── services/
│   │   │   └── api.js             # API client
│   │   ├── App.jsx                # Main app component
│   │   └── index.jsx              # Entry point
│   ├── package.json               # Node dependencies
│   └── tailwind.config.js         # Tailwind config
├── SYSTEM_ARCHITECTURE.md         # Detailed architecture
├── SETUP_GUIDE.md                 # Installation guide
├── README.md                      # This file
├── .gitignore                     # Git ignore rules
└── check_services.sh/ps1          # Service checker scripts
```

## 🔧 Troubleshooting

### MongoDB Connection Issues

```bash
# Check if MongoDB is running
mongosh

# If not running, start it
mongod --dbpath /path/to/data
```

### Ollama Not Responding

```bash
# Check Ollama status
ollama list

# Restart Ollama
ollama serve

# Verify Mistral-Nemo is installed
ollama pull mistral-nemo
```

### Models Not Found

```bash
# Retrain models
cd backend
python ml/train.py

# Check artifacts directory
ls ml/artifacts/
# Should see: category_model.pkl, priority_model.pkl, sla_model.pkl
```

### CORS Errors

```bash
# Update backend/.env
CORS_ORIGINS=http://localhost:3000

# Restart backend
uvicorn main:app --reload
```

### WebSocket Connection Failed

```bash
# Check backend is running on port 8000
curl http://localhost:8000/health

# Check frontend WebSocket URL in .env
REACT_APP_WS_URL=ws://localhost:8000
```

## 🤝 Contributing

Contributions are welcome! Please follow these steps:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

### Development Guidelines

- Follow PEP 8 for Python code
- Use ESLint/Prettier for JavaScript
- Write unit tests for new features
- Update documentation for API changes
- Add comments for complex logic

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- **FastAPI** - Modern Python web framework
- **Ollama** - Local LLM inference
- **ChromaDB** - Vector database for embeddings
- **scikit-learn** - Machine learning library
- **React** - Frontend framework
- **Tailwind CSS** - Utility-first CSS

## 📞 Support

For questions or issues:

- **GitHub Issues**: [Create an issue](https://github.com/jayshinde0/TicketFlow-AI/issues)
- **Email**: jayshinde0@example.com
- **Documentation**: See [SYSTEM_ARCHITECTURE.md](SYSTEM_ARCHITECTURE.md) and [SETUP_GUIDE.md](SETUP_GUIDE.md)

## 🗺️ Roadmap

- [ ] Multi-language support (i18n)
- [ ] Email notifications
- [ ] Slack/Teams integration
- [ ] Advanced analytics (predictive insights)
- [ ] Mobile app (React Native)
- [ ] Docker Compose setup
- [ ] Kubernetes deployment
- [ ] A/B testing for AI responses
- [ ] Voice-to-ticket (speech recognition)
- [ ] Custom model fine-tuning UI

---

**Built with ❤️ by Team  Sankalp**

⭐ Star this repo if you find it helpful!
