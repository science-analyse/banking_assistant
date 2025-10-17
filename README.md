# 🏦 Bank of Baku RAG Assistant

<div align="center">

### Intelligent Banking Assistant with Advanced RAG Technology

[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Flask](https://img.shields.io/badge/Flask-3.0+-green.svg)](https://flask.palletsprojects.com/)
[![Docker](https://img.shields.io/badge/Docker-Ready-blue.svg)](https://www.docker.com/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Status](https://img.shields.io/badge/Status-Production%20Ready-success.svg)]()

*Answering questions about Bank of Baku cards with AI-powered precision*

[Features](#-features) • [Quick Start](#-quick-start) • [Architecture](#-architecture) • [Deployment](#-deployment) • [Demo](#-demo)

</div>

---

## 📋 Table of Contents

- [Overview](#-overview)
- [Key Features](#-key-features)
- [System Architecture](#-system-architecture)
- [Quick Start](#-quick-start)
- [How It Works](#-how-it-works)
- [Project Structure](#-project-structure)
- [Deployment](#-deployment)
- [Usage Examples](#-usage-examples)
- [API Reference](#-api-reference)
- [Configuration](#-configuration)
- [Contributing](#-contributing)

---

## 🎯 Overview

**Bank of Baku RAG Assistant** is a production-ready AI chatbot that provides accurate, real-time information about Bank of Baku's credit and debit card products using Retrieval-Augmented Generation (RAG) technology.

### 🌟 What Makes It Special?

```mermaid
graph LR
    A[User Question] --> B{Smart Detection}
    B -->|List Question| C[Returns ALL Cards]
    B -->|Specific Question| D[Vector Search]
    D --> E[Top 3 Chunks]
    E --> F[Gemini AI]
    F --> G[Structured Answer]
    C --> H[Complete List]

    style A fill:#667eea
    style B fill:#764ba2
    style C fill:#f093fb
    style D fill:#4facfe
    style G fill:#43e97b
    style H fill:#43e97b
```

### 📊 At a Glance

| Component | Technology | Purpose |
|-----------|-----------|---------|
| **Frontend** | Flask + HTML/CSS/JS | Beautiful chat interface |
| **Backend** | Python 3.11 | RAG system logic |
| **Vector DB** | ChromaDB | Semantic search |
| **Embeddings** | Local (ChromaDB) | Zero API costs |
| **LLM** | Gemini 2.5 Flash | Answer generation |
| **Deployment** | Docker | One-click deploy |

---

## ✨ Key Features

### 🎨 Modern Web Interface

```mermaid
graph TD
    A[Beautiful Chat UI] --> B[Gradient Design]
    A --> C[Mobile Responsive]
    A --> D[Real-time Updates]

    B --> E[Purple/Blue Theme]
    C --> F[Works on All Devices]
    D --> G[Loading Indicators]
    D --> H[Auto-scroll]

    style A fill:#667eea,color:#fff
    style B fill:#764ba2,color:#fff
    style C fill:#f093fb
    style D fill:#4facfe
```

- 💬 **Chat Interface** - Intuitive conversation flow
- 🎨 **Gradient Design** - Modern purple/blue aesthetic
- 📱 **Mobile-First** - Responsive on all devices
- ⚡ **Real-time** - Instant responses with loading states
- 🔗 **Clickable Sources** - Direct links to Bank of Baku pages

### 🧠 Intelligent Question Handling

```mermaid
flowchart TD
    Q[User Question] --> D{Detect Type}

    D -->|List| L[List All Cards]
    D -->|Comparison| C[Format as Table]
    D -->|Features| F[Bullet Points]
    D -->|Pricing| P[Price Breakdown]
    D -->|General| G[Structured Text]

    L --> R1[7 Credit Cards]
    C --> R2[Comparison Table]
    F --> R3[Feature List]
    P --> R4[Clear Pricing]
    G --> R5[Formatted Answer]

    style Q fill:#667eea,color:#fff
    style D fill:#764ba2,color:#fff
    style L fill:#43e97b
    style C fill:#4facfe
    style F fill:#f093fb
    style P fill:#fa709a
    style G fill:#fee140
```

#### Question Types:

1. **📋 List Questions** → Returns ALL available cards
   - *"Hansı kredit kartları var?"*
   - Returns: All 7 credit cards

2. **⚖️ Comparison Questions** → Formatted tables
   - *"Bolkart debet və Platinum fərqi nədir?"*
   - Returns: Comparison table

3. **⭐ Best/Superlative** → Structured recommendations
   - *"Ən yaxşı debet kartı hansıdır?"*
   - Returns: Reasoned answer with bullets

4. **💰 Pricing Questions** → Clear breakdowns
   - *"Kartların qiymətləri nə qədərdir?"*
   - Returns: Organized pricing info

5. **ℹ️ General Questions** → Well-formatted responses
   - *"Maaş kartı haqqında məlumat"*
   - Returns: Detailed information

### 🔍 Advanced RAG Capabilities

- **Smart Retrieval** - Semantic search with ChromaDB
- **Local Embeddings** - No API quota limits
- **Context-Aware** - Uses relevant information only
- **Source Attribution** - Shows data sources
- **Azerbaijani Support** - Full language support

---

## 🏗️ System Architecture

### High-Level Architecture

```mermaid
graph TB
    subgraph "User Layer"
        U[User Browser]
    end

    subgraph "Frontend Layer"
        UI[Flask Web App]
        HTML[HTML/CSS/JS]
        API[REST API]
    end

    subgraph "Backend Layer"
        RAG[RAG System]
        QD[Question Detector]
        VDB[ChromaDB]
        LLM[Gemini 2.5 Flash]
    end

    subgraph "Data Layer"
        SC[Web Scraper]
        DATA[RAG Chunks]
        URLS[Bank URLs]
    end

    U -->|HTTP| UI
    UI --> HTML
    UI --> API
    API --> RAG
    RAG --> QD
    QD -->|List Question| VDB
    QD -->|Specific Question| VDB
    VDB -->|Top K Chunks| LLM
    LLM -->|Answer| API
    API -->|JSON| UI
    UI -->|Rendered HTML| U

    SC -->|Scrapes| URLS
    SC -->|Generates| DATA
    DATA -->|Indexed in| VDB

    style U fill:#667eea,color:#fff
    style UI fill:#764ba2,color:#fff
    style RAG fill:#4facfe,color:#fff
    style VDB fill:#43e97b
    style LLM fill:#fa709a
    style DATA fill:#fee140
```

### RAG Processing Flow

```mermaid
sequenceDiagram
    participant User
    participant Frontend
    participant RAG System
    participant ChromaDB
    participant Gemini

    User->>Frontend: Ask Question
    Frontend->>RAG System: POST /api/query

    RAG System->>RAG System: Detect Question Type

    alt List Question
        RAG System->>ChromaDB: Get All Cards
        ChromaDB-->>RAG System: All Unique Cards
        RAG System->>Gemini: Format List
        Gemini-->>RAG System: Formatted List
    else Specific Question
        RAG System->>ChromaDB: Semantic Search
        ChromaDB-->>RAG System: Top 3 Chunks
        RAG System->>Gemini: Generate Answer
        Gemini-->>RAG System: Structured Answer
    end

    RAG System-->>Frontend: Answer + Sources
    Frontend-->>User: Rendered Response

    Note over User,Gemini: Average Response Time: 2-3 seconds
```

### Data Flow

```mermaid
graph LR
    A[Bank of Baku Website] -->|Web Scraping| B[Raw HTML]
    B -->|BeautifulSoup| C[Clean Text]
    C -->|Chunking| D[Text Chunks]
    D -->|Metadata| E[JSONL Format]
    E -->|Embedding| F[ChromaDB Vectors]

    G[User Query] -->|Embed| H[Query Vector]
    H -->|Search| F
    F -->|Top K| I[Relevant Chunks]
    I -->|Context| J[Gemini LLM]
    J -->|Generate| K[Answer]

    style A fill:#667eea,color:#fff
    style E fill:#43e97b
    style F fill:#4facfe
    style J fill:#fa709a
    style K fill:#fee140
```

---

## 🚀 Quick Start

### Prerequisites

- **Python 3.11+** or **Docker**
- **Gemini API Key** ([Get one here](https://makersuite.google.com/app/apikey))

### Option 1: Automated Deployment (Recommended)

```bash
# Clone repository
git clone https://github.com/your-repo/banking_assistant.git
cd banking_assistant

# Run deployment script
./deploy.sh

# Opens on http://localhost:5001
```

### Option 2: Manual Docker Deployment

```bash
# Ensure .env file exists
echo "LLM_API_KEY=your_gemini_api_key" > .env

# Build and run
docker-compose up -d

# Check health
curl http://localhost:5001/api/health
```

### Option 3: Local Development

```bash
# Install dependencies
pip install -r requirements.txt

# Run application
python run.py

# Opens on http://localhost:5001
```

### Deployment Timeline

```mermaid
gantt
    title Deployment Process
    dateFormat  mm:ss
    section Build
    Install Dependencies    :00:00, 02:00
    Build Docker Image      :02:00, 01:30
    section Deploy
    Start Container         :03:30, 00:30
    Load Data              :04:00, 00:20
    Health Check           :04:20, 00:10
    section Ready
    Service Ready          :04:30, 00:01
```

**Total Time: ~4-5 minutes** ⚡

---

## 🔧 How It Works

### 1. Data Collection

```mermaid
graph TD
    A[Bank URLs] -->|Scraper| B[Fetch HTML]
    B -->|Parse| C[Extract Content]
    C -->|Clean| D[Remove Navigation]
    D -->|Deduplicate| E[Unique Text]
    E -->|Chunk| F[400-word Chunks]
    F -->|Metadata| G[JSONL Format]

    style A fill:#667eea,color:#fff
    style G fill:#43e97b
```

**13 Cards Scraped**:
- 7 Credit Cards
- 6 Debit Cards
- 2,607 clean words
- 100% success rate

### 2. Embedding & Indexing

```mermaid
graph LR
    A[JSONL Chunks] -->|Read| B[Load Data]
    B -->|ChromaDB| C[Generate Embeddings]
    C -->|Store| D[Vector Database]
    D -->|Index| E[Semantic Search Ready]

    style A fill:#667eea,color:#fff
    style C fill:#4facfe
    style E fill:#43e97b
```

**Embedding Model**: ChromaDB Default (all-MiniLM-L6-v2)
- ✅ Free & Local
- ✅ No API quota
- ✅ Fast retrieval

### 3. Query Processing

```mermaid
stateDiagram-v2
    [*] --> ReceiveQuestion
    ReceiveQuestion --> DetectType

    DetectType --> ListQuestion: Contains "hansı kartlar"
    DetectType --> ComparisonQuestion: Contains "fərq"
    DetectType --> FeatureQuestion: Contains "xüsusiyyət"
    DetectType --> PricingQuestion: Contains "qiymət"
    DetectType --> GeneralQuestion: Other

    ListQuestion --> GetAllCards
    ComparisonQuestion --> SemanticSearch
    FeatureQuestion --> SemanticSearch
    PricingQuestion --> SemanticSearch
    GeneralQuestion --> SemanticSearch

    GetAllCards --> FormatList
    SemanticSearch --> Top3Chunks
    Top3Chunks --> GenerateAnswer

    FormatList --> ReturnResult
    GenerateAnswer --> ReturnResult
    ReturnResult --> [*]

    note right of DetectType
        Smart question type
        detection using
        keyword patterns
    end note

    note right of SemanticSearch
        Vector similarity
        search in ChromaDB
    end note
```

### 4. Answer Generation

**Prompt Engineering**:

```
System: You are Bank of Baku card information assistant

Context: [Retrieved chunks with card details]

Formatting Rules:
- Comparison → Use Markdown tables
- Features → Use bullet points
- Pricing → Show clear numbers
- Bold important info

User Question: [User's question in Azerbaijani]

Generate: Structured answer in Azerbaijani
```

---

## 📁 Project Structure

```mermaid
graph TD
    ROOT[banking_assistant/] --> FRONT[frontend/]
    ROOT --> BACK[backend/]
    ROOT --> SCRAPE[scraper/]
    ROOT --> DOCKER[Docker Files]
    ROOT --> CONFIG[Configuration]

    FRONT --> APP[app.py - Flask]
    FRONT --> TEMP[templates/]
    FRONT --> STATIC[static/]

    TEMP --> HTML[index.html]
    STATIC --> CSS[style.css]
    STATIC --> JS[script.js]

    BACK --> RAG[rag_system.py]
    BACK --> INIT[__init__.py]

    SCRAPE --> SCPY[scraper.py]
    SCRAPE --> URLS[urls/]
    SCRAPE --> OUT[output/]

    URLS --> CRED[credit cards urls.txt]
    URLS --> DEB[debet cards urls.txt]

    OUT --> CHUNKS[rag_chunks.jsonl]
    OUT --> RAW[raw_data.json]

    DOCKER --> DF[Dockerfile]
    DOCKER --> DC[docker-compose.yml]

    CONFIG --> ENV[.env]
    CONFIG --> REQ[requirements.txt]
    CONFIG --> RUN[run.py]

    style ROOT fill:#667eea,color:#fff
    style FRONT fill:#764ba2,color:#fff
    style BACK fill:#4facfe,color:#fff
    style SCRAPE fill:#43e97b
    style DOCKER fill:#fa709a
```

### Directory Breakdown

| Directory | Purpose | Key Files |
|-----------|---------|-----------|
| **frontend/** | Web UI | `app.py`, `templates/`, `static/` |
| **backend/** | RAG Logic | `rag_system.py` |
| **scraper/** | Data Collection | `scraper.py`, `urls/`, `output/` |
| **Root** | Config & Deploy | `Dockerfile`, `run.py`, `.env` |

---

## 🌐 Deployment

### Deployment Options Matrix

```mermaid
graph TD
    A[Choose Deployment] --> B{Environment}

    B -->|Local Dev| C[python run.py]
    B -->|Docker Local| D[docker-compose up]
    B -->|VPS/Server| E[./deploy.sh]
    B -->|Cloud Platform| F[Platform-Specific]

    F --> G[Railway]
    F --> H[Render]
    F --> I[DigitalOcean]
    F --> J[AWS/GCP]

    C --> K[Port 5001]
    D --> K
    E --> K
    G --> K
    H --> K
    I --> K
    J --> K

    K --> L[Application Ready!]

    style A fill:#667eea,color:#fff
    style B fill:#764ba2,color:#fff
    style L fill:#43e97b
```

### Quick Deploy Commands

```bash
# 1. Automated (Easiest)
./deploy.sh

# 2. Docker (Production)
docker-compose up -d

# 3. Local (Development)
python run.py
```

### Environment Variables

| Variable | Required | Description | Example |
|----------|----------|-------------|---------|
| `LLM_API_KEY` | ✅ Yes | Gemini API Key | `AIza...` |
| `FLASK_ENV` | ❌ No | Environment | `production` |
| `PORT` | ❌ No | Server Port | `5001` |

### Health Monitoring

```bash
# Check application health
curl http://localhost:5001/api/health

# Expected response
{
  "status": "healthy",
  "indexed_chunks": 13
}
```

---

## 💡 Usage Examples

### Example 1: List All Cards

**Question**: *"Hansı kredit kartları var?"*

**Response**:
```
Bank of Baku-da mövcud olan kredit kartları:

1. Bolkart kredit
2. Bolkart Gold kredit
3. Bolkart Diamond kredit
4. Qızıl kredit kartı
5. Dostlar klubu Gümüş
6. Dostlar klubu Qızıl
7. Dostlar klubu Brilliant

📎 Mənbələr: [Clickable links to each card]
```

### Example 2: Comparison Table

**Question**: *"Bolkart debet və Platinum fərqi nədir?"*

**Response**:

| Xüsusiyyət | Bolkart Debet | Bolkart Platinum |
|------------|---------------|------------------|
| **Qiymət** | Pulsuz | 50-70 AZN |
| **Tip** | Visa/MC | Visa Platinum |
| **Min. Balans** | 300 AZN | 3,000 AZN |
| **Faiz** | 7% | 7% |
| **Keşbek** | ✓ | ✓ |

### Example 3: Feature List

**Question**: *"Keşbek xüsusiyyəti olan kartlar hansılardır?"*

**Response**:
```
Keşbek xüsusiyyətli kartlar:

• Bolkart kredit - Müxtəlif sahələr üzrə keşbek
• Bolkart Gold kredit - Artırılmış keşbek limitləri
• Maaş kartı - 3 kateqoriya seçmək imkanı
• Bolkart debet - Standart keşbek şərtləri
```

---

## 📡 API Reference

### POST `/api/query`

Query the RAG system with a question.

**Request:**
```json
{
  "question": "Hansı kredit kartları var?"
}
```

**Response:**
```json
{
  "answer": "<html formatted answer>",
  "sources": [
    {
      "card_name": "Bolkart kredit",
      "card_type": "credit",
      "url": "https://www.bankofbaku.com/..."
    }
  ],
  "card_count": 7
}
```

### GET `/api/cards`

Get all available cards.

**Parameters:**
- `type` (optional): `"credit"` or `"debet"`

**Response:**
```json
{
  "cards": [...],
  "count": 13
}
```

### GET `/api/health`

Health check endpoint.

**Response:**
```json
{
  "status": "healthy",
  "indexed_chunks": 13
}
```

---

## ⚙️ Configuration

### Docker Configuration

**Resource Limits** (docker-compose.yml):
```yaml
deploy:
  resources:
    limits:
      cpus: '1.0'
      memory: 1G
    reservations:
      cpus: '0.5'
      memory: 512M
```

**Logging**:
```yaml
logging:
  driver: "json-file"
  options:
    max-size: "10m"
    max-file: "3"
```

### Application Settings

Edit `run.py` for custom port:
```python
app.run(host='0.0.0.0', port=5001, debug=False)
```

---

## 📊 Technical Specifications

### Performance Metrics

```mermaid
pie title Response Time Distribution
    "Question Detection" : 100
    "Vector Search" : 300
    "LLM Generation" : 1500
    "Rendering" : 100
```

| Metric | Value |
|--------|-------|
| **Avg Response Time** | 2-3 seconds |
| **Indexed Chunks** | 13 |
| **Cards Covered** | 13 (7 credit + 6 debit) |
| **Embedding Model** | all-MiniLM-L6-v2 |
| **LLM Model** | Gemini 2.5 Flash |
| **Languages** | Azerbaijani |

### Technology Stack

```mermaid
graph LR
    A[Frontend] --> B[Flask 3.0+]
    A --> C[HTML5/CSS3]
    A --> D[Vanilla JS]

    E[Backend] --> F[Python 3.11]
    E --> G[ChromaDB]
    E --> H[Gemini AI]

    I[Deployment] --> J[Docker]
    I --> K[Docker Compose]

    style A fill:#667eea,color:#fff
    style E fill:#764ba2,color:#fff
    style I fill:#4facfe,color:#fff
```

---

## 🎨 Screenshots

### Chat Interface
```
┌─────────────────────────────────────────────────┐
│  🏦 Bank of Baku - Kart Məlumat Köməkçisi      │
│                                         [Ready] │
├─────────────────────────────────────────────────┤
│                                                 │
│  🤖 Salam! Mən Bank of Baku-nun kart          │
│     məhsulları haqqında kömək edə bilərəm.    │
│                                                 │
│  👤 Hansı kredit kartları var?                │
│                                                 │
│  🤖 Bank of Baku-da mövcud olan kredit        │
│     kartları:                                  │
│     1. Bolkart kredit                         │
│     2. Bolkart Gold kredit                    │
│     ...                                        │
│                                                 │
│     📎 Mənbələr: [Links]                      │
│                                                 │
├─────────────────────────────────────────────────┤
│  [Sualınızı yazın...]              [Send 📤]  │
│  [Kredit] [Debet] [Keşbek]                    │
└─────────────────────────────────────────────────┘
```

---

## 🤝 Contributing

We welcome contributions! Here's how:

1. **Fork** the repository
2. **Create** a feature branch
3. **Make** your changes
4. **Test** thoroughly
5. **Submit** a pull request

### Development Setup

```bash
# Clone your fork
git clone https://github.com/your-username/banking_assistant.git

# Create virtual environment
python -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run tests
python -m pytest

# Start development server
python run.py
```

---

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## 🙏 Acknowledgments

- **Bank of Baku** - For providing comprehensive card information
- **Google Gemini** - For powerful LLM capabilities
- **ChromaDB** - For efficient vector storage
- **Flask** - For lightweight web framework

---

## 📞 Support

- 📧 **Email**: support@example.com
- 💬 **Issues**: [GitHub Issues](https://github.com/your-repo/banking_assistant/issues)
- 📖 **Documentation**: [Full Docs](DEPLOYMENT.md)

---

<div align="center">

### 🌟 Star this repository if you find it helpful!

**Built with ❤️ using Claude Code**

[⬆ Back to Top](#-bank-of-baku-rag-assistant)

</div>
