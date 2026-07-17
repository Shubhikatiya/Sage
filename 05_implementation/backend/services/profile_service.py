"""
Domain Profile Synthesis Service

Builds and maintains a synthesized understanding of each life domain/project
by combining documents, topics, and stored thoughts into a coherent profile.
"""

import re

NOISE_WORDS = {'page', 'table', 'summary', 'document', 'overview', 'appendix',
               'figure', 'chart', 'slide', 'section', 'introduction'}
STOP_WORDS = {'the', 'and', 'for', 'are', 'with', 'they', 'this', 'that',
                'have', 'from', 'been', 'were', 'said', 'each', 'which'}

def clean_topic_name(name):
    """Remove duplicate words and clean topic names."""
    words = name.lower().split()
    seen = set()
    cleaned = []
    for w in words:
        if w not in seen and w not in STOP_WORDS and len(w) > 2:
            seen.add(w)
            cleaned.append(w)
    return ' '.join(cleaned).title() if cleaned else name

def is_valid_topic(name):
    """Filter out noisy extracted topics."""
    lower = name.lower()
    words = lower.split()
    # Skip if same word repeated (e.g. "Mood Mood")
    if len(words) >= 2 and words[0] == words[1]:
        return False
    # Skip if mostly noise words
    if any(w in NOISE_WORDS for w in words):
        return False
    # Skip very short
    if len(name) < 4:
        return False
    return True

def extract_clean_problem(text):
    """Extract problem statement from pitch deck / document templates."""
    # Look for "Problem Statement" section
    match = re.search(r'(?i)problem\s*statement\s*:?\s*(.+?)(?:\n{2,}|\n#|\n---|$)', text, re.DOTALL)
    if match:
        problem = match.group(1).strip()
        # Clean template artifacts
        problem = re.sub(r'\?\s*Who\s*[!?]', '', problem)
        problem = re.sub(r'\n+', ' ', problem)
        problem = problem.strip()
        if len(problem) > 20:
            return problem[:400]
    return None

def extract_team(text):
    """Extract team name from document."""
    match = re.search(r'(?i)team\s*name\s*:?\s*(.+?)(?:\n|$)', text)
    if match:
        return match.group(1).strip()
    return None

def synthesize_domain_profile(domain_name, documents, topics, thoughts):
    """
    Build a structured profile of a domain from its stored content.
    Prioritizes clean summaries over raw document text.
    """
    # Gather clean text sources (prioritize research notes, then docs)
    clean_text_parts = []
    raw_text = ""
    
    for doc in documents:
        # Prefer research note summaries if available
        summary = doc.get('summary', '')
        if summary and len(summary) > 50:
            clean_text_parts.append(summary)
        
        content = doc.get('content', '') or ''
        if content:
            raw_text += content + "\n\n"
    
    # Also add thought content
    for thought in thoughts:
        t_content = thought.get('content', '')
        if t_content and len(t_content) > 10:
            clean_text_parts.append(t_content)
    
    # Use clean text as primary source, raw as backup
    all_text = "\n\n".join(clean_text_parts) if clean_text_parts else raw_text
    all_text = all_text[:10000]
    
    # Extract structured info
    problem = extract_clean_problem(all_text) or extract_clean_problem(raw_text)
    team = extract_team(raw_text)
    
    # Extract key sentences for identity
    sentences = [s.strip() for s in re.split(r'[.!?]\s+', all_text) 
                 if 20 < len(s.strip()) < 300]
    
    # Build profile sections
    profile_parts = []
    
    # Section 1: What is it? (best identity sentence or first meaningful sentence)
    identity_sentences = [s for s in sentences if any(kw in s.lower() for kw in 
        ['is a', 'is an', 'helps', 'enables', 'provides', 'framework', 'platform', 'system'])]
    if identity_sentences:
        profile_parts.append(f"**What it is:** {identity_sentences[0]}.")
    
    # Section 2: Problem Statement (extracted cleanly)
    if problem:
        profile_parts.append(f"**Problem it solves:** {problem}")
    
    # Section 3: Team
    if team:
        profile_parts.append(f"**Team:** {team}")
    
    # Section 4: Key Components / Topics (cleaned)
    if topics:
        # Filter and deduplicate topics
        seen_topics = set()
        clean_topics = []
        for t in topics:
            name = t['name']
            if is_valid_topic(name):
                cleaned = clean_topic_name(name)
                if cleaned.lower() not in seen_topics:
                    seen_topics.add(cleaned.lower())
                    clean_topics.append(cleaned)
        if clean_topics:
            profile_parts.append(f"**Key themes:** {', '.join(clean_topics[:6])}.")
    
    # Section 5: Recent Activity
    doc_names = []
    seen_names = set()
    for d in documents[-5:]:
        fname = d.get('filename', '')
        if fname and fname not in seen_names:
            seen_names.add(fname)
            # Clean up "Document: " prefix if present
            fname = fname.replace('Document: ', '')
            doc_names.append(fname)
    if doc_names:
        profile_parts.append(f"**Recent uploads:** {', '.join(doc_names[:3])}.")
    
    # Section 6: Core Insight (best sentence mentioning domain name)
    core_sentences = [s for s in sentences if domain_name.lower() in s.lower() and len(s) > 30]
    if core_sentences:
        best = max(core_sentences, key=lambda s: len(s))
        profile_parts.append(f"**Core concept:** {best}.")
    
    return '\n\n'.join(profile_parts) if profile_parts else f"No synthesized understanding yet for {domain_name}. Upload documents to build context."

def update_domain_profile(db, domain_id):
    """
    Rebuild the profile for a domain from all its content.
    Call this after document uploads or significant changes.
    """
    import crud, models
    domain = crud.get_life_domain(db, domain_id)
    if not domain:
        return None
    
    # Gather all content for this domain
    documents = crud.get_documents(db, life_domain_id=domain_id)
    notes = crud.get_research_notes(db, life_domain_id=domain_id)
    thoughts = crud.get_thoughts(db, life_domain_id=domain_id)
    topics = crud.get_topics(db, life_domain_id=domain_id)
    
    # Convert to dicts for the synthesizer
    # For documents, include the research note summary if available
    doc_dicts = []
    for d in documents:
        # Find associated research note
        note_summary = ""
        for n in notes:
            if hasattr(n, 'title') and d.filename in str(n.title):
                note_summary = n.content[:800] if hasattr(n, 'content') else ""
                break
        
        doc_dicts.append({
            'content': d.content,
            'filename': d.filename,
            'summary': note_summary
        })
    
    # Also add standalone notes
    for n in notes:
        # Only add if not already covered by a document
        doc_dicts.append({
            'content': n.content if hasattr(n, 'content') else '',
            'filename': n.title if hasattr(n, 'title') else 'Research Note',
            'summary': n.content[:500] if hasattr(n, 'content') else ''
        })
    
    topic_dicts = [{'name': t.name, 'frequency': t.frequency} for t in topics]
    thought_dicts = [{'content': t.content} for t in thoughts]
    
    profile_text = synthesize_domain_profile(
        domain.name,
        doc_dicts,
        topic_dicts,
        thought_dicts
    )
    
    # Save to domain
    crud.update_life_domain(db, domain_id, {'profile': profile_text})
    
    return profile_text
