from services.embedding_service import get_embedding
import numpy as np

def cosine_similarity(vec_a, vec_b):
    """Compute cosine similarity between two vectors."""
    a = np.array(vec_a)
    b = np.array(vec_b)
    return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))

def classify_document(text, domains, min_confidence=0.15):
    """
    Classify a document into the best matching life domain.
    
    Rules:
    - Finance (personal finance) = only when no project context found
    - Project finance = financial docs that mention a specific project name go to that project
    """
    if not text or not domains:
        return None
    
    doc_text = text[:2000].strip().lower()
    if not doc_text:
        return None
    
    doc_embedding = get_embedding(text[:2000].strip())
    
    # Project names that should trigger project-level finance classification
    project_names = ['sage', 'kaal', 'reroot', 'navgunjara', 're-root']
    found_projects = [p for p in project_names if p in doc_text]
    has_financial_content = any(word in doc_text for word in ['revenue', 'profit', 'expense', 'funding', 'budget', 'finance', 'cost', 'investment', 'annual report', 'quarterly'])
    
    best_match = None
    best_score = -1
    scores = []
    
    for domain in domains:
        # Handle both dict and SQLAlchemy object
        if isinstance(domain, dict):
            name = domain.get('name', '')
            desc = domain.get('description', '')
            domain_id = domain.get('id', '')
        else:
            name = getattr(domain, 'name', '')
            desc = getattr(domain, 'description', '')
            domain_id = getattr(domain, 'id', '')
        
        domain_text = f"{name}. {desc}"
        domain_embedding = get_embedding(domain_text)
        score = cosine_similarity(doc_embedding, domain_embedding)
        scores.append({'domain_id': domain_id, 'domain_name': name, 'score': score})
        
        if score > best_score:
            best_score = score
            best_match = {'id': domain_id, 'name': name}
    
    # --- PROJECT FINANCE RULE ---
    # If document has financial content AND mentions a project name,
    # override semantic match: prefer the project over Finance
    if has_financial_content and found_projects:
        for s in scores:
            # Check if this domain matches a found project name
            domain_name_lower = s['domain_name'].lower()
            for proj in found_projects:
                if proj in domain_name_lower:
                    best_match = {'id': s['domain_id'], 'name': s['domain_name']}
                    best_score = s['score']
                    break
    
    if best_match and best_score >= min_confidence:
        top_3 = sorted(scores, key=lambda x: x['score'], reverse=True)[:3]
        reasoning_parts = [f"Best match: {best_match['name']} (score: {best_score:.3f})"]
        if found_projects and has_financial_content:
            reasoning_parts.append(f"Detected project finance context: {', '.join(found_projects)}")
        for s in top_3[1:]:
            reasoning_parts.append(f"Also considered: {s['domain_name']} ({s['score']:.3f})")
        
        return {
            'domain_id': best_match['id'],
            'domain_name': best_match['name'],
            'confidence': best_score,
            'reasoning': '\n'.join(reasoning_parts),
            'all_scores': scores
        }
    
    return None
