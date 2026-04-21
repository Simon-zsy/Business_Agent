# Business_Agent

An automated news intelligence agent that fetches business news, summarizes it with AI, generates a keyword heatmap, and delivers a formatted HTML report to your inbox on demand.

## Pipeline Overview

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

## Project Structure

```
Business_Agent/
├── agent.py          # Main entry point — orchestrates the full pipeline
├── news.py           # GNews API fetching, source filtering, semantic similarity
├── summarizer.py     # Azure OpenAI summarization
├── heatmap.py        # Doubao image generation (bubble heatmap)
├── email_sender.py   # SMTP sending + HTML report generation
├── config.txt        # All credentials and keywords (edit this before running)
└── test_email.py     # Standalone email test with sample data
```

## Setup

### 1. Install Dependencies

```bash
pip install openai sentence-transformers torch requests
```

### 2. Configure `config.txt`

Open `config.txt` and fill in your credentials:

```
EMAIL=your_email@gmail.com
PASSWORD=your_gmail_app_password

AZURE_API_KEY=your_azure_openai_key
AZURE_API_VERSION=2025-02-01-preview
AZURE_ENDPOINT=https://your-resource.openai.azure.com
AZURE_MODEL=gpt-4o

stock
market
earnings
economy
nasdaq
```

The lines after `# Keywords Configuration` (with no `=` sign) are treated as search keywords — one per line.

### 3. Run

```bash
python agent.py
```

---

## Getting the Required API Keys

### GNews API (News Fetching)

1. Go to [https://gnews.io](https://gnews.io) and create a free account.
2. After signing in, your API key is shown on the dashboard.
3. The free tier allows 100 requests/day and returns up to 10 articles per request (the agent paginates automatically).
4. Open `news.py` and replace the value of `API_KEY` near the top of the file with your key.

### Azure OpenAI API (AI Summarization)

1. Go to [https://portal.azure.com](https://portal.azure.com) and sign in.
2. Create an **Azure OpenAI** resource (search "Azure OpenAI" in the marketplace).
3. Once deployed, open the resource and go to **Keys and Endpoint** to copy:
   - **Key 1** → `AZURE_API_KEY` in `config.txt`
   - **Endpoint** → `AZURE_ENDPOINT` in `config.txt`
4. In **Azure OpenAI Studio**, deploy a model (e.g., `gpt-4o`) and note the **deployment name** → `AZURE_MODEL` in `config.txt`.
5. The `AZURE_API_VERSION` can stay as `2025-02-01-preview` unless Azure requires a newer version.

> If you do not have Azure OpenAI access, the agent will skip summarization and still send the report with news articles and heatmap.

### Doubao / ByteDance Image API (Heatmap Generation)

1. Go to [https://console.volcengine.com](https://console.volcengine.com) and register a ByteDance Volcano Engine account.
2. Navigate to **Ark** → **API Key Management** and create a new API key.
3. The key starts with `ark-`. Open `heatmap.py` and replace `DOUBAO_API_KEY` with your key.
4. In the Ark console, enable the **doubao-seedream** image generation model for your account.

> If heatmap generation fails (e.g., the API key is invalid), the agent will still send the email report without the heatmap image.

### Gmail App Password (Email Sending)

Gmail requires an **App Password** instead of your regular account password when sending via SMTP.

1. Go to your Google Account at [https://myaccount.google.com](https://myaccount.google.com).
2. Under **Security**, ensure **2-Step Verification** is turned on (required for App Passwords).
3. Search for **"App passwords"** in the Security page search bar and open it.
4. Select app: **Mail**, select device: **Other (custom name)**, type `Business Agent`, then click **Generate**.
5. Copy the 16-character password (shown once, with spaces like `xxxx xxxx xxxx xxxx`).
6. Paste it as `PASSWORD` in `config.txt` — include the spaces, the agent handles them automatically.

> The agent sends the report to the same address it sends from (self-email). To change the recipient, edit `to_emails` in `agent.py:300`.

---

## Expected Results

After a successful run you will see terminal output like:

```
╔══════════════════════════════════════════════════════════════════════════════╗
║                    🤖 BUSINESS AGENT - NEWS INTELLIGENCE                    ║
╚══════════════════════════════════════════════════════════════════════════════╝

════════════════════════════════ LOADING CONFIGURATION ═════════════════════════
✅ Email: your_email@gmail.com
✅ Keywords: stock, market, earnings, economy, nasdaq

════════════════════════════════ FETCHING NEWS ══════════════════════════════════
✅ Found 30 articles (API total: 142)
✅ After filtering: 18 from trusted sources
✅ Keyword matching completed

════════════════════════════════ EXTRACTING TRENDS ══════════════════════════════
✅ Top 5 trending keywords:
    1. stock           ███████ (7)
    2. market          ███ (3)
    3. earnings        ███ (3)
    ...

════════════════════════════════ GENERATING AI SUMMARY ══════════════════════════
✅ Summary received: 412 chars

════════════════════════════════ GENERATING HEATMAP ════════════════════════════
✅ Heatmap generated successfully

════════════════════════════════ SENDING EMAIL REPORT ══════════════════════════
✅ Email sent successfully!

📊 EXECUTION SUMMARY
⏱️  Total execution time: 38.42 seconds
📰 Articles processed: 18
🔥 Trending keywords found: 5
📝 Summary generated: Yes
🎨 Heatmap generated: Yes
📧 Email sent: Yes
```

The email you receive will contain:
- **Trending Keywords table** — top keywords ranked by article frequency with a visual bar
- **Keyword Heatmap** — an AI-generated bubble chart image where bubble size reflects frequency
- **AI-Generated Summary** — a 200-300 word paragraph summarizing the top news
- **News by Category** — up to 5 articles per keyword, with source, relevance score, date, and link

### Testing Without Running the Full Pipeline

To verify your email credentials without calling any external APIs:

```bash
python test_email.py
```

This sends a report with hardcoded sample data and skips news fetching, summarization, and heatmap generation.
