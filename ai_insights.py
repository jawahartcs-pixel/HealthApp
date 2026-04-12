import requests
import urllib.parse
import json


SERVICES = {
    "ChatGPT": {
        "label": "ChatGPT (OpenAI)",
        "icon": "🤖",
        "url": "https://chatgpt.com/",
        "supports_url_query": False,
        "color": "#10a37f",
    },
    "Gemini": {
        "label": "Gemini (Google)",
        "icon": "✨",
        "url": "https://gemini.google.com/app",
        "supports_url_query": False,
        "color": "#4285f4",
    },
    "Grok": {
        "label": "Grok (xAI)",
        "icon": "⚡",
        "url": "https://x.com/i/grok",
        "supports_url_query": False,
        "color": "#1da1f2",
    },
    "Perplexity": {
        "label": "Perplexity",
        "icon": "🔍",
        "url": "https://www.perplexity.ai/",
        "supports_url_query": True,
        "color": "#6b5ce7",
    },
}


def build_test_prompt(patient_name, age, gender, test_name, value, unit, ref_min, ref_max):
    """Build a standardized prompt for AI analysis of a blood test result."""
    ref_range_str = "Not specified"
    if ref_min is not None and ref_max is not None:
        ref_range_str = f"{ref_min} – {ref_max} {unit}".strip()

    age_str = str(age) if age else "Unknown"
    gender_str = gender.title() if gender else "Unknown"
    value_str = f"{value} {unit}".strip() if unit else str(value)

    prompt = (
        f"Blood test analysis request:\n\n"
        f"Patient: {patient_name}, Age: {age_str}, Gender: {gender_str}\n"
        f"Test: {test_name}\n"
        f"Result: {value_str}\n"
        f"Normal reference range: {ref_range_str}\n\n"
        f"Please:\n"
        f"1. Explain what this test measures.\n"
        f"2. Describe what this result means — is it normal, high, or low?\n"
        f"3. What could this result indicate for a patient of this age and gender?\n"
        f"4. Any clinical concerns or recommendations?\n\n"
        f"Keep the explanation clear and concise for a healthcare professional."
    )
    return prompt


def get_quick_open_url(service, prompt):
    """Return URL to open the AI service. Perplexity supports direct query injection."""
    info = SERVICES.get(service, {})
    if info.get("supports_url_query"):
        encoded = urllib.parse.quote(prompt)
        return f"https://www.perplexity.ai/search?q={encoded}"
    return info.get("url", "")


def query_openai(prompt, api_key, model="gpt-4o-mini"):
    """Query OpenAI ChatGPT API and return the response text."""
    url = "https://api.openai.com/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    data = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 1200,
    }
    resp = requests.post(url, headers=headers, json=data, timeout=45)
    resp.raise_for_status()
    return resp.json()["choices"][0]["message"]["content"]


def query_gemini(prompt, api_key):
    """Query Google Gemini API and return the response text."""
    url = (
        f"https://generativelanguage.googleapis.com/v1beta/models/"
        f"gemini-1.5-flash:generateContent?key={api_key}"
    )
    headers = {"Content-Type": "application/json"}
    data = {"contents": [{"parts": [{"text": prompt}]}]}
    resp = requests.post(url, headers=headers, json=data, timeout=45)
    resp.raise_for_status()
    return resp.json()["candidates"][0]["content"]["parts"][0]["text"]


def query_grok(prompt, api_key):
    """Query xAI Grok API and return the response text."""
    url = "https://api.x.ai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    data = {
        "model": "grok-beta",
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 1200,
    }
    resp = requests.post(url, headers=headers, json=data, timeout=45)
    resp.raise_for_status()
    return resp.json()["choices"][0]["message"]["content"]


def query_perplexity(prompt, api_key):
    """Query Perplexity API and return the response text."""
    url = "https://api.perplexity.ai/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    data = {
        "model": "llama-3.1-sonar-small-128k-online",
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 1200,
    }
    resp = requests.post(url, headers=headers, json=data, timeout=45)
    resp.raise_for_status()
    return resp.json()["choices"][0]["message"]["content"]


_STANDARD_INFO_PROMPT = """For the blood test called '{test_name}', provide reference information.
Respond ONLY with a single valid JSON object — no markdown, no explanation, no code fences.
Use exactly these keys:
{{
  "male_min": <number or null>,
  "male_max": <number or null>,
  "female_min": <number or null>,
  "female_max": <number or null>,
  "unit": "<unit string, e.g. mg/dL>",
  "description": "<1-2 sentence clinical description of what this test measures>",
  "aliases": "<comma-separated list of common alternative names for this test>",
  "category": "<one of: Haematology, Biochemistry, Lipid Profile, Liver Function, Renal Function, Thyroid Function, Diabetes & Metabolic, Cardiac Markers, Coagulation, Immunology, Tumour Markers, Hormones, Vitamins & Minerals, Electrolytes, Urinalysis, Other>"
}}
Use internationally recognised adult reference ranges. If male and female ranges are the same, repeat the values for both."""


def fetch_test_standard_info(test_name, service_name, api_key):
    """
    Query an AI service to auto-populate investigation standard fields.
    Returns (dict with keys male_min/male_max/female_min/female_max/unit/description/aliases/category, error_str).
    """
    prompt = _STANDARD_INFO_PROMPT.format(test_name=test_name)
    text, err = query_service(service_name, prompt, api_key)
    if err:
        return None, err
    # Parse JSON from the response (strip any accidental markdown fences)
    import re as _re
    json_text = text.strip()
    # Remove markdown code fences if present
    json_text = _re.sub(r'^```(?:json)?', '', json_text, flags=_re.MULTILINE)
    json_text = _re.sub(r'```$', '', json_text, flags=_re.MULTILINE)
    json_text = json_text.strip()
    try:
        data = json.loads(json_text)
        return data, None
    except json.JSONDecodeError:
        # Try to extract JSON object with regex
        match = _re.search(r'\{.*\}', json_text, _re.DOTALL)
        if match:
            try:
                data = json.loads(match.group())
                return data, None
            except json.JSONDecodeError:
                pass
        return None, f"Could not parse AI response as JSON. Raw response:\n{text[:500]}"


def query_service(service_name, prompt, api_key):
    """Dispatch query to the correct AI service. Returns (text, error)."""
    try:
        if service_name == "ChatGPT":
            return query_openai(prompt, api_key), None
        elif service_name == "Gemini":
            return query_gemini(prompt, api_key), None
        elif service_name == "Grok":
            return query_grok(prompt, api_key), None
        elif service_name == "Perplexity":
            return query_perplexity(prompt, api_key), None
        else:
            return None, f"Unknown service: {service_name}"
    except requests.exceptions.HTTPError as e:
        status = e.response.status_code if e.response is not None else "?"
        if status == 401:
            return None, f"Invalid API key (401 Unauthorized)"
        elif status == 429:
            return None, f"Rate limit exceeded (429). Please try again shortly."
        else:
            return None, f"HTTP error {status}: {e}"
    except requests.exceptions.Timeout:
        return None, "Request timed out. The service may be slow — try again."
    except Exception as e:
        return None, str(e)
