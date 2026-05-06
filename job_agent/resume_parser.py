"""
Resume Parser - Reads a resume file and extracts a structured profile using Azure OpenAI.
Supports .txt and .pdf formats.
"""

import json
from pathlib import Path
from typing import Optional
from openai import AzureOpenAI


def read_resume(path: str) -> str:
    """
    Read resume content from a .txt or .pdf file.

    Args:
        path: File path to the resume

    Returns:
        Plain text content of the resume
    """
    file_path = Path(path)

    if not file_path.exists():
        raise FileNotFoundError(f"Resume file not found: {path}")

    suffix = file_path.suffix.lower()

    if suffix == '.txt':
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()

    elif suffix == '.pdf':
        try:
            import PyPDF2
            text_parts = []
            with open(file_path, 'rb') as f:
                reader = PyPDF2.PdfReader(f)
                for page in reader.pages:
                    text_parts.append(page.extract_text() or '')
            return '\n'.join(text_parts)
        except ImportError:
            raise ImportError(
                "PyPDF2 is required to parse PDF resumes. "
                "Run: pip install PyPDF2"
            )

    else:
        raise ValueError(f"Unsupported resume format: {suffix}. Use .txt or .pdf")


def extract_profile(resume_text: str, client: AzureOpenAI, model_name: str = 'gpt-4o') -> dict:
    """
    Use Azure OpenAI to extract a structured profile from resume text.

    Args:
        resume_text: Raw resume text
        client: Initialized AzureOpenAI client
        model_name: Model to use

    Returns:
        dict with keys: skills (list), roles (list), summary (str)
    """
    prompt = f"""You are a career advisor. Extract the key information from this resume and return a JSON object with exactly these fields:
- "skills": list of technical and soft skills (strings)
- "roles": list of job titles or roles this person is suitable for (strings, e.g. "software engineer intern", "data analyst intern")
- "summary": one sentence describing the candidate's background and strengths

Resume:
{resume_text[:3000]}

Return ONLY valid JSON, no markdown, no explanation."""

    try:
        response = client.chat.completions.create(
            model=model_name,
            messages=[
                {"role": "system", "content": "You are a precise career advisor. Always respond with valid JSON only."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=500,
            temperature=0.3,
        )

        content = response.choices[0].message.content or ''
        content = content.strip()

        # Strip markdown code fences if present
        if content.startswith('```'):
            lines = content.split('\n')
            content = '\n'.join(lines[1:-1])

        profile = json.loads(content)

        # Normalise keys in case model capitalises them
        return {
            'skills': profile.get('skills', []),
            'roles': profile.get('roles', []),
            'summary': profile.get('summary', ''),
        }

    except json.JSONDecodeError:
        print("Could not parse profile JSON from model, using fallback extraction")
        # Fallback: return raw text as summary only
        return {'skills': [], 'roles': ['intern', 'internship'], 'summary': resume_text[:200]}
    except Exception as e:
        print(f"Error extracting profile: {e}")
        return {'skills': [], 'roles': ['intern', 'internship'], 'summary': ''}


if __name__ == '__main__':
    # Quick test with a sample resume.txt
    sample = """
    John Doe | johndoe@email.com | github.com/johndoe

    Education:
    BSc Computer Science, HKUST, 2024

    Skills:
    Python, SQL, Machine Learning, TensorFlow, React, Node.js, Git

    Experience:
    - Research Assistant, HKUST AI Lab (2023): built NLP pipelines
    - Part-time Developer, Startup X (2022): built REST APIs with Flask

    Projects:
    - Stock price predictor using LSTM (Python, TensorFlow)
    - E-commerce site (React + Node.js)
    """

    resume_path = Path('resume.txt')
    resume_path.write_text(sample)

    text = read_resume('resume.txt')
    print("Resume loaded, length:", len(text))
    print("(Profile extraction requires Azure credentials)")
