"""analysis/prompts.py — All AI prompts, UPSC syllabus-aware."""
import json

SYLLABUS = """
GS1: Modern Indian History | World History | Indian Culture | Geography | Indian Society | Women | Urbanisation
GS2: Constitution | Parliamentary System | Federalism | Judiciary | Governance | Social Justice | IR | Neighbourhood | Bilateral Groups | UN
GS3: Economy | Planning | Budget | Agriculture | Food Security | Industry | Infrastructure | S&T | Space | Environment | Biodiversity | Climate | Disaster Management | Internal Security | Cybersecurity
GS4: Ethics | Integrity | Aptitude | Emotional Intelligence | Public Service Values | Probity | Case Studies
Essay: Multi-dimensional analytical essays drawing on all GS papers
"""

def tagger_prompt(title, text, source):
    return f"""You are a UPSC Civil Services examiner. Classify this news article for UPSC preparation.
{SYLLABUS}
Source: {source}
Title: {title}
Text: {text}

Return ONLY valid JSON:
{{
  "gs_papers": ["GS2","GS3"],
  "syllabus_sections": ["Parliamentary System","Fiscal Policy"],
  "subject_tags": ["Polity","Economy"],
  "prelims_relevance": 8,
  "mains_relevance": 7,
  "difficulty_prelims": "medium",
  "topics": ["GST Council","Cooperative Federalism"],
  "keywords": ["indirect tax","revenue sharing","states"],
  "is_current_affairs": true
}}
Rules: prelims_relevance 0-10 (8+ if specific facts testable as MCQ). mains_relevance 0-10 (8+ if requires 200+ word analytical answer). difficulty_prelims: easy|medium|hard.
Respond ONLY with valid JSON. No markdown."""

def summariser_prompt(title, text, source, gs_papers):
    papers = ", ".join(gs_papers) if gs_papers else "GS"
    return f"""You are a UPSC content writer. Summarise this article for aspirants.
{SYLLABUS}
Article: {title}
Source: {source}
GS Papers: {papers}
Text: {text}

Return ONLY valid JSON:
{{
  "short_summary": "3-4 sentence summary, max 80 words, facts only, ends with exam relevance line.",
  "detailed_summary": "6-8 sentence comprehensive summary, max 200 words, covers who/what/where/when/why/how and implications.",
  "upsc_significance": "2-3 sentences. Specific: which syllabus section, likely question type, what aspirant should note."
}}
Respond ONLY with valid JSON. No markdown."""

def insights_prompt(title, text, source, gs_papers):
    papers = ", ".join(gs_papers) if gs_papers else "GS"
    return f"""You are a UPSC subject matter expert. Extract structured information.
{SYLLABUS}
Article: {title}
Source: {source}
GS Papers: {papers}
Text: {text}

Return ONLY valid JSON:
{{
  "background": "2-3 sentences of historical/policy context.",
  "causes": ["cause 1","cause 2"],
  "consequences": ["consequence 1","consequence 2"],
  "constitutional_articles": ["Article 21","Article 280"],
  "acts_and_laws": ["Right to Education Act 2009"],
  "committees_commissions": ["14th Finance Commission"],
  "government_schemes": ["PM-KISAN","MGNREGS"],
  "international_orgs": ["WTO","IMF","UNEP"],
  "related_concepts": ["Cooperative Federalism","Fiscal Federalism"],
  "key_facts": ["3 specific facts with numbers/dates/names likely in Prelims MCQ"],
  "way_forward": "2-3 sentences on policy directions relevant for Mains answer writing."
}}
Respond ONLY with valid JSON. No markdown."""

def questions_prompt(title, short_summary, insights, gs_papers):
    papers = ", ".join(gs_papers) if gs_papers else "GS"
    kf = json.dumps(insights.get("key_facts",[]), ensure_ascii=False)
    co = json.dumps(insights.get("related_concepts",[]), ensure_ascii=False)
    return f"""You are a UPSC question paper setter. Generate practice questions.
Article: {title}
Summary: {short_summary}
GS Papers: {papers}
Key Facts: {kf}
Related Concepts: {co}

Return ONLY valid JSON array with exactly 4 questions (2 prelims, 2 mains):
[
  {{
    "question_type": "prelims",
    "question_text": "With reference to [topic], which of the following statements is/are correct?\n1. Statement one\n2. Statement two\nSelect the correct answer:",
    "options": ["A. 1 only","B. 2 only","C. Both 1 and 2","D. Neither 1 nor 2"],
    "correct_answer": "C",
    "explanation": "Why C is correct, why others are wrong.",
    "marks": 2, "difficulty": "medium"
  }},
  {{
    "question_type": "prelims",
    "question_text": "Consider the following pairs: [pair list]. Which is/are correctly matched?",
    "options": ["A. 1 only","B. 2 only","C. 1 and 2","D. None"],
    "correct_answer": "A",
    "explanation": "Explanation.",
    "marks": 2, "difficulty": "hard"
  }},
  {{
    "question_type": "mains",
    "question_text": "Discuss the significance of [topic] in the context of [theme]. What are the challenges and way forward? (150 words)",
    "options": [], "correct_answer": "",
    "explanation": "Model outline: 1)Intro 2)Significance 3)Challenges 4)Way forward 5)Conclusion",
    "marks": 10, "difficulty": "medium"
  }},
  {{
    "question_type": "mains",
    "question_text": "Critically analyse [policy/development] and its implications for [governance theme]. (250 words)",
    "options": [], "correct_answer": "",
    "explanation": "Model outline with 5-6 key points aspirant must cover.",
    "marks": 15, "difficulty": "hard"
  }}
]
Respond ONLY with valid JSON array. No markdown."""

def pyq_linker_prompt(title, topics, concepts):
    return f"""You are a UPSC expert with knowledge of all previous year papers 1979-2023.
Article: {title}
Topics: {json.dumps(topics, ensure_ascii=False)}
Concepts: {json.dumps(concepts, ensure_ascii=False)}

Return ONLY valid JSON array of genuine PYQ connections (empty [] if not confident):
[
  {{
    "pyq_year": 2019,
    "pyq_paper": "Prelims GS",
    "pyq_question": "Exact question text you are confident about.",
    "connection_type": "direct",
    "connection_relevance": "How this article connects to this PYQ."
  }}
]
Rules: Only include questions you are genuinely confident about. Return [] if uncertain. Max 3 connections. connection_type: direct|thematic|conceptual.
Respond ONLY with valid JSON array. No markdown."""
