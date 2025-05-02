from openai import OpenAI
import fitz  # PyMuPDF
import os
from tenacity import retry, wait_random_exponential, stop_after_attempt, retry_if_exception_type
from openai import RateLimitError, APIError

# ✅ OpenAI client initialized with secret API key
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

@retry(
    wait=wait_random_exponential(min=1, max=10),
    stop=stop_after_attempt(3),
    retry=retry_if_exception_type((RateLimitError, APIError))
)
def ask_openai(prompt):
    """Send a prompt to OpenAI with retry logic."""
    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3
    )
    return response.choices[0].message.content

def extract_text(pdf_path):
    """Extract all text from a PDF file using PyMuPDF."""
    doc = fitz.open(pdf_path)
    return "\n".join(page.get_text() for page in doc)

def summarize_audit(text, filename):
    """Generate a structured, one-page audit summary."""
    prompt = f"""
You are a senior auditor. Analyze the following audit report and summarize it in a clear and concise format. Limit the response to 1 page, using this structure:

### Audit of {filename}

1. Audit Topic
- Brief title or theme of the audit

2. Main Findings
- Key risks or findings (2–4 bullet points)

3. Measures Proposed
- Actionable steps or controls (2–4 bullet points)

4. Future Steps
- Follow-up recommendations (2–3 bullet points)

AUDIT TEXT:
{text[:8000]}
"""
    return ask_openai(prompt)

def compare_audits(summaries):
    """Compare summaries to identify shared risks and differences."""
    joined = "\n\n".join(summaries)
    prompt = (
        "Compare the following audit summaries and highlight:\n"
        "- Common audit topics\n"
        "- Differences in findings or measures\n"
        "- Shared risks or recommendations\n\n"
        f"{joined}"
    )
    return ask_openai(prompt)

def extract_learnings(summaries):
    """Extract 3–5 actionable lessons for future audits."""
    joined = "\n\n".join(summaries)
    prompt = (
        "Based on the following audit summaries, extract 3–5 concise audit lessons or best practices "
        "to improve future audit processes:\n\n"
        f"{joined}"
    )
    return ask_openai(prompt)

def analyze_audits(paths, filenames):
    """Main analysis pipeline for processing all audit PDFs."""
    summaries = []
    for path, name in zip(paths, filenames):
        text = extract_text(path)
        summary = summarize_audit(text, name)
        summaries.append(summary)

    comparison = compare_audits(summaries)
    learnings = extract_learnings(summaries)

    full_text = "=== AUDIT SUMMARIES ===\n\n" + "\n\n".join(summaries)
    full_text += "\n\n=== COMPARISON ===\n\n" + comparison
    full_text += "\n\n=== LEARNINGS ===\n\n" + learnings

    return summaries, comparison, learnings, full_text
