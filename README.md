# Her Circle

Her Circle is a dedicated women's reproductive health assistant designed to provide a calm, grounded, and medical-first space for understanding your body. Unlike general web searches, Her Circle focuses on providing high-quality, cited medical information alongside synthesized lived experiences from real women.

##  Core Features

-   **Medical-First Grounding (RAG)**: Uses Retrieval-Augmented Generation to provide answers based on curated medical sources and trusted organizations.
*   **Lived experience Context**: Synthesizes relevant discussions from real-world communities (Reddit) to provide balanced, empathetic context.
*   **Safety & Scope Focus**: Automatically identifies urgent symptoms and redirects out-of-scope queries to ensure a focused health experience.
*   **Premium UI/UX**: A calm, interactive interface with smooth scroll-reveal animations and a dynamic cursor-following glow for a polished modern feel.
*   **Multilingual Support**: Intelligent detection and response in the user's preferred language.

##  Tech Stack

### Frontend
- **Framework**: React 18
- **Build Tool**: Vite
- **Styling**: Vanilla CSS (Custom Animation System)
- **Communication**: Axios for API interaction

### Backend
- **Framework**: Flask (Python)
- **LLM**: Llama 3 (via Groq API)
- **Vector Database**: ChromaDB (for Medical RAG)
- **Data Gathering**: Custom scrapers for medical sources and Reddit threads

##  Getting Started

### Prerequisites
- Python 3.9+
- Node.js 16+
- A Groq API Key (get one at [console.groq.com](https://console.groq.com))

### Backend Setup
1. Navigate to the `backend/` directory.
2. Create and activate a virtual environment:
   ```bash
   python -m venv venv
   
   # To activate on Windows:
   venv\Scripts\activate          # (Command Prompt)
   .\venv\Scripts\Activate.ps1   # (PowerShell)
   source venv/Scripts/activate   # (Git Bash)
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Create a `.env` file in the `backend/` folder:
   ```env
   GROQ_API_KEY=your_api_key_here
   HERCIRCLE_TOPIC_CACHE_TTL_SECONDS=21600
   ```
5. Run the server:
   ```bash
   python app.py
   ```

### Frontend Setup
1. Navigate to the `frontend/` directory.
2. Install dependencies:
   ```bash
   npm install
   ```
3. Start the development server:
   ```bash
   npm run dev
   ```
4. Open the application at `http://localhost:5173`.

##  Project Structure

```text
her-circle/
├── backend/
│   ├── data/
│   │   ├── chroma/           # Vector database for medical RAG
│   │   ├── curated_sources.json
│   │   └── rag_manifest.json
│   ├── venv/                 # Python virtual environment (ignored by git)
│   ├── app.py                # Main Flask API and LLM orchestration
│   ├── ingest.py             # Data ingestion script for RAG
│   ├── rag.py                # Medical retrieval logic
│   ├── reddit.py             # Reddit scraper and synthesis logic
│   ├── requirements.txt      # Backend dependencies
│   └── scraper.py            # Primary web scraper for medical sources
├── frontend/
│   ├── public/               # Static assets (favicons, etc.)
│   ├── src/
│   │   ├── App.css           # Global design system & animations


│   │   ├── App.jsx           # Main application shell & logic
│   │   ├── index.css         # Basic resets
│   │   └── main.jsx          # React entry point
│   ├── index.html            # Main HTML entry
│   ├── package.json          # Frontend dependencies
│   └── vite.config.js        # Vite configuration
└── README.md                 # Project documentation
```
