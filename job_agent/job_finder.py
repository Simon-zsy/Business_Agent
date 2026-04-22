"""
Job Finder - Fetches internship listings from JSearch API (via RapidAPI), filters by
company whitelist, and ranks results by semantic similarity to the candidate's resume.
"""

import json
import time
import urllib.request
import urllib.error
from collections import Counter
from urllib.parse import urlencode
from datetime import datetime
from typing import List, Optional

import torch
from sentence_transformers import SentenceTransformer
from openai import OpenAI

# Shared embedding model (same one used by news.py)
_MODEL: Optional[SentenceTransformer] = None


def _get_model() -> SentenceTransformer:
    global _MODEL
    if _MODEL is None:
        print("🔄 Loading embedding model...")
        _MODEL = SentenceTransformer('all-MiniLM-L6-v2')
        print("✅ Embedding model ready")
    return _MODEL


# ---------------------------------------------------------------------------
# 1. Fetching
# ---------------------------------------------------------------------------

def _normalize_jsearch_job(raw: dict) -> dict:
    """Convert a JSearch result dict to the common internal format."""
    city    = raw.get('job_city') or ''
    country = raw.get('job_country') or ''
    location_str = ', '.join(filter(None, [city, country]))
    return {
        'company':  {'display_name': raw.get('employer_name') or 'Unknown'},
        'title':    raw.get('job_title') or '',
        'description': raw.get('job_description') or '',
        'location': {'display_name': location_str},
        'redirect_url': raw.get('job_apply_link') or '#',
        'created':  (raw.get('job_posted_at_datetime_utc') or '')[:10],
    }


def fetch_jobs_jsearch(
    keywords: List[str],
    location: str,
    api_key: str,
    max_results: int = 50,
) -> List[dict]:
    """
    Fetch internship job listings from the JSearch API (via RapidAPI).

    Sign up free at https://rapidapi.com/letscrape-6bRBa3QguO5/api/jsearch
    Free tier: 200 requests / month.

    Args:
        keywords: Role keywords extracted from the resume
        location: City / region to search in (e.g. 'Hong Kong')
        api_key: RapidAPI key
        max_results: Maximum total results to return

    Returns:
        List of normalised job dicts (same structure as Adzuna output)
    """
    all_jobs: List[dict] = []
    results_per_page = 10
    pages_needed = min((max_results + results_per_page - 1) // results_per_page, 10)

    # Use just the first keyword to keep the query broad enough to return results.
    # JSearch is sensitive to overly specific queries — shorter is better.
    # Strip the word "intern/internship" from the role if present to avoid
    # duplicates like "intern Finance Intern Hong Kong".
    role = keywords[0] if keywords else 'business'
    role_clean = role.lower().replace('intern', '').replace('internship', '').strip()
    role_clean = role_clean or 'business'
    location_str = location or 'Hong Kong'
    queries_to_try = [
        f"intern {role_clean} {location_str}",
        f"internship {location_str}",          # broad fallback
    ]

    headers = {
        'X-RapidAPI-Key':  api_key,
        'X-RapidAPI-Host': 'jsearch.p.rapidapi.com',
    }

    for query in queries_to_try:
        print(f"   Query: \"{query}\"")
        for page in range(1, pages_needed + 1):
            params = {
                'query':     query,
                'page':      str(page),
                'num_pages': '1',
                # intentionally omit employment_types — many HK internships are not tagged
            }

            url = f"https://jsearch.p.rapidapi.com/search?{urlencode(params)}"
            req = urllib.request.Request(url, headers=headers)

            try:
                with urllib.request.urlopen(req, timeout=15) as resp:
                    data = json.loads(resp.read().decode('utf-8'))
                    results = data.get('data', [])
                    if not results:
                        break
                    all_jobs.extend(_normalize_jsearch_job(r) for r in results)
                    if len(all_jobs) >= max_results:
                        break
                    time.sleep(0.5)

            except urllib.error.HTTPError as e:
                print(f"❌ JSearch API error (page {page}): HTTP {e.code}")
                break
            except Exception as e:
                print(f"❌ Request failed (page {page}): {e}")
                break

        if all_jobs:
            break   # got results — no need to try the fallback query

    print(f"✅ Fetched {len(all_jobs)} jobs from JSearch")
    return all_jobs[:max_results]


# ---------------------------------------------------------------------------
# 2. Filtering
# ---------------------------------------------------------------------------

def filter_by_companies(jobs: List[dict], company_whitelist: List[str]) -> List[dict]:
    """
    If a whitelist is provided, return only jobs from those companies.
    If the whitelist is empty, return all jobs unchanged.

    Args:
        jobs: Raw job list from fetch_jobs_adzuna
        company_whitelist: List of company name substrings to keep

    Returns:
        Filtered list
    """
    if not company_whitelist:
        return jobs

    whitelist_lower = [c.lower() for c in company_whitelist]
    matched = []
    for job in jobs:
        company_name = (job.get('company', {}) or {}).get('display_name', '').lower()
        if any(w in company_name for w in whitelist_lower):
            matched.append(job)

    print(f"✅ {len(matched)} jobs match the company whitelist out of {len(jobs)} total")
    return matched


# ---------------------------------------------------------------------------
# 3. Ranking
# ---------------------------------------------------------------------------

def rank_jobs(jobs: List[dict], resume_text: str) -> List[dict]:
    """
    Rank jobs by cosine similarity between the resume and each job's title + description.

    Args:
        jobs: List of job dicts (may be raw Adzuna results or pre-filtered)
        resume_text: Full resume text for embedding

    Returns:
        Jobs sorted by similarity_score descending, with 'similarity_score' added
    """
    if not jobs:
        return []

    model = _get_model()

    resume_embedding = model.encode(resume_text, convert_to_tensor=True)

    job_texts = []
    for job in jobs:
        title = job.get('title', '')
        description = job.get('description', '')
        job_texts.append(f"{title}. {description[:500]}")

    job_embeddings = model.encode(job_texts, convert_to_tensor=True)

    # Cosine similarity: dot product of normalised vectors
    resume_norm = resume_embedding / resume_embedding.norm()
    job_norms = job_embeddings / job_embeddings.norm(dim=1, keepdim=True)
    scores = (job_norms @ resume_norm).tolist()

    for job, score in zip(jobs, scores):
        job['similarity_score'] = float(score)

    ranked = sorted(jobs, key=lambda j: j['similarity_score'], reverse=True)
    return ranked


# ---------------------------------------------------------------------------
# 4. Company bubble image generation
# ---------------------------------------------------------------------------

# Brand colour hints for well-known companies — helps the image model produce
# more recognisable, on-brand bubbles.
_BRAND_COLORS = {
    'google':       'multicolour (red, blue, yellow, green)',
    'meta':         'deep blue and sky blue gradient',
    'microsoft':    'four-colour squares: red, green, blue, yellow',
    'amazon':       'deep orange and black',
    'apple':        'silver and white metallic',
    'netflix':      'bright red on black',
    'bytedance':    'black and vibrant blue',
    'tiktok':       'black with cyan and pink neon glow',
    'tesla':        'red and silver metallic',
    'nvidia':       'lime green and black',
    'goldman sachs':'dark navy blue and gold',
    'jpmorgan':     'royal blue and grey',
    'mckinsey':     'dark blue and white',
    'bloomberg':    'orange and black',
    'uber':         'black and white',
    'airbnb':       'coral pink and white',
    'spotify':      'bright green and black',
    'openai':       'teal and white',
    'anthropic':    'warm orange and white',
}


def _brand_color(company_name: str) -> str:
    """Return a colour description for a company, or a default gradient."""
    key = company_name.lower()
    for brand, color in _BRAND_COLORS.items():
        if brand in key:
            return color
    return 'purple and blue gradient'


def generate_company_bubble_image(
    ranked_jobs: List[dict],
    doubao_api_key: str,
    top_n: int = 20,
) -> Optional[str]:
    """
    Generate a company-logo bubble chart using the Doubao image generation API.
    Bubble size is proportional to the number of matching job listings per company.

    Args:
        ranked_jobs: Jobs sorted by similarity_score (output of rank_jobs)
        doubao_api_key: Doubao (ByteDance Ark) API key
        top_n: How many top jobs to use when counting company frequencies

    Returns:
        URL of the generated image, or None if generation failed
    """
    display = ranked_jobs[:top_n]
    if not display:
        print("⚠️  No jobs to generate bubble image from")
        return None

    # Count jobs per company in the top-N results
    company_counts: Counter = Counter()
    for job in display:
        name = (job.get('company', {}) or {}).get('display_name', 'Unknown')
        company_counts[name] += 1

    # Build prompt lines — largest bubble first
    bubble_lines = []
    for company, count in company_counts.most_common():
        color = _brand_color(company)
        bubble_lines.append(
            f'- "{company}": {count} listing(s), color scheme: {color}'
        )

    bubble_desc = '\n'.join(bubble_lines)

    prompt = f"""Create a modern, colorful bubble chart visualization of company job opportunities.

Each bubble represents one company. Bubble size is proportional to the number of internship listings.

Companies and their brand colors:
{bubble_desc}

Design requirements:
1. Each bubble is a perfect circle filled with the company's brand colors (gradient or solid)
2. The company name is written in clean white bold text centered inside the bubble
3. Bubble sizes clearly reflect the listing count — more listings = noticeably larger bubble
4. Bubbles are tightly clustered together in a visually balanced composition, with slight overlaps allowed
5. Background is clean white or very light grey
6. No legends, axes, titles, or decorative borders
7. Overall style: modern data visualization, flat design, professional"""

    try:
        client = OpenAI(
            base_url='https://ark.cn-beijing.volces.com/api/v3',
            api_key=doubao_api_key,
        )

        print("🎨 Generating company bubble image...")
        response = client.images.generate(
            model='doubao-seedream-5-0-260128',
            prompt=prompt,
            size='2K',
            response_format='url',
            extra_body={'watermark': False},
        )

        url = response.data[0].url
        print(f"✅ Company bubble image generated!")
        return url

    except Exception as e:
        print(f"⚠️  Company bubble image generation failed: {e}")
        return None


# ---------------------------------------------------------------------------
# 5. Output helpers
# ---------------------------------------------------------------------------

def print_job_results(ranked_jobs: List[dict], top_n: int = 20) -> None:
    """Print a ranked job table to the terminal."""
    display = ranked_jobs[:top_n]

    if not display:
        print("⚠️  No jobs to display.")
        return

    print(f"\n{'='*80}")
    print(f"  TOP {len(display)} INTERNSHIP MATCHES")
    print(f"{'='*80}")
    print(f"{'#':<4} {'Score':<7} {'Company':<25} {'Title':<35} {'Location'}")
    print(f"{'-'*4} {'-'*6} {'-'*24} {'-'*34} {'-'*20}")

    for i, job in enumerate(display, 1):
        score = job.get('similarity_score', 0)
        company = (job.get('company', {}) or {}).get('display_name', 'Unknown')[:24]
        title = (job.get('title', 'Unknown'))[:34]
        location = (job.get('location', {}) or {}).get('display_name', '')[:20]
        url = job.get('redirect_url', '')

        print(f"{i:<4} {score:.2f}   {company:<25} {title:<35} {location}")
        print(f"     Link: {url}")
        print()


def generate_job_report_html(
    ranked_jobs: List[dict],
    profile: dict,
    top_n: int = 20,
    image_url: Optional[str] = None,
) -> str:
    """
    Generate an HTML email report for the job results, styled consistently
    with the existing business news reports.

    Args:
        ranked_jobs: Jobs sorted by similarity_score
        profile: Extracted resume profile dict (skills, roles, summary)
        top_n: How many jobs to include
        image_url: Optional URL of the company bubble image to embed

    Returns:
        HTML string
    """
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    display = ranked_jobs[:top_n]

    # --- Profile section ---
    skills_str = ', '.join(profile.get('skills', [])[:15]) or 'N/A'
    roles_str = ', '.join(profile.get('roles', [])) or 'N/A'
    summary_str = profile.get('summary', '')

    profile_html = f"""
    <h2>👤 Candidate Profile</h2>
    <div style='background-color:#f0f7ff; padding:15px; border-left:4px solid #2196F3;
                border-radius:4px; margin-bottom:20px;'>
        <p><strong>Summary:</strong> {summary_str}</p>
        <p><strong>Skills:</strong> {skills_str}</p>
        <p><strong>Target Roles:</strong> {roles_str}</p>
    </div>
    """

    # --- Bubble image section ---
    bubble_html = ''
    if image_url:
        bubble_html = """
    <h2>🫧 Company Opportunity Map</h2>
    <div style='text-align:center; margin:20px 0;'>
        <img src='cid:heatmap_image'
             style='max-width:100%; height:auto; border-radius:10px;
                    box-shadow:0 4px 12px rgba(0,0,0,0.15);'>
        <p style='color:#999; font-size:12px; margin-top:8px;'>
            Bubble size = number of matching listings per company
        </p>
    </div>
    """

    # --- Jobs table ---
    rows_html = ''
    for i, job in enumerate(display, 1):
        score = job.get('similarity_score', 0)
        company = (job.get('company', {}) or {}).get('display_name', 'Unknown')
        title = job.get('title', 'Unknown')
        location = (job.get('location', {}) or {}).get('display_name', '')
        url = job.get('redirect_url', '#')
        created = (job.get('created', '') or '')[:10]

        score_pct = f"{score:.0%}"
        bar_len = min(int(score * 100), 100)

        rows_html += f"""
        <tr>
            <td style='text-align:center;'><strong>{i}</strong></td>
            <td><strong>{company}</strong></td>
            <td><a href='{url}' style='color:#4a90d9; text-decoration:none;'>{title}</a></td>
            <td>{location}</td>
            <td>{created}</td>
            <td>
                <div style='display:flex; align-items:center; gap:6px;'>
                    <div style='width:80px; height:14px; background:#e0e0e0; border-radius:7px; overflow:hidden;'>
                        <div style='width:{bar_len}%; height:100%; background:#4a90d9; border-radius:7px;'></div>
                    </div>
                    <span style='font-size:12px; color:#555;'>{score_pct}</span>
                </div>
            </td>
        </tr>
        """

    jobs_html = f"""
    <h2>💼 Top {len(display)} Internship Matches</h2>
    <table border='0' cellpadding='10' style='width:100%; border-collapse:collapse;'>
        <thead>
            <tr style='background:#f5f5f5;'>
                <th>#</th>
                <th>Company</th>
                <th>Role</th>
                <th>Location</th>
                <th>Posted</th>
                <th>Match</th>
            </tr>
        </thead>
        <tbody>
            {rows_html}
        </tbody>
    </table>
    """

    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <title>Internship Opportunities Report</title>
        <style>
            body {{
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                margin: 0; padding: 20px;
                background: linear-gradient(135deg, #4a90d9 0%, #357abd 100%);
            }}
            .container {{
                max-width: 960px; margin: 0 auto;
                background-color: white; padding: 30px;
                border-radius: 12px; box-shadow: 0 10px 30px rgba(0,0,0,0.3);
            }}
            h1 {{ color: #333; border-bottom: 4px solid #4a90d9;
                  padding-bottom: 15px; margin-bottom: 30px; }}
            h2 {{ color: #555; margin-top: 30px; font-size: 20px; }}
            table {{ width: 100%; border-collapse: collapse; margin-bottom: 20px; }}
            th, td {{ padding: 12px; text-align: left; border-bottom: 1px solid #ddd; }}
            th {{ background-color: #f5f5f5; font-weight: bold; }}
            tr:hover {{ background-color: #fafafa; }}
            a {{ color: #4a90d9; text-decoration: none; }}
            a:hover {{ text-decoration: underline; }}
            .footer {{
                margin-top: 40px; text-align: center; color: #999;
                font-size: 12px; border-top: 1px solid #ddd; padding-top: 20px;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🎓 Internship Opportunities Report</h1>
            <div style='color:#999; font-size:13px; margin:10px 0;'>Generated: {now}</div>

            {profile_html}

            {bubble_html}

            {jobs_html}

            <div class="footer">
                <p>Business Agent — Internship Finder</p>
                <p style='margin-top:8px;'>Powered by Adzuna API + Semantic Similarity Ranking</p>
            </div>
        </div>
    </body>
    </html>
    """

    return html
