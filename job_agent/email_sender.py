import smtplib
import os
import requests
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.image import MIMEImage
from email.header import Header
from email.utils import formataddr, formatdate, make_msgid
from email.policy import SMTP
from datetime import datetime
from pathlib import Path
from typing import Optional, List
import urllib.request


def load_config(config_file: str = "config.txt") -> dict:
    config_path = Path(config_file)
    
    if not config_path.exists():
        raise FileNotFoundError(f"Cannot find {config_file} file")
    
    config = {
        'email': None,
        'password': None,
        'keywords': [],
        'azure_api_key': None,
        'azure_api_version': '2025-02-01-preview',
        'azure_endpoint': 'https://hkust.azure-api.net',
        'azure_model': 'gpt-5-mini',
        # Job search settings
        'adzuna_app_id': None,
        'adzuna_app_key': None,
        'job_country': 'us',
        'job_location': '',
        'job_top_n': 20,
        'resume_path': 'resume.txt',
        'target_companies': [],
        # Image generation
        'doubao_api_key': None,
    }

    in_keywords_section = False
    in_companies_section = False

    with open(config_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()

            if 'Keywords Configuration' in line:
                in_keywords_section = True
                in_companies_section = False
                continue

            if 'Target Companies' in line:
                in_companies_section = True
                in_keywords_section = False
                continue

            if (in_keywords_section or in_companies_section) and 'Configuration' in line:
                in_keywords_section = False
                in_companies_section = False

            if not line or line.startswith('#'):
                continue

            if '=' in line:
                key, value = line.split('=', 1)
                key = key.strip()
                value = value.strip()

                if key == 'EMAIL':
                    config['email'] = value
                elif key == 'PASSWORD':
                    config['password'] = value
                elif key == 'AZURE_API_KEY':
                    config['azure_api_key'] = value
                elif key == 'AZURE_API_VERSION':
                    config['azure_api_version'] = value
                elif key == 'AZURE_ENDPOINT':
                    config['azure_endpoint'] = value
                elif key == 'AZURE_MODEL':
                    config['azure_model'] = value
                elif key == 'ADZUNA_APP_ID':
                    config['adzuna_app_id'] = value
                elif key == 'ADZUNA_APP_KEY':
                    config['adzuna_app_key'] = value
                elif key == 'JOB_COUNTRY':
                    config['job_country'] = value
                elif key == 'JOB_LOCATION':
                    config['job_location'] = value
                elif key == 'JOB_TOP_N':
                    config['job_top_n'] = int(value)
                elif key == 'RESUME_PATH':
                    config['resume_path'] = value
                elif key == 'DOUBAO_API_KEY':
                    config['doubao_api_key'] = value

                in_keywords_section = False
                in_companies_section = False

            elif in_keywords_section and line:
                config['keywords'].append(line)

            elif in_companies_section and line:
                config['target_companies'].append(line)
    
    if not config['email']:
        raise ValueError("config.txt is missing EMAIL configuration")
    if not config['password']:
        raise ValueError("config.txt is missing PASSWORD configuration")
    
    return config


SMTP_CONFIGS = {
    "gmail.com": {"server": "smtp.gmail.com", "port": 587, "encryption": "TLS"},
    "qq.com": {"server": "smtp.qq.com", "port": 465, "encryption": "SSL"},
    "outlook.com": {"server": "smtp-mail.outlook.com", "port": 587, "encryption": "TLS"},
    "163.com": {"server": "smtp.163.com", "port": 465, "encryption": "SSL"},
    "126.com": {"server": "smtp.126.com", "port": 465, "encryption": "SSL"},
    "sina.com": {"server": "smtp.sina.com", "port": 465, "encryption": "SSL"},
    "aliyun.com": {"server": "smtp.aliyun.com", "port": 465, "encryption": "TLS"},
    "yandex.com": {"server": "smtp.yandex.com", "port": 465, "encryption": "TLS"},
}


def get_smtp_config(email: str) -> dict:

    domain = email.split("@")[-1].lower()
    
    if domain in SMTP_CONFIGS:
        return SMTP_CONFIGS[domain]
    
    return {
        "server": f"smtp.{domain}",
        "port": 587,
        "encryption": "TLS"
    }


def send_html_email(
    from_email: str,
    password: str,
    to_emails: List[str],
    subject: str,
    html_content: str,
    image_url: Optional[str] = None,
    custom_smtp_server: Optional[str] = None,
    custom_smtp_port: Optional[int] = None,
) -> bool:
    """
    send the generated HTML report via email with optional heatmap image attachment
    """
    try:
        password_clean = password.replace('\xa0', ' ')  # substitute the non-breaking space
        
        html_content = html_content.replace('\xa0', ' ')  # substitute the non-breaking space with a regular space
        
        if custom_smtp_server and custom_smtp_port:
            smtp_server = custom_smtp_server
            smtp_port = int(custom_smtp_port)
            use_tls = smtp_port == 587
        else:
            config = get_smtp_config(from_email)
            smtp_server = config["server"]
            smtp_port = config["port"]
            use_tls = config["encryption"] == "TLS"
        
        msg = MIMEMultipart("related")
        msg["From"] = formataddr(("Business Agent", from_email))
        msg["To"] = ", ".join(to_emails)
        msg["Subject"] = Header(subject, "utf-8")
        msg["Date"] = formatdate(localtime=True)
        msg["Message-ID"] = make_msgid()
        msg["MIME-Version"] = "1.0"
        msg["Content-Type"] = "multipart/related; charset=utf-8"
        
        msg_alternative = MIMEMultipart("alternative")
        msg.attach(msg_alternative)
        
        text_content = f"Business Agent News Report\n\nPlease use HTML-supported email client to view this email."
        text_part = MIMEText(text_content, "plain", "utf-8")
        msg_alternative.attach(text_part)
        
        html_part = MIMEText(html_content, "html", "utf-8")
        msg_alternative.attach(html_part)
        
        if image_url:
            try:
                print(f"📥 Downloading image from {image_url[:50]}...")
                image_data = urllib.request.urlopen(image_url).read()
                image = MIMEImage(image_data)
                image.add_header('Content-ID', '<heatmap_image>')
                image.add_header('Content-Disposition', 'inline', filename='heatmap.png')
                msg.attach(image)
                print("✅ Image attached to email")
            except Exception as e:
                print(f"⚠️  Warning: Failed to attach image: {e}")
        
        print(f"🔐 Connecting to SMTP: {smtp_server}:{smtp_port}")
        
        try:
            if use_tls:
                server = smtplib.SMTP(smtp_server, smtp_port, timeout=30)
                server.starttls()
            else:
                server = smtplib.SMTP_SSL(smtp_server, smtp_port, timeout=30)
            
            server.login(from_email, password_clean)
            server.send_message(msg, from_addr=from_email, to_addrs=to_emails)
            server.quit()
            
            print(f"✅ Email sent successfully to {', '.join(to_emails)}")
            return True
        
        except smtplib.SMTPAuthenticationError:
            print("❌ Email send failed: Authentication error. Check email and password/auth code.")
            return False
        except smtplib.SMTPConnectError:
            print(f"❌ Email send failed: Cannot connect to {smtp_server}:{smtp_port}")
            return False
        except Exception as e:
            print(f"❌ Email send failed: {str(e)}")
            return False
    
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def generate_report_with_heatmap(
    trending_keywords: List,
    articles: List,
    keywords_list: List[str],
    image_url: Optional[str] = None,
    summary_text: Optional[str] = None,
    title: str = "Business News Report"
) -> str:
    """
    generate the HTML report content with optional heatmap image and AI summary
    """
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    keywords_html = ""
    if trending_keywords:
        keywords_html = "<h2>🔥 Trending Keywords</h2><table border='1' cellpadding='10' style='width:100%; border-collapse:collapse;'>"
        for rank, (keyword, count) in enumerate(trending_keywords[:15], 1):
            bar_length = min(count * 5, 100)
            keywords_html += f"""
            <tr>
                <td>{rank}</td>
                <td><strong>{keyword}</strong></td>
                <td>{count}</td>
                <td><div style='width:100px; height:20px; background-color:#e0e0e0;'><div style='width:{bar_length}px; height:20px; background-color:#ff6b6b;'></div></div></td>
            </tr>
            """
        keywords_html += "</table>"
    
    heatmap_html = ""
    if image_url:
        heatmap_html = f"""
        <h2>📊 Keyword Heatmap</h2>
        <div style='text-align: center; margin: 20px 0;'>
            <img src='cid:heatmap_image' style='max-width: 100%; height: auto; border-radius: 8px;'>
        </div>
        """
    
    summary_html = ""
    if summary_text:
        summary_html = f"""
        <h2>🧠 AI-Generated Summary</h2>
        <div style='background-color: #f0f7ff; padding: 15px; border-left: 4px solid #2196F3; border-radius: 4px; margin-bottom: 20px;'>
            <p style='color: #333; line-height: 1.6; margin: 0;'>{summary_text}</p>
        </div>
        """
    
    articles_by_keyword = {}
    for keyword in keywords_list:
        articles_by_keyword[keyword] = []
    
    for article in articles:
        top_keyword = article.get('top_keyword', 'Other')
        if top_keyword in articles_by_keyword:
            articles_by_keyword[top_keyword].append(article)
    
    articles_html = "<h2>📰 News by Category</h2>"
    article_count = 0
    
    for keyword in keywords_list:
        keyword_articles = articles_by_keyword.get(keyword, [])
        if keyword_articles:
            articles_html += f"<h3 style='color: #ff6b6b; margin-top: 20px;'>📌 {keyword.upper()} ({len(keyword_articles)} articles)</h3>"
            
            for article in keyword_articles[:5]:  
                article_count += 1
                similarity = article.get('similarity_score', 0)
                title_text = article.get('title', '')
                source = article.get('source', {}).get('name', 'Unknown')
                published = article.get('publishedAt', '')[:10]
                url = article.get('url', '#')
                
                articles_html += f"""
                <div style='margin-bottom: 15px; padding: 10px; border-left: 4px solid #ff6b6b; background-color: #fafafa;'>
                    <p><strong>[{article_count}] {title_text}</strong></p>
                    <p style='font-size: 12px; color: #666;'>
                        Source: <strong>{source}</strong> | 
                        Relevance: <strong>{similarity:.0%}</strong> | 
                        Date: <strong>{published}</strong>
                    </p>
                    <p><a href='{url}' style='color: #ff6b6b; text-decoration: none;'>Read More →</a></p>
                </div>
                """
    
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <title>{title}</title>
        <style>
            body {{ 
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                margin: 0;
                padding: 20px;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            }}
            .container {{ 
                max-width: 900px;
                margin: 0 auto;
                background-color: white;
                padding: 30px;
                border-radius: 12px;
                box-shadow: 0 10px 30px rgba(0,0,0,0.3);
            }}
            h1 {{ 
                color: #333;
                border-bottom: 4px solid #ff6b6b;
                padding-bottom: 15px;
                margin-bottom: 30px;
            }}
            h2 {{ 
                color: #555;
                margin-top: 30px;
                font-size: 20px;
            }}
            h3 {{
                font-size: 16px;
                margin-bottom: 15px;
            }}
            table {{ 
                width: 100%;
                border-collapse: collapse;
                margin-bottom: 20px;
            }}
            th, td {{
                padding: 12px;
                text-align: left;
                border-bottom: 1px solid #ddd;
            }}
            th {{
                background-color: #f5f5f5;
                font-weight: bold;
            }}
            a {{ 
                color: #ff6b6b;
                text-decoration: none;
            }}
            a:hover {{ 
                text-decoration: underline;
            }}
            .footer {{ 
                margin-top: 40px;
                text-align: center;
                color: #999;
                font-size: 12px;
                border-top: 1px solid #ddd;
                padding-top: 20px;
            }}
            .timestamp {{
                color: #999;
                font-size: 13px;
                margin: 10px 0;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🚀 {title}</h1>
            <div class="timestamp">Generated: {now}</div>
            
            {keywords_html}
            
            {heatmap_html}
            
            {summary_html}
            
            {articles_html}
            
            <div class="footer">
                <p>Business Agent - Automated News Intelligence System</p>
                <p style='margin-top: 10px;'>Powered by AI-driven News Analysis | Next report: 24h later</p>
            </div>
        </div>
    </body>
    </html>
    """
    
    return html


# Backward compatibility
def load_email_config(config_file: str = "email_config.txt") -> dict:
    """Backward compatibility function - loads from email_config.txt or config.txt"""
    config_path = Path(config_file)
    
    if not config_path.exists():
        # Try config.txt instead
        config_path = Path("config.txt")
        if not config_path.exists():
            raise FileNotFoundError(f"File not found: {config_file}")
    
    config = load_config(str(config_path))
    return {
        'from_email': config['email'],
        'password': config['password'],
        'to_emails': [config['email']]
    }


if __name__ == "__main__":
    sample_keywords = [
        ('stock', 7),
        ('earnings', 3),
        ('market', 3),
    ]
    
    sample_articles = [
        {
            'title': 'Stock Market Surge Driven by Tech earnings',
            'source': {'name': 'Reuters'},
            'top_keyword': 'stock',
            'similarity_score': 0.95,
            'publishedAt': '2026-04-19',
            'url': 'https://example.com/article1'
        },
        {
            'title': 'S&P 500 reaches record high',
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
        }
    ]
    
    keywords_list = ['stock', 'market', 'earnings', 'economy', 'nasdaq']
    
    html = generate_report_with_heatmap(
        trending_keywords=sample_keywords,
        articles=sample_articles,
        keywords_list=keywords_list,
        image_url=None,  
        title="Business News Intelligence Report"
    )
    
    try:
        config = load_config()
        success = send_html_email(
            from_email=config['email'],
            password=config['password'],
            to_emails=[config['email']],
            subject="Business Agent - Test Report",
            html_content=html,
            image_url=None
        )
        
        if success:
            print("✅ Successfully sent test email with generated report!")
        else:
            print("❌ Failed to send test email. Please check the configuration.")
    
    except FileNotFoundError as e:
        print(f"❌ Error: {e}")
        print("Please edit the config.txt file and enter your email information.")
    except ValueError as e:
        print(f"❌ Error: {e}")
        print("Please check the config.txt file for missing configurations.")
