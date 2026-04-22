# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Running the Agent

```bash
# Run the full pipeline (fetch news → summarize → heatmap → email)
python agent.py

# Test email sending only (with sample data)
python test_email.py

# Run individual modules standalone
python news.py        # Fetch and display news
python heatmap.py     # Generate heatmap with sample data
python email_sender.py  # Send test report email
```

## Architecture

This is a single-pipeline automation agent with no web server or scheduler. The pipeline runs sequentially in `agent.py`:

1. **Config loading** (`email_sender.load_config`) — reads `config.txt` for email credentials, Azure keys, and keywords
2. **News fetching** (`news.fetch_articles`) — calls GNews API (`gnews.io/api/v4/search`), paginates up to 50 results, filters to trusted mainstream sources, then uses `sentence-transformers` (`all-MiniLM-L6-v2`) to compute semantic similarity between articles and keywords
3. **Trend extraction** (`news.extract_trending_keywords`) — counts article-to-keyword assignments from the similarity step
4. **AI summarization** (`summarizer.generate_news_summary`) — calls Azure OpenAI (GPT-4o at `hkust.azure-api.net`) with the top 8 articles
5. **Heatmap generation** (`heatmap.generate_heatmap`) — calls Doubao image generation API (ByteDance, OpenAI-compatible at `ark.cn-beijing.volces.com`) with a bubble chart prompt
6. **Email report** (`email_sender.send_html_email`) — generates HTML report and sends via SMTP (auto-detects server from email domain)

## Configuration (`config.txt`)

The config file uses a custom INI-like format parsed manually. Keywords are placed **after** the `# Keywords Configuration` comment section as bare words (one per line), with no `=` sign. Any line with `=` ends the keywords section.

```
EMAIL=user@gmail.com
PASSWORD=app-password-here
AZURE_API_KEY=...
AZURE_API_VERSION=2025-02-01-preview
AZURE_ENDPOINT=https://...
AZURE_MODEL=gpt-4o
stock
market
earnings
```

## API Keys

- **GNews API key**: hardcoded in `news.py` as `API_KEY`
- **Doubao (ByteDance) API key**: hardcoded in `heatmap.py` as `DOUBAO_API_KEY`
- **Azure OpenAI key**: read from `config.txt`
- **Email credentials**: read from `config.txt` (Gmail requires an App Password, not the account password)

## Key Dependencies

- `sentence-transformers` + `torch` — semantic similarity in `news.py`
- `openai` — used for both Azure OpenAI (`AzureOpenAI` client in `summarizer.py`) and Doubao image generation (standard `OpenAI` client with custom `base_url` in `heatmap.py`)
- Standard library only for HTTP/email (`urllib`, `smtplib`)
