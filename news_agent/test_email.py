#!/usr/bin/env python3
"""
Standalone email sender test
"""

from email_sender import load_config, send_html_email, generate_report_with_heatmap

def test_email():
    """Test email sending independently"""
    print("=" * 80)
    print("📧 Testing Email Sender")
    print("=" * 80)
    
    try:
        # Load config
        print("\n📋 Loading configuration...")
        config = load_config()
        print(f"✅ Config loaded: {config['email']}")
        
        # Create sample data for report
        print("\n📝 Creating sample report...")
        
        sample_keywords = [
            ('stock', 7),
            ('earnings', 5),
            ('market', 4),
        ]
        
        sample_articles = [
            {
                'title': 'Stock Market Surge Driven by Tech Earnings',
                'source': {'name': 'Reuters'},
                'top_keyword': 'stock',
                'similarity_score': 0.95,
                'publishedAt': '2026-04-19',
                'url': 'https://example.com/article1'
            },
            {
                'title': 'S&P 500 Reaches Record High',
                'source': {'name': 'Bloomberg'},
                'top_keyword': 'market',
                'similarity_score': 0.88,
                'publishedAt': '2026-04-19',
                'url': 'https://example.com/article2'
            },
            {
                'title': 'Tech Companies Report Strong Q1 Earnings',
                'source': {'name': 'CNBC'},
                'top_keyword': 'earnings',
                'similarity_score': 0.92,
                'publishedAt': '2026-04-19',
                'url': 'https://example.com/article3'
            },
            {
                'title': 'Federal Reserve Keeps Interest Rates Steady',
                'source': {'name': 'Financial Times'},
                'top_keyword': 'market',
                'similarity_score': 0.85,
                'publishedAt': '2026-04-19',
                'url': 'https://example.com/article4'
            },
        ]
        
        keywords_list = ['stock', 'market', 'earnings', 'economy', 'nasdaq']
        
        # Generate HTML report
        print("🎨 Generating HTML report...")
        html_content = generate_report_with_heatmap(
            trending_keywords=sample_keywords,
            articles=sample_articles,
            keywords_list=keywords_list,
            image_url=None,
            summary_text="Markets showed strong performance this week with tech stocks leading gains. Earnings reports from major companies exceeded expectations, driving investor confidence. Federal Reserve maintained steady rates, supporting market stability.",
            title="Business News Intelligence Report - Test"
        )
        print(f"✅ HTML report generated ({len(html_content)} chars)")
        
        # Send email
        print("\n📧 Sending test email...")
        success = send_html_email(
            from_email=config['email'],
            password=config['password'],
            to_emails=[config['email']],
            subject="Test Report: Business News Intelligence",
            html_content=html_content,
            image_url=None
        )
        
        if success:
            print("\n" + "=" * 80)
            print("✅ EMAIL TEST SUCCESSFUL!")
            print("=" * 80)
        else:
            print("\n" + "=" * 80)
            print("❌ EMAIL TEST FAILED")
            print("=" * 80)
        
        return success

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    test_email()
