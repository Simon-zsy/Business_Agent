"""
agent.py — Internship Job Finder Pipeline

Pipeline:
  1. Load config  (email_sender.load_config)
  2. Read resume  (resume_parser.read_resume)
  3. Extract profile via Azure OpenAI  (resume_parser.extract_profile)
  4. Fetch internship listings via Adzuna  (job_finder.fetch_jobs_adzuna)
  5. Filter by company whitelist  (job_finder.filter_by_companies)
  6. Rank by semantic similarity  (job_finder.rank_jobs)
  7. Print results to terminal  (job_finder.print_job_results)
  8. Generate company bubble image  (job_finder.generate_company_bubble_image)
  9. Send HTML email report  (email_sender.send_html_email)

Usage:
    cd job_agent
    python agent.py
"""

import sys
from pathlib import Path

from openai import AzureOpenAI

from email_sender import load_config, send_html_email
from resume_parser import read_resume, extract_profile
from job_finder import (
    fetch_jobs_jsearch,
    filter_by_companies,
    rank_jobs,
    print_job_results,
    generate_job_report_html,
    generate_company_bubble_image,
)


def main():
    print("=" * 60)
    print("  Business Agent — Internship Job Finder")
    print("=" * 60)

    # ------------------------------------------------------------------
    # 1. Load configuration
    # ------------------------------------------------------------------
    print("\n📋 Loading configuration...")
    try:
        config = load_config()
    except (FileNotFoundError, ValueError) as e:
        print(f"❌ Config error: {e}")
        sys.exit(1)

    # Check JSearch credentials
    if not config.get('jsearch_api_key') or config['jsearch_api_key'] == 'your_rapidapi_key_here':
        print("❌ JSEARCH_API_KEY not set in config.txt")
        print("   Sign up free at https://rapidapi.com/letscrape-6bRBa3QguO5/api/jsearch")
        sys.exit(1)

    print(f"✅ Config loaded — location: {config['job_location']}, top_n: {config['job_top_n']}")

    # ------------------------------------------------------------------
    # 2. Read resume
    # ------------------------------------------------------------------
    resume_path = config.get('resume_path', 'resume.txt')
    print(f"\n📄 Reading resume from '{resume_path}'...")

    try:
        resume_text = read_resume(resume_path)
        print(f"✅ Resume loaded ({len(resume_text)} characters)")
    except FileNotFoundError:
        print(f"❌ Resume file not found: '{resume_path}'")
        print("   Create a resume.txt file in the project directory or update RESUME_PATH in config.txt")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Failed to read resume: {e}")
        sys.exit(1)

    # ------------------------------------------------------------------
    # 3. Extract profile via Azure OpenAI
    # ------------------------------------------------------------------
    print("\n🤖 Extracting candidate profile with Azure OpenAI...")
    azure_client = AzureOpenAI(
        api_key=config['azure_api_key'],
        api_version=config['azure_api_version'],
        azure_endpoint=config['azure_endpoint'],
    )

    profile = extract_profile(resume_text, azure_client, config['azure_model'])
    print(f"✅ Profile extracted")
    print(f"   Skills:      {', '.join(profile['skills'][:8])}")
    print(f"   Target roles: {', '.join(profile['roles'][:5])}")
    print(f"   Summary:     {profile['summary'][:100]}...")

    # ------------------------------------------------------------------
    # 4. Fetch jobs from Adzuna
    # ------------------------------------------------------------------
    print(f"\n🔍 Fetching internship listings from JSearch ({config['job_location']})...")
    jobs = fetch_jobs_jsearch(
        keywords=profile['roles'],
        location=config['job_location'],
        api_key=config['jsearch_api_key'],
        max_results=100,  # Fetch more before filtering, then trim to top_n
    )

    if not jobs:
        print("⚠️  No jobs returned from JSearch. Check your API key and search parameters.")
        sys.exit(0)

    # ------------------------------------------------------------------
    # 5. Filter by company whitelist
    # ------------------------------------------------------------------
    target_companies = config.get('target_companies', [])
    if target_companies:
        print(f"\n🏢 Filtering by {len(target_companies)} target companies...")
        filtered_jobs = filter_by_companies(jobs, target_companies)
        # If whitelist returns nothing, fall back to all jobs with a warning
        if not filtered_jobs:
            print("⚠️  No jobs matched the company whitelist — showing all results instead")
            filtered_jobs = jobs
    else:
        filtered_jobs = jobs

    # ------------------------------------------------------------------
    # 6. Rank by semantic similarity
    # ------------------------------------------------------------------
    print(f"\n📊 Ranking {len(filtered_jobs)} jobs by resume similarity...")
    ranked_jobs = rank_jobs(filtered_jobs, resume_text)

    # ------------------------------------------------------------------
    # 7. Print to terminal
    # ------------------------------------------------------------------
    top_n = config.get('job_top_n', 20)
    print_job_results(ranked_jobs, top_n=top_n)

    # ------------------------------------------------------------------
    # 8. Generate company bubble image
    # ------------------------------------------------------------------
    image_url = None
    doubao_key = config.get('doubao_api_key')
    if doubao_key and doubao_key != 'your_doubao_api_key_here':
        image_url = generate_company_bubble_image(
            ranked_jobs,
            doubao_api_key=doubao_key,
            top_n=top_n,
        )
    else:
        print("⚠️  DOUBAO_API_KEY not set — skipping bubble image generation")

    # ------------------------------------------------------------------
    # 9. Send HTML email report
    # ------------------------------------------------------------------
    print(f"\n📧 Sending email report to {config['email']}...")
    html = generate_job_report_html(ranked_jobs, profile, top_n=top_n, image_url=image_url)

    success = send_html_email(
        from_email=config['email'],
        password=config['password'],
        to_emails=[config['email']],
        subject="Business Agent — Internship Opportunities Report",
        html_content=html,
        image_url=image_url,
    )

    if success:
        print("✅ Email report sent successfully!")
    else:
        print("⚠️  Email sending failed, but results are printed above.")

    print("\n✅ Job finder pipeline complete.")


if __name__ == '__main__':
    main()
