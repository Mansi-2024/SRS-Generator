# ARAQAT — Automated Requirements Analysis & Quality Assessment Tool

A web-based NLP tool that reads software requirement documents and tells you:
- Which sentences are actual **requirements**
- Which are **Functional (FR)** vs **Non-Functional (NFR)**
- Which contain **vague/ambiguous words**
- The overall **quality score** of your document
- A structured **SRS-style export**

## Tech Stack
| Layer | Technology |
|---|---|
| Frontend | React 18 + Vite |
| Backend | Python 3 + Flask |
| NLP | spaCy (en_core_web_sm) |
| Styling | Vanilla CSS (glassmorphism dark theme) |

## Project Structure
```
Software_engineering_CP/
├── backend/
│   ├── app.py              # Flask app & API routes
│   ├── analyzer.py         # NLP core logic
│   ├── requirements.txt    # Python dependencies
│   └── tests/
│       └── test_analyzer.py
├── frontend/
│   ├── src/
│   │   ├── App.jsx
│   │   ├── index.css
│   │   └── components/
│   │       ├── UploadZone.jsx
│   │       ├── MetricsPanel.jsx
│   │       ├── RequirementsTable.jsx
│   │       └── ExportPanel.jsx
│   ├── index.html
│   ├── vite.config.js
│   └── package.json
└── sample_requirements.txt
```

## Getting Started

### 1. Backend Setup
```bash
cd backend

# Create and activate virtual environment
python -m venv venv
venv\Scripts\activate          # Windows
# source venv/bin/activate     # Mac/Linux

# Install Python dependencies
pip install -r requirements.txt

# Download spaCy language model
python -m spacy download en_core_web_sm

# Start Flask server (runs on port 5000)
python app.py
```

### 2. Frontend Setup
```bash
cd frontend

# Install JS dependencies (already done if you ran npm install)
npm install

# Start Vite dev server (runs on port 5173)
npm run dev
```

### 3. Open the App
Go to **http://localhost:5173** in your browser.

## API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/health` | Health check |
| POST | `/api/analyze` | Upload .txt file and get analysis JSON |
| POST | `/api/export` | Send analysis JSON, receive formatted SRS text |

## Running Tests
```bash
cd backend
pytest tests/ -v
```

## Features
- 📄 **Upload** `.txt` requirement documents via drag-and-drop
- ✂️ **Sentence extraction** using spaCy's NLP pipeline
- 🏷 **Classification**: FR vs NFR using keyword scoring
- ⚠️ **Vague word detection**: highlights words like "fast", "user-friendly"
- 📊 **Quality metrics**: counts, percentages, and quality score out of 100
- 📑 **SRS export**: downloadable structured document
