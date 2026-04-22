#!/usr/bin/env python3
"""
News Summarizer - Uses Azure OpenAI API to summarize news articles
"""

from openai import AzureOpenAI
from typing import List, Dict, Optional


def initialize_azure_client(api_key: str, api_version: str, azure_endpoint: str) -> AzureOpenAI:
    """
    Initialize Azure OpenAI client
    
    Args:
        api_key: Azure OpenAI API key
        api_version: API version
        azure_endpoint: Azure endpoint URL
    
    Returns:
        AzureOpenAI client instance
    """
    return AzureOpenAI(
        api_key=api_key,
        api_version=api_version,
        azure_endpoint=azure_endpoint
    )


def generate_news_summary(
    articles: List[Dict],
    keywords_list: List[str],
    client: AzureOpenAI,
    model_name: str = "gpt-4o",
    max_tokens: int = 300
) -> Optional[str]:
    """
    Generate a comprehensive summary of news articles using Azure OpenAI
    
    Args:
        articles: List of article dictionaries with 'title', 'description', 'top_keyword'
        keywords_list: List of keywords being tracked
        client: Azure OpenAI client
        model_name: Model name to use
        max_tokens: Maximum tokens for summary
    
    Returns:
        Summary text or None if failed
    """
    if not articles:
        return None
    
    try:
        # Prepare article information for summarization
        article_texts = []
        for i, article in enumerate(articles[:8], 1):  # Limit to top 8 articles instead of 10
            title = article.get('title', 'Unknown')
            keyword = article.get('top_keyword', 'N/A')
            
            article_texts.append(f"{i}. {title}")
        
        articles_summary = "\n".join(article_texts)
        keywords_str = ", ".join(keywords_list[:5])  # Limit keywords to top 5
        
        # Create simplified summarization prompt (short output)
        prompt = f"""Briefly summarize these {len(article_texts)} articles in around 200-300 words (1 paragraph max):

{articles_summary}

Key points on: {keywords_str}"""
        
        print("🧠 Generating AI summary...")
        print(f"📤 Prompt length: {len(prompt)} chars")
        
        # Call Azure OpenAI API
        response = client.chat.completions.create(
            model=model_name,
            messages=[
                {"role": "system", "content": "You are a business analyst. Provide concise, factual summaries."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=max_tokens,
            temperature=0.7  # Adjusted for gpt-4o
        )
        
        # Debug: Check response structure
        print(f"📊 Response choices: {len(response.choices)}")
        print(f"📊 Finish reason: {response.choices[0].finish_reason}")
        
        if not response.choices:
            print("⚠️  Warning: No choices in response from API")
            return None
        
        choice = response.choices[0]
        message = choice.message
        print(f"📝 Message object: {message}")
        print(f"📝 Message.content: {repr(message.content)}")
        
        summary = message.content if message.content is not None else ""
        
        # Check if content was filtered or blocked
        if choice.finish_reason == "content_filter":
            print("⚠️  Warning: Summary was blocked by content filter")
            return None
        
        if choice.finish_reason == "length":
            print(f"⚠️  Warning: Summary truncated due to max_tokens limit")
            # Still return it even if truncated
        
        print(f"📝 Raw summary type: {type(summary)}, length: {len(summary)}")
        
        # Check for empty responses
        if not summary or summary.strip() == "":
            print(f"❌ Empty summary received from API (finish_reason: {choice.finish_reason})")
            print(f"📊 Full response object: {response}")
            return None
        
        print("✅ Summary generated successfully!")
        print(f"📝 Summary length: {len(summary)} characters")
        return summary
    
    except Exception as e:
        print(f"❌ Error generating summary: {e}")
        import traceback
        traceback.print_exc()
        return None


if __name__ == "__main__":
    # Test example
    sample_articles = [
        {
            'title': 'Stock Market Surge Driven by Tech Earnings',
            'description': 'Tech companies show strong Q1 results',
            'top_keyword': 'stock',
            'source': {'name': 'Reuters'}
        },
        {
            'title': 'Federal Reserve Signals Rate Changes',
            'description': 'Economic outlook affects market sentiment',
            'top_keyword': 'economy',
            'source': {'name': 'Bloomberg'}
        }
    ]
    
    keywords = ['stock', 'market', 'earnings', 'economy', 'nasdaq']
    
    # This would require valid Azure credentials
    # client = initialize_azure_client(api_key, api_version, azure_endpoint)
    # summary = generate_news_summary(sample_articles, keywords, client)
    # print(summary)
