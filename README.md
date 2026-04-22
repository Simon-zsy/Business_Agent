# Business Agent

An automated business intelligence agent with two independent pipelines:

- **`news_agent`** — fetches business news, summarizes with AI, generates a keyword heatmap, and emails an HTML report
- **`job_agent`** — reads your resume, finds matching internship listings, ranks them by relevance, and emails a report with links

---

## Project Structure

```
Business_Agent/
├── news_agent/          # News intelligence pipeline
│   ├── agent.py         # Entry point
│   ├── news.py          # GNews API, source filtering, semantic similarity
│   ├── summarizer.py    # Azure OpenAI summarization
│   ├── heatmap.py       # Doubao image generation (bubble heatmap)
│   ├── email_sender.py  # SMTP sending + HTML report generation
│   ├── test_email.py    # Standalone email test with sample data
│   └── config.txt       # Credentials and keywords
│
└── job_agent/           # Internship job finder pipeline
    ├── agent.py         # Entry point
    ├── job_finder.py    # Adzuna API, company filtering, semantic ranking
    ├── resume_parser.py # Resume reading + Azure OpenAI profile extraction
    ├── email_sender.py  # SMTP sending + HTML report generation
    ├── resume.txt       # Your resume (create this before running)
    └── config.txt       # Credentials, Adzuna keys, and target companies
```

---

## News Agent

### Pipeline

```
config.txt
    │
    ▼
[1] Fetch News (GNews API)
    │  └─ Filter to trusted sources (Reuters, Bloomberg, CNBC, etc.)
    │  └─ Rank articles by semantic similarity to your keywords
    ▼
[2] Extract Trending Keywords
    │  └─ Count keyword-to-article assignments
    ▼
[3] Generate AI Summary (Azure OpenAI / GPT-4o)
    │  └─ 200-300 word paragraph from top 8 articles
    ▼
[4] Generate Heatmap Image (Doubao / ByteDance)
    │  └─ Bubble chart: bubble size ∝ keyword frequency
    ▼
[5] Send Email Report (SMTP)
       └─ HTML email with trending table, heatmap, summary, and articles by category
```

### Setup

**1. Install dependencies**

```bash
pip install openai sentence-transformers torch requests
```

**2. Configure `news_agent/config.txt`**

```
EMAIL=your_email@gmail.com
PASSWORD=your_gmail_app_password

AZURE_API_KEY=your_azure_openai_key
AZURE_API_VERSION=2025-02-01-preview
AZURE_ENDPOINT=https://your-resource.openai.azure.com
AZURE_MODEL=gpt-4o

# Keywords Configuration
stock
market
earnings
economy
nasdaq
```

Lines after `# Keywords Configuration` with no `=` sign are treated as search keywords — one per line.

**3. Run**

```bash
cd news_agent
python agent.py
```

To verify email credentials only (no API calls):

```bash
cd news_agent
python test_email.py
```

---

## Job Agent

### Pipeline

```
resume.txt + config.txt
    │
    ▼
[1] Parse Resume
    │  └─ Reads .txt or .pdf
    ▼
[2] Extract Candidate Profile (Azure OpenAI / GPT-4o)
    │  └─ Skills, target roles, one-line summary
    ▼
[3] Fetch Internship Listings (Adzuna API)
    │  └─ Searches by role keywords + location
    ▼
[4] Filter by Company Whitelist
    │  └─ Keeps only listings from your target companies (optional)
    ▼
[5] Rank by Semantic Similarity
    │  └─ Cosine similarity between resume and each job description
    ▼
[6] Output Results
       ├─ Print ranked table to terminal (company, title, location, match %, link)
       └─ Send HTML email report with apply links
```

### Setup

**1. Install dependencies**

```bash
pip install openai sentence-transformers torch PyPDF2
```

(`PyPDF2` is only needed if your resume is a PDF — skip it if using a `.txt` file.)

**2. Get an Adzuna API key**

1. Go to [https://developer.adzuna.com](https://developer.adzuna.com) and create a free account.
2. Register an application — you will receive an **App ID** and an **App Key**.
3. The free tier allows 250 requests/day, which is more than enough for this pipeline.

**3. Write your resume**

Create `job_agent/resume.txt` with your resume content in plain text. For example:

```
Jane Doe | jane@email.com

Education:
BSc Computer Science, HKUST, 2026

Skills:
Python, SQL, Machine Learning, React, Git, TensorFlow

Experience:
- Research Assistant, HKUST AI Lab (2024): built NLP data pipelines
- Part-time Developer, Startup X (2023): REST APIs with Flask + PostgreSQL

Projects:
- Stock price predictor using LSTM (Python, TensorFlow)
- Full-stack e-commerce site (React + Node.js)
```

A PDF resume also works — just set `RESUME_PATH=resume.pdf` in `config.txt`.

**4. Configure `job_agent/config.txt`**

```
EMAIL=your_email@gmail.com
PASSWORD=your_gmail_app_password

AZURE_API_KEY=your_azure_openai_key
AZURE_API_VERSION=2025-02-01-preview
AZURE_ENDPOINT=https://your-resource.openai.azure.com
AZURE_MODEL=gpt-4o

# Job Search Configuration
ADZUNA_APP_ID=your_adzuna_app_id
ADZUNA_APP_KEY=your_adzuna_app_key
JOB_COUNTRY=us
JOB_LOCATION=New York
JOB_TOP_N=20
RESUME_PATH=resume.txt
DOUBAO_API_KEY=your_doubao_api_key

# Target Companies
Google
Meta
Microsoft
Amazon
ByteDance
Goldman Sachs
JPMorgan
McKinsey
```

- **`JOB_COUNTRY`** — two-letter country code: `us`, `gb`, `au`, `ca`, etc.
- **`JOB_LOCATION`** — city or region to search in. Leave empty to search nationwide.
- **`JOB_TOP_N`** — how many results to show and include in the email.
- **`RESUME_PATH`** — filename of your resume (relative to the `job_agent/` folder).
- **Target Companies** — bare company names, one per line. The agent will prioritise listings from these companies. If none match, it falls back to all results. Remove this section entirely to skip filtering.

**5. Run**

```bash
cd job_agent
python agent.py
```

The terminal will print a ranked table of the top matches, and you will receive an HTML email with company names, job titles, locations, match scores, and direct apply links.

---

## API Keys Reference

| Key | Used by | Where to get it |
|---|---|---|
| GNews API key | `news_agent/news.py` | [gnews.io](https://gnews.io) — free, 100 req/day |
| Azure OpenAI key | both agents | [portal.azure.com](https://portal.azure.com) — deploy a GPT-4o model |
| Doubao API key | `news_agent/heatmap.py`, `job_agent/config.txt` | [console.volcengine.com](https://console.volcengine.com) → Ark |
| Adzuna App ID + Key | `job_agent` | [developer.adzuna.com](https://developer.adzuna.com) — free, 250 req/day |
| Gmail App Password | both agents | Google Account → Security → App Passwords |

### Gmail App Password

Gmail requires an **App Password** instead of your regular account password for SMTP.

1. Go to [https://myaccount.google.com](https://myaccount.google.com).
2. Under **Security**, enable **2-Step Verification** if not already on.
3. Search for **"App passwords"**, open it, and generate one for "Mail / Other".
4. Copy the 16-character password (e.g. `xxxx xxxx xxxx xxxx`) into `PASSWORD` in `config.txt` — include the spaces, the agent handles them automatically.

### Azure OpenAI

1. In [portal.azure.com](https://portal.azure.com), create an **Azure OpenAI** resource.
2. Go to **Keys and Endpoint** → copy Key 1 (`AZURE_API_KEY`) and Endpoint (`AZURE_ENDPOINT`).
3. In **Azure OpenAI Studio**, deploy a `gpt-4o` model and use its deployment name as `AZURE_MODEL`.

> If Azure OpenAI is unavailable, the news agent skips summarization and still sends the report. The job agent requires it for resume profile extraction.
