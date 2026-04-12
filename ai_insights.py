import requests
import urllib.parse
import json
import re
from lxml import html as lxml_html


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


_UNITS = (
    r'mg/dL|g/dL|mmol/L|µmol/L|umol/L|nmol/L|pmol/L|ng/mL|ng/dL|ng/L|µg/dL|ug/dL|'
    r'µg/L|ug/L|IU/L|mIU/L|mIU/mL|U/L|kU/L|µIU/mL|uIU/mL|mIU/mL|'
    r'g/L|mEq/L|mmol/mol|pg/mL|fL|fl|%|'
    r'x10\^9/L|×10\^9/L|10\^9/L|\*10\^9/L|cells/µL|cells/uL|per µL|per uL|'
    r'ratio|index|titre|titer'
)

_RANGE_RE = re.compile(
    rf'(\d+\.?\d*)\s*(?:[-–—]|to)\s*(\d+\.?\d*)\s*({_UNITS})',
    re.IGNORECASE
)

_MALE_CTX_RE = re.compile(
    rf'(?:male|men|man|m)[^.]*?(\d+\.?\d*)\s*(?:[-–—]|to)\s*(\d+\.?\d*)\s*({_UNITS})',
    re.IGNORECASE
)
_FEMALE_CTX_RE = re.compile(
    rf'(?:female|women|woman|f)[^.]*?(\d+\.?\d*)\s*(?:[-–—]|to)\s*(\d+\.?\d*)\s*({_UNITS})',
    re.IGNORECASE
)

_CATEGORY_KEYWORDS = {
    'Haematology': ['haemoglobin', 'hemoglobin', 'haematocrit', 'hematocrit', 'platelet', 'wbc', 'rbc',
                    'white blood cell', 'red blood cell', 'neutrophil', 'lymphocyte', 'eosinophil',
                    'basophil', 'monocyte', 'mcv', 'mch', 'mchc', 'full blood count', 'complete blood count'],
    'Biochemistry': ['albumin', 'total protein', 'globulin', 'bilirubin', 'alkaline phosphatase',
                     'alt', 'ast', 'ggt', 'ldh', 'uric acid', 'creatinine', 'urea', 'sodium',
                     'potassium', 'chloride', 'bicarbonate'],
    'Lipid Profile': ['cholesterol', 'ldl', 'hdl', 'triglyceride', 'vldl', 'lipid'],
    'Liver Function': ['bilirubin', 'alt', 'ast', 'alp', 'ggt', 'albumin', 'liver'],
    'Renal Function': ['creatinine', 'urea', 'egfr', 'bun', 'renal', 'kidney', 'cystatin'],
    'Thyroid Function': ['tsh', 'ft3', 'ft4', 't3', 't4', 'thyroid', 'thyroxine', 'triiodothyronine'],
    'Diabetes & Metabolic': ['glucose', 'hba1c', 'insulin', 'fasting', 'c-peptide', 'glycated'],
    'Cardiac Markers': ['troponin', 'bnp', 'creatine kinase', 'ck-mb', 'myoglobin', 'cardiac'],
    'Coagulation': ['pt', 'aptt', 'inr', 'fibrinogen', 'd-dimer', 'coagulation', 'clotting'],
    'Hormones': ['testosterone', 'oestrogen', 'estrogen', 'cortisol', 'prolactin', 'lh', 'fsh',
                 'progesterone', 'dhea', 'hormone'],
    'Vitamins & Minerals': ['vitamin', 'folate', 'ferritin', 'iron', 'calcium', 'magnesium',
                            'phosphate', 'zinc', 'selenium', 'copper'],
    'Electrolytes': ['sodium', 'potassium', 'chloride', 'bicarbonate', 'electrolyte'],
    'Tumour Markers': ['psa', 'cea', 'ca 125', 'ca125', 'afp', 'ca 19-9', 'tumour marker', 'tumor marker'],
    'Immunology': ['ige', 'igg', 'iga', 'igm', 'c3', 'c4', 'complement', 'ana', 'crp', 'esr'],
}


def _guess_category(test_name, text=''):
    combined = (test_name + ' ' + text).lower()
    for cat, keywords in _CATEGORY_KEYWORDS.items():
        for kw in keywords:
            if kw in combined:
                return cat
    return 'Other'


def _clean_html(raw_html):
    """Strip HTML tags and decode common entities, returning plain text."""
    text = re.sub(r'<script[^>]*>.*?</script>', ' ', raw_html, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r'<style[^>]*>.*?</style>', ' ', text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r'<[^>]+>', ' ', text)
    text = re.sub(r'&nbsp;', ' ', text)
    text = re.sub(r'&amp;', '&', text)
    text = re.sub(r'&lt;', '<', text)
    text = re.sub(r'&gt;', '>', text)
    text = re.sub(r'&#\d+;', ' ', text)
    text = re.sub(r'&[a-zA-Z]+;', ' ', text)
    text = re.sub(r'\s+', ' ', text)
    return text.strip()


def _extract_ranges(text):
    """
    Extract the best male/female reference range and unit from a block of text.
    Returns (male_min, male_max, female_min, female_max, unit) — any may be None/''.
    """
    male_min = male_max = female_min = female_max = None
    unit = ''

    m_match = _MALE_CTX_RE.search(text)
    if m_match:
        male_min, male_max, unit = float(m_match.group(1)), float(m_match.group(2)), m_match.group(3)

    f_match = _FEMALE_CTX_RE.search(text)
    if f_match:
        female_min, female_max = float(f_match.group(1)), float(f_match.group(2))
        if not unit:
            unit = f_match.group(3)

    if male_min is None and female_min is None:
        gen = _RANGE_RE.search(text)
        if gen:
            male_min = female_min = float(gen.group(1))
            male_max = female_max = float(gen.group(2))
            unit = gen.group(3)
    elif male_min is not None and female_min is None:
        female_min, female_max = male_min, male_max
    elif female_min is not None and male_min is None:
        male_min, male_max = female_min, female_max

    return male_min, male_max, female_min, female_max, unit


_SCRAPE_HEADERS = {
    'User-Agent': (
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
        'AppleWebKit/537.36 (KHTML, like Gecko) '
        'Chrome/120.0.0.0 Safari/537.36'
    ),
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.5',
}


def scrape_test_standard_info(test_name):
    """
    Search the web (no API key needed) to gather blood test reference information.
    Returns (dict_or_None, error_str_or_None, debug_info_dict).
    debug_info is always returned so callers can show what was fetched.
    """
    result = dict(
        male_min=None, male_max=None,
        female_min=None, female_max=None,
        unit='', description='', aliases='', category='Other'
    )
    collected_text = ''
    debug = {
        'queries': [],       # list of dicts: {source, query_url, chars_collected}
        'collected_text': '' # will be filled at end
    }

    # ── 1. DuckDuckGo Instant Answer API ─────────────────────────────────────
    ia_query = f'{test_name} blood test'
    ia_url = f'https://api.duckduckgo.com/?q={urllib.parse.quote(ia_query)}&format=json&no_html=1&skip_disambig=1'
    try:
        ia_resp = requests.get(ia_url, headers=_SCRAPE_HEADERS, timeout=10)
        ia_data = ia_resp.json()
        abstract = ia_data.get('AbstractText') or ia_data.get('Answer') or ''
        if abstract:
            result['description'] = abstract[:500]
            collected_text += ' ' + abstract
        debug['queries'].append({
            'source': 'DuckDuckGo Instant Answer API',
            'url': ia_url,
            'status': ia_resp.status_code,
            'chars': len(abstract),
            'got': abstract[:300] if abstract else '(empty — no AbstractText or Answer)',
        })
    except Exception as e:
        debug['queries'].append({'source': 'DuckDuckGo Instant Answer API', 'url': ia_url, 'error': str(e)})

    # ── 2. Wikipedia summary API ──────────────────────────────────────────────
    slug = test_name.replace(' ', '_')
    wiki_url = f'https://en.wikipedia.org/api/rest_v1/page/summary/{urllib.parse.quote(slug)}'
    try:
        wiki_resp = requests.get(wiki_url, headers=_SCRAPE_HEADERS, timeout=10)
        if wiki_resp.status_code == 200:
            wiki_data = wiki_resp.json()
            wiki_extract = wiki_data.get('extract', '')
            if wiki_extract and not result['description']:
                result['description'] = wiki_extract[:500]
            collected_text += ' ' + wiki_extract
            debug['queries'].append({
                'source': 'Wikipedia summary API',
                'url': wiki_url,
                'status': 200,
                'chars': len(wiki_extract),
                'got': wiki_extract[:300] if wiki_extract else '(empty)',
            })
        else:
            debug['queries'].append({
                'source': 'Wikipedia summary API',
                'url': wiki_url,
                'status': wiki_resp.status_code,
                'chars': 0,
                'got': f'HTTP {wiki_resp.status_code} — no article found',
            })
    except Exception as e:
        debug['queries'].append({'source': 'Wikipedia summary API', 'url': wiki_url, 'error': str(e)})

    # ── 3. DuckDuckGo HTML search ─────────────────────────────────────────────
    ddg_q = f'{test_name} blood test reference range normal adult male female'
    ddg_url = f'https://html.duckduckgo.com/html/?q={urllib.parse.quote(ddg_q)}'
    try:
        search_resp = requests.get(ddg_url, headers=_SCRAPE_HEADERS, timeout=15)
        search_text = _clean_html(search_resp.text)
        # Collect chunks near any mention of the test name (also try without spaces, e.g. "crp")
        search_terms = list({test_name.lower(), test_name.lower().replace(' ', ''), test_name.split()[0].lower()})
        chunks = []
        for term in search_terms:
            pos = 0
            while True:
                idx = search_text.lower().find(term, pos)
                if idx == -1:
                    break
                chunks.append(search_text[max(0, idx - 150): idx + 500])
                pos = idx + max(len(term), 1)
        collected_text += ' ' + ' '.join(chunks[:15])
        debug['queries'].append({
            'source': 'DuckDuckGo HTML search',
            'url': ddg_url,
            'status': search_resp.status_code,
            'chars': len(' '.join(chunks[:15])),
            'got': (' '.join(chunks[:3]))[:400] if chunks else '(test name not found in results)',
        })
    except Exception as e:
        debug['queries'].append({'source': 'DuckDuckGo HTML search', 'url': ddg_url, 'error': str(e)})
        if not collected_text.strip():
            debug['collected_text'] = collected_text
            return None, f"Web search failed: {e}", debug

    # ── 4. Targeted medical reference pages ───────────────────────────────────
    slug_dash = test_name.lower().replace(' ', '-')
    targeted = [
        f'https://medlineplus.gov/lab-tests/{slug_dash}-test/',
        f'https://www.labtestsonline.org.uk/tests/{slug_dash}',
    ]
    for t_url in targeted:
        try:
            r = requests.get(t_url, headers=_SCRAPE_HEADERS, timeout=10)
            if r.status_code == 200:
                page_text = _clean_html(r.text)
                snippet = page_text[:3000]
                collected_text += ' ' + snippet
                debug['queries'].append({
                    'source': f'Medical reference page ({t_url.split("/")[2]})',
                    'url': t_url,
                    'status': 200,
                    'chars': len(snippet),
                    'got': snippet[:300],
                })
                break
            else:
                debug['queries'].append({'source': f'Medical reference page ({t_url.split("/")[2]})', 'url': t_url, 'status': r.status_code, 'got': f'HTTP {r.status_code}'})
        except Exception as e:
            debug['queries'].append({'source': f'Medical reference page', 'url': t_url, 'error': str(e)})

    # ── 5. Parse ranges from everything collected ─────────────────────────────
    male_min, male_max, female_min, female_max, unit = _extract_ranges(collected_text)
    if male_min is not None:
        result['male_min'] = male_min
        result['male_max'] = male_max
        result['female_min'] = female_min
        result['female_max'] = female_max
        result['unit'] = unit

    # ── 6. Guess category ─────────────────────────────────────────────────────
    result['category'] = _guess_category(test_name, collected_text[:1000])

    debug['collected_text'] = collected_text[:4000]

    if not result['description'] and result['male_min'] is None:
        return None, (
            f"Could not find reference data for '{test_name}' from web search. "
            "Review the debug info below to see what was fetched."
        ), debug

    return result, None, debug


def scrape_test_explanation(test_name, value, unit, ref_min=None, ref_max=None, gender=''):
    """
    Search the web for a plain-language explanation of a blood test result.
    Returns (text_or_None, error_str_or_None, debug_info_dict).
    """
    debug = {'queries': [], 'collected_text': ''}
    parts = [test_name, 'blood test']
    if value not in (None, ''):
        parts.append(str(value))
    if unit:
        parts.append(unit)
    parts += ['meaning', 'clinical significance']
    ddg_q = ' '.join(parts)
    ddg_url = f'https://html.duckduckgo.com/html/?q={urllib.parse.quote(ddg_q)}'

    collected = ''
    try:
        resp = requests.get(ddg_url, headers=_SCRAPE_HEADERS, timeout=15)
        full_text = _clean_html(resp.text)
        search_terms = list({test_name.lower(), test_name.lower().replace(' ', ''), test_name.split()[0].lower()})
        chunks = []
        for term in search_terms:
            pos = 0
            while True:
                idx = full_text.lower().find(term, pos)
                if idx == -1:
                    break
                chunks.append(full_text[max(0, idx - 100): idx + 600])
                pos = idx + max(len(term), 1)
        collected = ' '.join(chunks[:12])
        debug['queries'].append({
            'source': 'DuckDuckGo HTML search',
            'url': ddg_url,
            'status': resp.status_code,
            'chars': len(collected),
            'got': collected[:400] if collected else '(no snippets found)',
        })
    except Exception as e:
        debug['queries'].append({'source': 'DuckDuckGo HTML search', 'url': ddg_url, 'error': str(e)})
        return None, f"Search failed: {e}", debug

    # Also try Wikipedia
    wiki_url = f'https://en.wikipedia.org/api/rest_v1/page/summary/{urllib.parse.quote(test_name.replace(" ", "_"))}'
    try:
        wr = requests.get(wiki_url, headers=_SCRAPE_HEADERS, timeout=10)
        if wr.status_code == 200:
            wiki_extract = wr.json().get('extract', '')
            collected = wiki_extract[:1500] + '\n\n' + collected
            debug['queries'].append({'source': 'Wikipedia', 'url': wiki_url, 'status': 200, 'chars': len(wiki_extract), 'got': wiki_extract[:200]})
    except Exception:
        pass

    debug['collected_text'] = collected[:4000]

    if not collected.strip():
        return None, "No results found. Try a more specific test name.", debug

    # Format a compact summary from snippets
    ref_line = ''
    if ref_min is not None and ref_max is not None:
        ref_line = f"Reference range: {ref_min}–{ref_max} {unit}. "
    gender_line = f"Patient gender: {gender}. " if gender else ''

    summary = (
        f"**Web search results for: {test_name}** ({value} {unit})\n"
        f"{ref_line}{gender_line}\n\n"
        "---\n"
        "*Extracted snippets from web search (unfiltered — always verify with a clinician):*\n\n"
        + collected[:3000]
    )
    return summary, None, debug


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
