import json
import urllib.request
import time
from urllib.parse import urlencode
from difflib import SequenceMatcher
from pathlib import Path
import torch
from sentence_transformers import SentenceTransformer

# ========== 1. Configuration ==========

# Trusted mainstream media sources
TRUSTED_SOURCES = {
    # Global financial & business media
    'bloomberg', 'reuters', 'associated press', 'wsj', 'wall street journal', 'financial times', 
    'cnbc', 'bbc', 'marketwatch', 'seeking alpha', 'yahoo finance', 'investing.com',
    'fortune', 'forbes', 'economist', 'ft.com', 'cnbc.com',
    'abc', 'cnn', 'nbc', 'cbs', 'fox news',
    'crunchbase', 'techcrunch',
    # Regional financial media
    'business insider', 'markets insider',
    # Crypto & fintech (if included in keywords)
    'coindesk', 'coin telegraph', 'cointelegraph',
    # Market data
    'nasdaq', 'nyse', 's&p',
}

CONFIG = {
    # Data sources configuration
    'sources': [
        {
            'region_name': 'US Market',
            'lang': 'en',
            'country': 'us',
            'keywords': 'stock market earnings economy investor trading ipo merger acquisition financial'
        }
    ],
    # API configuration
    'api': {
        'max_results': 50,
        'request_delay': 2
    },
    # Display configuration
    'display': {
        'max_per_region': 50,
        'show_source_count': True,
        'similarity_threshold': 0.6
    }
}


def load_config():
    """Load configuration from CONFIG dict"""
    return CONFIG


# ========== 2. API Key ==========
API_KEY = "01eb7b9c3bc8879fd50b68cfb11aeba8"

# ========== 2b. Embedding Model ==========
EMBEDDING_MODEL = SentenceTransformer('all-MiniLM-L6-v2')


# ========== 3. Core Functions ==========

def fetch_articles(keywords, lang, country, max_results):
    """
    Fetch articles using GNews search API with pagination support.
    GNews free API returns max 10 results per request, so we paginate.
    
    Args:
        keywords: Search keywords (space-separated, converted to OR)
        lang: Language code
        country: Country code
        max_results: Maximum number of results to return
    
    Returns:
        List of articles, total count
    """
    search_query = " OR ".join(keywords.split())
    all_articles = []
    total_available = 0
    pages_needed = (max_results + 9) // 10  # Ceiling division
    
    for page in range(1, pages_needed + 1):
        params = {
            "q": search_query,
            "lang": lang,
            "country": country,
            "max": 10,
            "page": page,
            "apikey": API_KEY,
            "sortby": "publishedAt"
        }
        
        url = f"https://gnews.io/api/v4/search?{urlencode(params)}"
        
        try:
            with urllib.request.urlopen(url) as response:
                data = json.loads(response.read().decode("utf-8"))
                articles = data.get("articles", [])
                total_available = data.get("totalArticles", 0)
                
                if not articles:
                    break
                
                all_articles.extend(articles)
                
                if len(all_articles) >= max_results:
                    all_articles = all_articles[:max_results]
                    break
                
                time.sleep(0.5)
        except urllib.error.HTTPError as e:
            print(f"❌ API Error on page {page}: {e.code}")
            break
    
    return all_articles, total_available


def calculate_similarity(title1, title2):
    """Calculate similarity between two titles"""
    return SequenceMatcher(None, title1.lower(), title2.lower()).ratio()


def is_trusted_source(source_name):
    """Check if article source is from mainstream/trusted media"""
    if not source_name:
        return False
    
    source_lower = source_name.lower()
    
    # Direct match with any trusted source
    for trusted in TRUSTED_SOURCES:
        if trusted in source_lower:
            return True
    
    return False

def filter_trusted_sources(articles):
    """
    Filter articles to only keep those from mainstream/trusted media sources
    
    Args:
        articles: List of article dicts
    
    Returns:
        Filtered list of articles from trusted sources
    """
    trusted_articles = []
    for article in articles:
        source_name = article.get('source', {}).get('name', '')
        if is_trusted_source(source_name):
            trusted_articles.append(article)
    
    return trusted_articles


def deduplicate_articles(articles, threshold=0.6):
    """
    Deduplicate and aggregate similar articles
    
    Returns: [
        {
            'article': article object,
            'count': number of sources reporting this news,
            'sources': [list of sources]
        }
    ]
    """
    groups = {}
    
    for i, article in enumerate(articles):
        title = article['title']
        
        # Find similar existing groups
        found_group = False
        for group_idx, group_data in groups.items():
            similarity = calculate_similarity(title, articles[group_idx]['title'])
            if similarity > threshold:
                # Aggregate to existing group
                group_data['count'] += 1
                group_data['sources'].append(article['source']['name'])
                found_group = True
                break
        
        # If no similar group found, create new group
        if not found_group:
            groups[i] = {
                'article': article,
                'count': 1,
                'sources': [article['source']['name']]
            }
    
    # Convert to list and sort by source count
    results = list(groups.values())
    results.sort(key=lambda x: x['count'], reverse=True)
    return results


def compute_keyword_similarity(articles, keywords):
    """
    Compute semantic similarity between articles and individual keywords.
    For each article, find the most similar keyword and track it.
    
    Args:
        articles: List of article dicts
        keywords: Space-separated keyword string
    
    Returns:
        Articles with added 'top_keyword' and 'similarity_score' fields
    """
    if not articles or not keywords:
        return articles
    
    try:
        # Split keywords into individual words
        keyword_list = keywords.split()
        keyword_embeddings = EMBEDDING_MODEL.encode(keyword_list, convert_to_tensor=True)
        
        # Get article descriptions and compute embeddings
        descriptions = [f"{a.get('title', '')} {a.get('description', '')}" for a in articles]
        article_embeddings = EMBEDDING_MODEL.encode(descriptions, convert_to_tensor=True)
        
        # For each article, find the most similar keyword
        for i, article in enumerate(articles):
            # Compute similarity between this article and all keywords
            similarities = torch.nn.functional.cosine_similarity(
                article_embeddings[i:i+1],
                keyword_embeddings,
                dim=1
            ).cpu().numpy()
            
            # Find the keyword with highest similarity
            max_idx = similarities.argmax()
            article['top_keyword'] = keyword_list[max_idx]
            article['similarity_score'] = float(similarities[max_idx])
        
        # Sort by similarity (descending)
        articles.sort(key=lambda x: x['similarity_score'], reverse=True)
        return articles
    
    except Exception as e:
        print(f"❌ Error computing similarity: {e}")
        return articles


def extract_trending_keywords(articles, top_n=15):
    """
    Extract trending keywords from articles based on top_keyword field.
    Counts how many articles matched each keyword.
    
    Args:
        articles: List of articles with 'top_keyword' field
        top_n: Number of top keywords to return
    
    Returns:
        List of (keyword, count) tuples sorted by frequency
    """
    from collections import Counter
    
    # Count top_keyword occurrences
    keywords = [a.get('top_keyword', 'unknown') for a in articles]
    counter = Counter(keywords)
    return counter.most_common(top_n)


def format_output(articles, max_per_region=20, show_similarity=True):
    """Format output for display"""
    output = []
    
    for i, article in enumerate(articles[:max_per_region], 1):
        similarity = article.get('similarity_score', 0)
        top_keyword = article.get('top_keyword', 'N/A')
        source_name = article.get('source', {}).get('name', 'Unknown')
        
        sim_indicator = f"[Match: {top_keyword} | {similarity:.2%}] " if show_similarity else ""
        
        line = f"[{i}] {sim_indicator}"
        output.append(line)
        output.append(f"   📌 {article['title']}")
        output.append(f"   💼 Source: {source_name}")
        output.append(f"   📅 {article['publishedAt'][:20]}")
        output.append(f"   🔗 {article['url'][:80]}...")
        output.append("")
    
    return "\n".join(output)


# ========== 4. Main Program ==========

def main():
    config = load_config()
    
    print("=" * 80)
    print("🚀 Business Agent - Multi-Region News Search")
    print("=" * 80)
    print()
    
    api_config = config.get('api', {})
    display_config = config.get('display', {})
    
    max_results = api_config.get('max_results', 50)
    request_delay = api_config.get('request_delay', 2)
    max_per_region = display_config.get('max_per_region', 20)
    show_sources = display_config.get('show_source_count', True)
    similarity_threshold = display_config.get('similarity_threshold', 0.6)
    
    sources = config.get('sources', [])
    
    for idx, source in enumerate(sources):
        region_name = source.get('region_name')
        lang = source.get('lang')
        country = source.get('country')
        keywords = source.get('keywords', '')
        
        print("=" * 80)
        print(f"🌐 {region_name}")
        print("=" * 80)
        print()
        
        # Fetch articles
        articles, total_count = fetch_articles(keywords, lang, country, max_results)
        
        if not articles:
            print(f"⚠️ No matching articles found")
            print(f"   Region: {region_name}")
            print(f"   API total: {total_count}")
        else:
            print(f"✅ Found {len(articles)}, Total available: {total_count}")
            print()
            
            # Filter to only trusted mainstream media sources
            articles = filter_trusted_sources(articles)
            
            if not articles:
                print(f"⚠️ No articles from trusted sources found")
                print()
            else:
                print(f"✅ After filtering: {len(articles)} from trusted sources")
                print()
                
                # Compute semantic similarity with keywords and find top keyword for each article
                articles = compute_keyword_similarity(articles, keywords)
                
                # Format output
                output = format_output(articles, max_per_region=max_per_region, show_similarity=True)
                print(output)
                
                # Extract and display trending keywords
                print("=" * 80)
                print("🔥 Trending Keywords This Run")
                print("=" * 80)
                trending = extract_trending_keywords(articles, top_n=15)
                for rank, (keyword, count) in enumerate(trending, 1):
                    bar_length = min(count, 20)
                    bar = "█" * bar_length
                    print(f"{rank:2d}. {keyword:15s} {bar} ({count})")
                print()
        
        # Avoid API rate limiting
        if idx < len(sources) - 1:
            print(f"⏳ Waiting {request_delay} seconds before next region...")
            time.sleep(request_delay)
        
        print()


if __name__ == "__main__":
    main()

