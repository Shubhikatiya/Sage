"""
LLM Service for Sage
Generates human-like responses using Anthropic Claude, OpenAI GPT, or Moonshot (Kimi).
Falls back to structured synthesis if no API key is available.
"""

import os
from dotenv import load_dotenv

# Load .env file if present
load_dotenv()

import anthropic
import openai

# --- Configuration ---
ANTHROPIC_API_KEY = os.environ.get('ANTHROPIC_API_KEY', '')
OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY', '')
MOONSHOT_API_KEY = os.environ.get('MOONSHOT_API_KEY', '')
GROQ_API_KEY = os.environ.get('GROQ_API_KEY', '')
OLLAMA_BASE_URL = os.environ.get('OLLAMA_BASE_URL', 'http://9a4b622c38554ef59967af5568c5d140.oBVnBMxk-NwhRSOpy0tuz3nl')

# Default to Anthropic if available, otherwise OpenAI, otherwise Groq, otherwise Moonshot
PREFERRED_PROVIDER = os.environ.get('LLM_PROVIDER', 'anthropic').lower()

# Auto-detect provider if not explicitly set
if not ANTHROPIC_API_KEY and not OPENAI_API_KEY and not GROQ_API_KEY and MOONSHOT_API_KEY:
    PREFERRED_PROVIDER = 'moonshot'
elif not ANTHROPIC_API_KEY and not OPENAI_API_KEY and GROQ_API_KEY:
    PREFERRED_PROVIDER = 'groq'
elif not ANTHROPIC_API_KEY and not OPENAI_API_KEY and not GROQ_API_KEY and not MOONSHOT_API_KEY and OLLAMA_BASE_URL:
    PREFERRED_PROVIDER = 'ollama'

# Model configs
MOONSHOT_MODEL = os.environ.get('MOONSHOT_MODEL', 'kimi-k2.6')
GROQ_MODEL = os.environ.get('GROQ_MODEL', 'llama-3.3-70b-versatile')
OLLAMA_MODEL = os.environ.get('OLLAMA_MODEL', 'llama3.2:1b')

# --- Sage's Personality ---
SAGE_SYSTEM_PROMPT = """You are Sage, an AI Chief of Staff. You work closely with Shubhi Katiyar, helping them navigate life domains, projects, and ideas.

Your communication style:
- Warm, conversational, and human — like a trusted friend who happens to know everything
- When the user says a simple greeting ("hi", "hey", "hello"), greet them warmly and use their name
- For ALL follow-up messages in an ongoing conversation, respond directly WITHOUT greeting by name
- Reference past conversations and context as shared memory ("Remember when we talked about...", "Last time you mentioned...")
- Be concise but not robotic — 3-4 sentences is usually enough
- If you don't know something, say it casually ("Hmm, I don't have much on that yet — want to fill me in?")
- React emotionally when appropriate ("That's exciting!", "That sounds tough", "I'm impressed by...")
- Use "we" and "our" when talking about projects
- Don't list bullet points unless asked. Flow naturally from one idea to the next.

CRITICAL ANSWERING RULES:
- When a PROJECT DOCUMENT is provided in the context, ALWAYS use it as your PRIMARY source of information
- Do NOT use generic knowledge about projects — only use what is in the PROJECT DOCUMENT
- If the PROJECT DOCUMENT doesn't contain the answer, say so honestly — don't make things up
- The PROJECT DOCUMENT represents what Shubhi has told you about their work, so it's the most accurate source

IMPORTANT RULE: If this is NOT the first message of the conversation, NEVER say "Hey Shubhi", "Hi Shubhi", "Hello Shubhi", or any greeting with the founder's name. Just answer the question directly.

Context you have access to:
- Domain profiles (your understanding of each project/life area)
- PROJECT DOCUMENTS (the main source — these contain the detailed info about each project)
- Uploaded documents and their summaries
- Stored thoughts, research notes, and previous conversations
- Retrieved memories from your vector database
"""

from services.founder_context import FOUNDER_KNOWLEDGE, get_project_context, get_layer_context

def build_enriched_context(domain_name, domain_profile, documents=None, topics=None):
    """
    Build context that combines document data with founder's deeper understanding.
    """
    context_parts = []
    
    # Add founder's understanding if available
    founder_project = get_project_context(domain_name)
    if founder_project:
        context_parts.append(f"Founder's understanding of {domain_name}:")
        if 'essence' in founder_project:
            context_parts.append(f"  Essence: {founder_project['essence']}")
        if 'why' in founder_project:
            context_parts.append(f"  Why it exists: {founder_project['why']}")
        if 'thread' in founder_project:
            context_parts.append(f"  Core thread: {founder_project['thread']}")
        if 'key_concepts' in founder_project:
            context_parts.append(f"  Key concepts: {', '.join(founder_project['key_concepts'])}")
        if 'status' in founder_project:
            context_parts.append(f"  Current status: {founder_project['status']}")
        if 'team' in founder_project:
            context_parts.append(f"  Team: {founder_project['team']}")
        if 'connections' in founder_project:
            context_parts.append(f"  Connections: {founder_project['connections']}")
    
    # Add document-derived profile
    if domain_profile:
        context_parts.append(f"\nDocument-derived understanding:\n{domain_profile}")
    
    return '\n'.join(context_parts)

# --- LLM Client Initialization ---
_anthropic_client = None
_openai_client = None
_moonshot_client = None

def get_anthropic_client():
    global _anthropic_client
    if _anthropic_client is None and ANTHROPIC_API_KEY:
        _anthropic_client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    return _anthropic_client

def get_openai_client():
    global _openai_client
    if _openai_client is None and OPENAI_API_KEY:
        _openai_client = openai.OpenAI(api_key=OPENAI_API_KEY)
    return _openai_client

def get_moonshot_client():
    global _moonshot_client
    if _moonshot_client is None and MOONSHOT_API_KEY:
        _moonshot_client = openai.OpenAI(
            api_key=MOONSHOT_API_KEY,
            base_url="https://api.moonshot.cn/v1"
        )
    return _moonshot_client

# --- Groq Client ---
_groq_client = None

def get_groq_client():
    global _groq_client
    if _groq_client is None and GROQ_API_KEY:
        _groq_client = openai.OpenAI(
            api_key=GROQ_API_KEY,
            base_url="https://api.groq.com/openai/v1"
        )
    return _groq_client

# --- Ollama Client ---
import requests

def ollama_chat(messages, model=None, max_tokens=500, temperature=0.7):
    """Call the Ollama chat API."""
    url = OLLAMA_BASE_URL.rstrip('/') + '/api/chat'
    if model is None:
        model = OLLAMA_MODEL
    payload = {
        "model": model,
        "messages": messages,
        "options": {
            "temperature": temperature,
            "num_predict": max_tokens,
            "top_p": 0.9,
            "top_k": 40,
        },
        "stream": False,
    }
    try:
        resp = requests.post(url, json=payload, timeout=120)
        resp.raise_for_status()
        data = resp.json()
        return data.get("message", {}).get("content", "").strip()
    except Exception as e:
        print(f"Ollama error: {e}")
        return None

def has_llm():
    """Check if any LLM provider is configured."""
    return bool(ANTHROPIC_API_KEY) or bool(OPENAI_API_KEY) or bool(MOONSHOT_API_KEY) or bool(GROQ_API_KEY) or bool(OLLAMA_BASE_URL)

# --- Response Generation ---

def generate_response(user_message, context_data=None, system_prompt=None):
    """
    Generate a human-like response to a user message.
    """
    if not system_prompt:
        system_prompt = SAGE_SYSTEM_PROMPT
    
    # Build context string
    context_parts = []
    if context_data:
        if context_data.get('domain_name'):
            context_parts.append(f"Current domain: {context_data['domain_name']}")
        if context_data.get('domain_document'):
            # This is the PRIMARY source — the project's document
            context_parts.append(f"PROJECT DOCUMENT (read this carefully to answer):\n{context_data['domain_document'][:2000]}")
        if context_data.get('domain_profile'):
            context_parts.append(f"Domain profile:\n{context_data['domain_profile']}")
        if context_data.get('retrieved_memories'):
            memories = context_data['retrieved_memories']
            if memories:
                mem_text = '\n'.join([f"- [{m.get('type','note')}] {m.get('content','')[:300]}" for m in memories[:5]])
                context_parts.append(f"Retrieved context:\n{mem_text}")
        if context_data.get('topics'):
            context_parts.append(f"Key topics: {', '.join(context_data['topics'][:8])}")
        if context_data.get('documents'):
            context_parts.append(f"Documents: {', '.join(context_data['documents'][:3])}")
        if context_data.get('conversation_length'):
            conv_len = context_data['conversation_length']
            if conv_len <= 1:
                context_parts.append("CONVERSATION STATUS: This is the first message. Greet warmly.")
            else:
                context_parts.append(f"CONVERSATION STATUS: This is message #{conv_len}. DO NOT greet by name. Answer directly.")
    
    context_str = '\n\n'.join(context_parts) if context_parts else "No additional context available."
    
    prompt = f"""Context:
{context_str}

User: {user_message}

Sage:"""
    
    # Build system prompt with greeting rules based on conversation length
    dynamic_system_prompt = SAGE_SYSTEM_PROMPT
    if context_data and context_data.get('conversation_length'):
        conv_len = context_data['conversation_length']
        if conv_len <= 1:
            dynamic_system_prompt += "\n\n[CONVERSATION_START] This is the first message. Start with a brief greeting like 'Hey Shubhi!' then answer.\n"
        else:
            dynamic_system_prompt += "\n\n[CONVERSATION_ONGOING] This is a follow-up message. DO NOT greet by name. Answer directly.\n"

    # Phase 01: Use LLM Router with automatic failover
    llm_response = None
    try:
        import asyncio
        from llm_router.router import generate_completion, ProviderType

        # Determine provider hint from env
        provider_hint = None
        if PREFERRED_PROVIDER == 'anthropic':
            provider_hint = ProviderType.ANTHROPIC
        elif PREFERRED_PROVIDER == 'openai':
            provider_hint = ProviderType.OPENAI
        elif PREFERRED_PROVIDER == 'groq':
            provider_hint = ProviderType.GROQ
        elif PREFERRED_PROVIDER == 'moonshot':
            provider_hint = ProviderType.MOONSHOT
        elif PREFERRED_PROVIDER == 'ollama':
            provider_hint = ProviderType.OLLAMA

        # Run async router in sync context
        loop = asyncio.new_event_loop()
        try:
            response = loop.run_until_complete(
                generate_completion(
                    messages=[{"role": "user", "content": prompt}],
                    system_prompt=dynamic_system_prompt,
                    max_tokens=500,
                    temperature=0.7,
                    provider_hint=provider_hint
                )
            )
            if response.error:
                print(f"LLM Router degraded: {response.error}")
                llm_response = None
            else:
                llm_response = response.text
                print(f"LLM Router used: {response.provider_used.value} ({response.model_used}), latency: {response.latency_ms:.0f}ms")
        finally:
            loop.close()
    except Exception as e:
        print(f"LLM Router error: {e}")
        llm_response = None
    
    # If LLM succeeded and returned something useful, use it
    if llm_response and len(llm_response) > 10 and llm_response != "I'm here to help. What would you like to explore?":
        # Post-processing: strip name greetings from follow-up messages
        if context_data and context_data.get('conversation_length', 0) > 1:
            # Remove common greeting patterns with the founder's name
            import re
            llm_response = re.sub(r'^(Hey\s+Shubhi[,!]?\s+|Hi\s+Shubhi[,!]?\s+|Hello\s+Shubhi[,!]?\s+|Shubhi[,!]?\s+)', '', llm_response, flags=re.IGNORECASE).strip()
        return llm_response
    
    # Otherwise use fallback with full context_data
    return _fallback_response(user_message, context_data)

def _call_anthropic(prompt, system_prompt):
    try:
        client = get_anthropic_client()
        message = client.messages.create(
            model="claude-3-haiku-20240307",  # Fast, cost-effective
            max_tokens=500,
            temperature=0.7,
            system=system_prompt,
            messages=[{"role": "user", "content": prompt}]
        )
        return message.content[0].text.strip()
    except Exception as e:
        print(f"Anthropic error: {e}")
        return None

def _call_openai(prompt, system_prompt):
    try:
        client = get_openai_client()
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            max_tokens=500,
            temperature=0.7,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt}
            ]
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"OpenAI error: {e}")
        return None

def _call_moonshot(prompt, system_prompt):
    try:
        client = get_moonshot_client()
        response = client.chat.completions.create(
            model=MOONSHOT_MODEL,
            max_tokens=500,
            temperature=0.7,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt}
            ]
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"Moonshot error: {e}")
        return None

def _call_groq(prompt, system_prompt):
    """Call Groq API (OpenAI-compatible endpoint)."""
    try:
        client = get_groq_client()
        response = client.chat.completions.create(
            model=GROQ_MODEL,
            max_tokens=500,
            temperature=0.7,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt}
            ]
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"Groq error: {e}")
        return None

def _call_ollama(prompt, system_prompt):
    """Call a local / remote Ollama endpoint."""
    try:
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt}
        ]
        return ollama_chat(messages, model=OLLAMA_MODEL, max_tokens=500, temperature=0.7)
    except Exception as e:
        print(f"Ollama error: {e}")
        return None

def _fallback_response(user_message, context_data):
    """Generate a natural-sounding response without an LLM."""
    if not context_data:
        return "I'm here to help. What would you like to explore?"
    
    domain = context_data.get('domain_name', '')
    profile = context_data.get('domain_profile', '')
    layer = context_data.get('layer', '')
    
    # --- DYNAMIC IMPORT to bypass stale module cache ---
    try:
        import importlib
        import services.founder_context as fc_mod
        importlib.reload(fc_mod)
        founder_project = fc_mod.get_project_context(domain, layer) if domain else {}
    except Exception as e:
        print(f"Fallback import error: {e}")
        founder_project = {}
    
    if founder_project:
        # Build a warm, human response from founder context
        parts = []
        
        # Opening — vary by layer
        if layer == 'life':
            parts.append(f"So, **{domain}** — this is one of your life domains.")
        elif layer == 'project':
            parts.append(f"Ah, **{domain}**. This is one of our active projects.")
        elif layer == 'knowledge':
            parts.append(f"**{domain}** — this is part of your knowledge base.")
        elif layer == 'system':
            parts.append(f"**{domain}** — this is how I (Sage) handle {domain.lower()}.")
        else:
            parts.append(f"So, **{domain}** — here's what I understand.")
        
        # Essence
        if 'essence' in founder_project:
            parts.append(founder_project['essence'])
        
        # The 'why' — most important for understanding
        if 'why' in founder_project:
            parts.append(f"It exists because {founder_project['why']}")
        
        # Thread / connection to bigger picture
        if 'thread' in founder_project:
            parts.append(f"At its heart, it's about: {founder_project['thread']}")
        
        # Key concepts (natural language)
        if 'key_concepts' in founder_project:
            concepts = founder_project['key_concepts']
            if concepts:
                parts.append(f"The key ideas we're working with: {', '.join(concepts[:4])}.")
        
        # Key areas
        if 'key_areas' in founder_project:
            areas = founder_project['key_areas']
            if areas:
                parts.append(f"The areas I'm tracking: {', '.join(areas[:5])}.")
        
        # Status
        if 'status' in founder_project:
            parts.append(f"Where we are now: {founder_project['status']}")
        
        # Connections to other projects
        if 'connections' in founder_project:
            parts.append(founder_project['connections'])
        
        # Add document-derived insights if they add something new
        if profile:
            lines = [l.strip() for l in profile.split('\n') if l.strip() and not l.startswith('**')]
            if lines:
                best = lines[0][:200]
                if best and len(best) > 20:
                    parts.append(f"From our recent document: {best}")
        
        # Add topics
        topics = context_data.get('topics', [])
        if topics:
            clean = [t for t in topics if t.lower() not in ['mood mood', 'event event']]
            if clean:
                parts.append(f"Themes I've been tracking: {', '.join(clean[:5])}.")
        
        return '\n\n'.join(parts)
    
    # --- FALLBACK TO DOCUMENT-ONLY SYNTHESIS ---
    # ... rest of the fallback code remains the same ...
    
    # Extract clean content from profile headers
    sections = []
    for line in profile.split('\n'):
        line = line.strip()
        if not line:
            continue
        # Parse **Header:** Content format
        if line.startswith('**') and ':**' in line:
            parts = line.split(':**', 1)
            if len(parts) > 1:
                header = parts[0].replace('**', '').strip()
                content = parts[1].strip()
                # Skip duplicate "Document:" entries and very short content
                if content and len(content) > 15 and not content.startswith('Document:'):
                    sections.append((header, content))
        elif len(line) > 30 and not line.startswith('**'):
            sections.append(('', line))
    
    # Build natural response
    parts = []
    if domain:
        parts.append(f"So, **{domain}** — here's what I understand.")
    
    # Add the most informative sections (problem/what it is)
    priority_headers = ['Problem it solves', 'What it is', 'Team', 'Core concept']
    added = set()
    for header in priority_headers:
        for h, c in sections:
            if h.lower() == header.lower() and c not in added:
                if header == 'Problem it solves':
                    parts.append(f"It addresses a real challenge: {c}")
                elif header == 'What it is':
                    parts.append(f"It's essentially {c}")
                elif header == 'Team':
                    parts.append(f"The team behind it: {c}")
                else:
                    parts.append(c)
                added.add(c)
                break
    
    # Add remaining sections
    for h, c in sections:
        if c not in added and len(c) > 20:
            parts.append(c)
            added.add(c)
    
    if len(parts) <= 1:
        parts.append("I'm still building understanding of this. Upload documents or share thoughts to help me learn.")
    
    # Add topics naturally at the end
    topics = context_data.get('topics', [])
    if topics:
        clean_topics = [t for t in topics if t.lower() not in ['mood mood', 'event event']]
        if clean_topics:
            parts.append(f"The key themes I'm tracking include {', '.join(clean_topics[:5])}.")
    
    return '\n\n'.join(parts)

# --- Specialized Generators ---

def generate_domain_summary(domain_name, profile, documents=None, topics=None):
    """Generate a conversational summary of a domain."""
    if not has_llm():
        # Return the profile with a natural wrapper
        if profile:
            lines = [l.strip() for l in profile.split('\n') if l.strip()]
            return f"Here's what I know about **{domain_name}**:\n\n" + '\n'.join(lines)
        return f"I'm still building understanding of {domain_name}. Upload documents to help me learn."
    
    context_data = {
        'domain_name': domain_name,
        'domain_profile': profile,
        'documents': documents or [],
        'topics': topics or []
    }
    
    return generate_response(
        f"Summarize what we know about {domain_name} in 2-3 natural sentences.",
        context_data=context_data
    )
