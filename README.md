# VeritasAI – Multi-Agent Legal Research System

VeritasAI is an advanced multi-agent system for comprehensive legal case research and analysis. It orchestrates multiple AI agents to parse queries, search legal databases, summarize case opinions, extract citations, analyze arguments, and provide insights through a modern React frontend.

## 🚀 Quick Start

### Prerequisites
- **Python 3.10+** (Windows users: prefer Python 3.10/3.11 for best compatibility)
- **Node.js 18+**
- **CourtListener API key** (get from [CourtListener](https://www.courtlistener.com/api/))
- **MongoDB** (atlas cloud instance)

### Setup Instructions

#### 1. Clone and Setup Environment
```bash
# Clone the repository
git clone <repository-url>
cd VeritasAI

# Create and activate virtual environment
python -m venv venv

# Windows
venv\Scripts\activate

# Linux/Mac
source venv/bin/activate
```

#### 2. Install Dependencies
```bash
# Install Python dependencies
pip install -r requirements.txt

# Install frontend dependencies
cd frontend
npm install
cd ..
```

#### 3. Environment Configuration
Create a `.env` file in the root directory:
```env
# Required Environment Variables
OPENAI_API_KEY=your_openai_api_key_here
GOOGLE_CLIENT_ID=your_google_client_id_here
GOOGLE_CLIENT_SECRET=your_google_client_secret_here
MONGO_URI=your_mongodb_atlas_uri_here
DATABASE_NAME=veritas_ai
LLM_MODEL=gpt-4o-mini
API_BASE_URL=https://api.openai.com/v1
TEMPERATURE=0.4
SESSION_SECRET_KEY=your_session_secret_key_here
JWT_SECRET=your_jwt_secret_key_here
COURTLISTENER_API_KEY=your_courtlistener_api_key_here
ENCRYPTION_KEY=your_32_character_encryption_key_here
```

#### 4. Start the Application
```bash
# Start all backend services
python run.py

# In a separate terminal, start the frontend
cd frontend
npm start
```

The application will be available at:
- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:8000

## 📖 Usage Guide

### Getting Started
1. **Authentication**: Log in with your Google account
2. **Query Search**: Enter legal queries in natural language
3. **PDF Analysis**: Upload legal documents for comprehensive analysis
4. **History**: Access your previous searches and results

### Features

#### 🔍 Query-Based Research
- Enter legal questions in natural language
- Get comprehensive analysis including:
  - Case summaries
  - Legal issues identified
  - Argument analysis
  - Citation verification
  - Analytics and patterns

#### 📄 PDF Document Analysis
- Upload legal PDF documents
- Extract and analyze case text
- Generate comprehensive summaries
- Identify key legal arguments and citations

#### 📊 Analytics Dashboard
- View legal patterns and trends
- Analyze jurisdictional insights
- Track precedential analysis
- Monitor citation networks

### Example Queries
```
- "contract breach damages remedies"
- "constitutional rights violations first amendment"
- "employment discrimination workplace harassment"
- "intellectual property patent infringement"
- "criminal procedure fourth amendment search"
```

## 👥 Contributors

### Team Members & Responsibilities

| Member | Role | Components |
|--------|------|------------|
| **Chamod** | **Team Leader** | Orchestrator, Argument Agent |
| **Sandun** | **Backend Developer** | Citation Agent, Frontend |
| **Monali** | **AI Specialist** | Summarization Agent, Analytics & Patterns Agent |
| **Lihini** | **Research Specialist** | Issue Agent |

### Individual Contributions

#### Chamod (Team Leader)
- **Orchestrator**: Main coordination system that manages all agents
- **Argument Agent**: Analyzes legal arguments and reasoning
- **System Architecture**: Overall system design and integration

#### Sandun (Backend Developer)
- **Citation Agent**: Extracts and verifies legal citations
- **Frontend Development**: React-based user interface
- **API Integration**: CourtListener API integration

#### Monali (AI Specialist)
- **Summarization Agent**: Creates comprehensive case summaries
- **Analytics Agent**: Generates insights and pattern analysis
- **AI Models**: LLM integration and prompt engineering

#### Lihini (Research Specialist)
- **Issue Agent**: Identifies and extracts legal issues
- **Legal Research**: Domain expertise and validation
- **Quality Assurance**: Legal accuracy and compliance

## 🏗️ Repository Structure

```
VeritasAI/
├── 📁 agents/                          # AI Agent Services
│   ├── 📁 analytics/                   # Analytics & Patterns Agent (Monali)
│   │   └── analytics_agent.py
│   ├── 📁 argument/                    # Argument Analysis Agent (Chamod)
│   │   └── argument_agent.py
│   ├── 📁 citation/                    # Citation Extraction Agent (Sandun)
│   │   ├── citation_agent.py
│   │   └── citation_service.py
│   ├── 📁 issue/                       # Issue Extraction Agent (Lihini)
│   │   └── issue_agent.py
│   ├── 📁 pdf/                         # PDF Processing Service
│   │   └── pdf_service.py
│   └── 📁 summary/                     # Summarization Agent (Monali)
│       └── summarization_agent.py
├── 📁 common/                          # Shared Utilities
│   ├── config.py                       # Configuration management
│   ├── encryption.py                   # Data encryption utilities
│   ├── logging.py                      # Logging configuration
│   ├── models.py                       # Data models
│   ├── responsible_ai.py              # Responsible AI framework
│   ├── security.py                     # Security utilities
│   └── utils.py                        # Common utilities
├── 📁 controller/                      # Main Orchestration (Chamod)
│   ├── auth_controller.py             # Authentication controller
│   └── orchestrator.py                # Main orchestrator service
├── 📁 data/                           # Data Storage
│   └── 📁 embeddings/                 # Vector embeddings
├── 📁 frontend/                        # React Frontend (Sandun)
│   ├── 📁 public/
│   ├── 📁 src/
│   │   ├── 📁 components/
│   │   │   ├── ChatInterface.js        # Main chat interface
│   │   │   ├── CitationsSection.js     # Citations display
│   │   │   ├── ExportActions.js        # Export functionality
│   │   │   ├── HomePage.js             # Landing page
│   │   │   ├── NavBar.js               # Navigation bar
│   │   │   ├── PDFUpload.js            # PDF upload component
│   │   │   └── ResultSection.js        # Results display
│   │   ├── App.js                      # Main app component
│   │   └── index.js                    # App entry point
│   ├── package.json                    # Frontend dependencies
│   └── tailwind.config.js             # Tailwind CSS config
├── 📁 model/                          # Data Models & Services
│   ├── case_indexer.py                 # Case indexing service
│   ├── citation_verifier.py           # Citation verification
│   ├── courtlistener_advanced.py      # Advanced CourtListener features
│   ├── courtlistener_client.py         # CourtListener API client
│   ├── issue_extractor.py              # Issue extraction logic (Lihini)
│   ├── legal_term_expander.py          # Legal term expansion
│   └── user_model.py                   # User data models
├── 📁 view/                           # API Views
│   ├── api_view.py                     # Main API endpoints
│   └── auth_view.py                    # Authentication endpoints
├── 📁 logs/                           # Application logs
├── 📁 tests/                          # Test files
├── 📁 venv/                           # Virtual environment
├── run.py                             # Application entry point
├── requirements.txt                   # Python dependencies
└── README.md                          # This file
```

## 🔧 Architecture Overview

### Multi-Agent System
- **Orchestrator** (Port 8000): Main coordination service
- **Citation Service** (Port 8003): Citation extraction and verification
- **PDF Service** (Port 8005): PDF document processing
- **Frontend** (Port 3000): React-based user interface

### Key Features
- **Responsible AI Framework**: IBM-based AI ethics and compliance
- **Data Encryption**: End-to-end encryption for user data
- **Multi-Service Architecture**: Microservices for scalability
- **Real-time Processing**: Live agent coordination and status updates

## 📝 License

This project is for academic and research purposes. Please verify downstream data source terms (CourtListener API) before commercial use.

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Submit a pull request

## 📞 Support

For questions or issues, please contact the development team or create an issue in the repository.

---

**Built with ❤️ by the VeritasAI Team**
