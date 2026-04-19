#!/usr/bin/env python3
"""
Business Agent - Automated News Intelligence System
Orchestrates: News Fetching → AI Summary → Heatmap Generation → Email Reporting
"""

import sys
import time
from pathlib import Path

# Import from other modules
from news import (
    fetch_articles,
    filter_trusted_sources,
    compute_keyword_similarity,
    extract_trending_keywords,
    API_KEY
)
from heatmap import generate_heatmap_prompt, generate_heatmap
from summarizer import initialize_azure_client, generate_news_summary
from email_sender import (
    load_config,
    send_html_email,
    generate_report_with_heatmap,
    get_smtp_config
)


def load_unified_config():
    """Load configuration from unified config.txt"""
    print("\n" + "=" * 80)
    print("🔧 LOADING CONFIGURATION")
    print("=" * 80)
    
    try:
        config = load_config("config.txt")
        print(f"✅ Email: {config['email']}")
        print(f"✅ Keywords: {', '.join(config['keywords'])}")
        return config
    except Exception as e:
        print(f"❌ Failed to load config: {e}")
        sys.exit(1)


def fetch_news(keywords_list):
    """Fetch news using news.py module"""
    print("\n" + "=" * 80)
    print("📰 FETCHING NEWS")
    print("=" * 80)
    
    try:
        # Convert keywords list to space-separated string for API
        keywords_string = " ".join(keywords_list)
        
        # Use py's functions to fetch
        lang = 'en'
        country = 'us'
        max_results = 50
        
        print(f"🔍 Searching for: {keywords_string}")
        print(f"📍 Region: {country.upper()} | Language: {lang}")
        print()
        
        # Fetch articles
        articles, total_count = fetch_articles(
            keywords_string, 
            lang, 
            country, 
            max_results
        )
        
        print(f"✅ Found {len(articles)} articles (API total: {total_count})")
        
        if not articles:
            print("⚠️  No articles found")
            return []
        
        # Filter to trusted sources
        print(f"🔽 Filtering to trusted sources...")
        articles = filter_trusted_sources(articles)
        print(f"✅ After filtering: {len(articles)} from trusted sources")
        
        if not articles:
            print("⚠️  No articles from trusted sources")
            return []
        
        # Compute keyword similarity
        print(f"🧠 Computing semantic similarity...")
        articles = compute_keyword_similarity(articles, keywords_string)
        print(f"✅ Keyword matching completed")
        
        return articles
    
    except Exception as e:
        print(f"❌ Error fetching news: {e}")
        import traceback
        traceback.print_exc()
        return []


def extract_trends(articles, top_n=10):
    """Extract trending keywords from articles"""
    print("\n" + "=" * 80)
    print("🔥 EXTRACTING TRENDS")
    print("=" * 80)
    
    try:
        trending = extract_trending_keywords(articles, top_n=top_n)
        
        print(f"✅ Top {len(trending)} trending keywords:")
        for rank, (keyword, count) in enumerate(trending, 1):
            bar_length = min(count, 20)
            bar = "█" * bar_length
            print(f"   {rank:2d}. {keyword:15s} {bar} ({count})")
        
        return trending
    
    except Exception as e:
        print(f"❌ Error extracting trends: {e}")
        return []


def generate_summary(articles, keywords_list, azure_client, azure_model):
    """Generate AI summary of news"""
    print("\n" + "=" * 80)
    print("🧠 GENERATING AI SUMMARY")
    print("=" * 80)
    
    try:
        if not articles:
            print("⚠️  No articles to summarize")
            return None
        
        print(f"📝 Summarizing {len(articles)} articles...")
        
        summary = generate_news_summary(
            articles=articles,
            keywords_list=keywords_list,
            client=azure_client,
            model_name=azure_model,
            max_tokens=500
        )
        
        if summary and summary.strip():
            print(f"✅ Summary received: {len(summary)} chars")
            return summary
        else:
            print(f"⚠️  Failed to generate summary (received empty response)")
            return None
    
    except Exception as e:
        print(f"❌ Error generating summary: {e}")
        import traceback
        traceback.print_exc()
        return None


def generate_heatmap_image(trending_keywords):
    """Generate heatmap visualization"""
    print("\n" + "=" * 80)
    print("🎨 GENERATING HEATMAP")
    print("=" * 80)
    
    try:
        if not trending_keywords:
            print("⚠️  No trending keywords to visualize")
            return None
        
        # Generate prompt
        prompt = generate_heatmap_prompt(trending_keywords)
        print(f"✅ Generated prompt for heatmap")
        
        # Generate image (uses default Doubao API key)
        image_url = generate_heatmap(api_key=None, trending_keywords=trending_keywords)
        
        if image_url:
            print(f"✅ Heatmap generated successfully")
            print(f"🔗 Image URL: {image_url[:60]}...")
            return image_url
        else:
            print("⚠️  Failed to generate heatmap")
            return None
    
    except Exception as e:
        print(f"❌ Error generating heatmap: {e}")
        import traceback
        traceback.print_exc()
        return None


def send_report_email(
    email_config,
    trending_keywords,
    articles,
    keywords_list,
    heatmap_url=None,
    summary_text=None
):
    """Generate and send report email"""
    print("\n" + "=" * 80)
    print("📧 SENDING EMAIL REPORT")
    print("=" * 80)
    
    try:
        # Generate HTML report with categories, heatmap, and summary
        print("📝 Generating HTML report...")
        html_content = generate_report_with_heatmap(
            trending_keywords=trending_keywords,
            articles=articles,
            keywords_list=keywords_list,
            image_url=heatmap_url,
            summary_text=summary_text,
            title="Business News Intelligence Report"
        )
        print("✅ HTML report generated")
        
        # Send email
        print("📧 Sending email...")
        success = send_html_email(
            from_email=email_config['email'],
            password=email_config['password'],
            to_emails=[email_config['email']],  # Send to self
            subject="📊 Business News Report - Daily Intelligence",
            html_content=html_content,
            image_url=heatmap_url
        )
        
        if success:
            print("✅ Email sent successfully!")
            return True
        else:
            print("❌ Failed to send email")
            return False
    
    except Exception as e:
        print(f"❌ Error sending email: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Main agent orchestration"""
    print("\n" + "╔" + "═" * 78 + "╗")
    print("║" + " " * 20 + "🤖 BUSINESS AGENT - NEWS INTELLIGENCE" + " " * 21 + "║")
    print("╚" + "═" * 78 + "╝")
    
    start_time = time.time()
    
    # Step 1: Load configuration
    config = load_unified_config()
    email_config = {
        'email': config['email'],
        'password': config['password']
    }
    keywords_list = config['keywords']
    
    # Initialize Azure OpenAI client for summarization
    try:
        azure_client = initialize_azure_client(
            api_key=config['azure_api_key'],
            api_version=config['azure_api_version'],
            azure_endpoint=config['azure_endpoint']
        )
        print("✅ Azure OpenAI client initialized")
    except Exception as e:
        print(f"⚠️  Warning: Failed to initialize Azure client: {e}")
        azure_client = None
    
    # Step 2: Fetch news
    articles = fetch_news(keywords_list)
    
    if not articles:
        print("\n❌ No articles found. Exiting.")
        return False
    
    # Step 3: Extract trends
    trending_keywords = extract_trends(articles, top_n=10)
    
    # Step 4: Generate AI summary (if Azure client available)
    summary_text = None
    if azure_client and config.get('azure_api_key'):
        summary_text = generate_summary(
            articles=articles,
            keywords_list=keywords_list,
            azure_client=azure_client,
            azure_model=config['azure_model']
        )
    else:
        print("\n⚠️  Azure OpenAI client not available, skipping summary generation")
    
    # Step 5: Generate heatmap
    heatmap_url = None
    if not trending_keywords:
        print("\n⚠️  No trending keywords. Skipping heatmap generation.")
    else:
        heatmap_url = generate_heatmap_image(trending_keywords)
    
    # Step 6: Send email report
    success = send_report_email(
        email_config=email_config,
        trending_keywords=trending_keywords,
        articles=articles,
        keywords_list=keywords_list,
        heatmap_url=heatmap_url,
        summary_text=summary_text
    )
    
    # Summary
    elapsed_time = time.time() - start_time
    
    print("\n" + "=" * 80)
    print("📊 EXECUTION SUMMARY")
    print("=" * 80)
    print(f"⏱️  Total execution time: {elapsed_time:.2f} seconds")
    print(f"📰 Articles processed: {len(articles)}")
    print(f"🔥 Trending keywords found: {len(trending_keywords)}")
    print(f"📝 Summary generated: {'Yes' if summary_text else 'No'}")
    print(f"🎨 Heatmap generated: {'Yes' if heatmap_url else 'No'}")
    print(f"📧 Email sent: {'Yes' if success else 'No'}")
    print("=" * 80 + "\n")
    
    return success


if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n❌ Interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
