import os
from openai import OpenAI


# Doubao API Key
SEEDREAM_API_KEY = "ark-3ebef06a-ba66-402d-9d1f-d17716f848f9-c3f3f"


# Heatmap prompt template - can be customized
HEATMAP_PROMPT_TEMPLATE = """Create a bubble heatmap visualization with the following keywords:

{keyword_list}

Requirements:
1. Display each keyword in a bubble/sphere shape
2. Bubble size is proportional to frequency count - larger count = larger bubble
3. Color gradient from BLUE (lowest frequency) to RED (highest frequency)
   - Blue: lowest frequency keywords
   - Cyan/Green: medium-low frequency
   - Yellow: medium-high frequency
   - Red: highest frequency
4. Each keyword text label centered inside its bubble
5. Text color: white for readability
6. Bubbles arranged in a balanced, visually appealing composition
7. Clean background (white or light grey)
8. No legends, titles, or subtitles
9. No borders or decorative elements
10. High quality, professional appearance

Keywords breakdown:
{keyword_breakdown}
"""


def generate_heatmap_prompt(trending_keywords, template=None):
    """
    Generate prompt for AI to create heatmap visualization
    
    Args:
        trending_keywords: List of (keyword, count) tuples
        template: Custom prompt template (optional)
    
    Returns:
        Prompt string for image generation API
    """
    if not trending_keywords:
        return ""
    
    if template is None:
        template = HEATMAP_PROMPT_TEMPLATE
    
    max_count = max(count for _, count in trending_keywords)
    
    # Build keyword list with frequency
    keyword_list = "\n".join([
        f"- {kw}: {count} times"
        for kw, count in trending_keywords
    ])
    
    # Build detailed breakdown
    keyword_breakdown = "\n".join([
        f"- {kw}: {count} articles ({count/max_count:.0%} of peak frequency)"
        for kw, count in trending_keywords
    ])
    
    prompt = template.format(
        keyword_list=keyword_list,
        keyword_breakdown=keyword_breakdown
    )
    
    return prompt

def generate_heatmap(api_key=None, trending_keywords=None):
    """
    Generate heatmap image using Doubao API
    
    Args:
        api_key: API key for Doubao service (uses SEEDREAM_API_KEY if None)
        trending_keywords: List of (keyword, count) tuples
    
    Returns:
        URL of generated image or None if failed
    """
    # Use default Doubao API key if not provided
    if api_key is None or not api_key.startswith('ark-'):
        api_key = SEEDREAM_API_KEY
    
    client = OpenAI(
        base_url="https://ark.cn-beijing.volces.com/api/v3",
        api_key=api_key,
    )
    
    prompt = generate_heatmap_prompt(trending_keywords)
    
    if not prompt:
        print("❌ No keywords provided for heatmap generation")
        return None
    
    try:
        print("🎨 Generating heatmap...")
        
        images_response = client.images.generate(
            model="doubao-seedream-5-0-260128",
            prompt=prompt,
            size="2K",
            response_format="url",
            extra_body={
                "watermark": False,
            },
        )
        
        image_url = images_response.data[0].url
        print(f"✅ Heatmap generated successfully!")
        print(f"🔗 Image URL: {image_url}")
        return image_url
    
    except Exception as e:
        print(f"❌ Error generating heatmap: {e}")
        return None


if __name__ == "__main__":
    # Example usage with sample trending keywords
    sample_trending = [
        ('stock', 7),
        ('earnings', 3),
        ('market', 3),
        ('investor', 2),
        ('trading', 2),
        ('economy', 1),
        ('ipo', 1)
    ]
    
    # Get API key from environment variable
    api_key = "ark-3ebef06a-ba66-402d-9d1f-d17716f848f9-c3f3f"
    
    if not api_key:
        print("❌ Error: ARK_API_KEY environment variable not set")
        print("Please set it: export ARK_API_KEY='your-api-key'")
    else:
        print("=" * 80)
        print("🔥 Business News Heatmap Generator")
        print("=" * 80)
        print()
        
        print("Trending Keywords:")
        for rank, (keyword, count) in enumerate(sample_trending, 1):
            bar_length = min(count, 10)
            bar = "█" * bar_length
            print(f"{rank:2d}. {keyword:15s} {bar} ({count})")
        print()
        
        # Generate heatmap
        image_url = generate_heatmap(api_key, sample_trending)
        
        if image_url:
            print()
            print("=" * 80)
            print("✅ Heatmap generation completed!")
            print("=" * 80)