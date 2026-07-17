import re
from collections import Counter
from services.embedding_service import get_embedding

def extract_topics(text, min_length=3, max_topics=15):
    """
    Extract key topics from document text.
    Returns list of topic dicts: {'name', 'frequency', 'context'}
    """
    if not text:
        return []
    
    # Clean text
    clean = text.lower()
    # Remove markdown table syntax
    clean = re.sub(r'\|[^\n]*\|', '', clean)
    clean = re.sub(r'[-=]{3,}', ' ', clean)
    
    # Extract headings as high-confidence topics
    headings = re.findall(r'^#{1,3}\s+(.+)$', text, re.MULTILINE)
    heading_topics = []
    for h in headings:
        h_clean = h.strip().strip(':').strip()
        if len(h_clean) >= min_length and len(h_clean) < 80:
            heading_topics.append(h_clean)
    
    # Extract capitalized phrases (likely named entities/topics)
    capitalized = re.findall(r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b', text)
    
    # Extract important bigrams and trigrams
    words = re.findall(r'\b[a-z]{3,}\b', clean)
    
    # Filter out stop words
    stop_words = {
        'the', 'and', 'for', 'are', 'but', 'not', 'you', 'all', 'can', 'had', 'her', 'was', 'one', 'our',
        'out', 'day', 'get', 'has', 'him', 'his', 'how', 'its', 'may', 'new', 'now', 'old', 'see', 'two',
        'who', 'boy', 'did', 'she', 'use', 'her', 'way', 'many', 'oil', 'sit', 'set', 'run', 'eat', 'far',
        'sea', 'eye', 'ago', 'off', 'too', 'any', 'say', 'man', 'try', 'ask', 'end', 'why', 'let', 'put',
        'say', 'she', 'try', 'way', 'own', 'say', 'too', 'old', 'tell', 'very', 'when', 'come', 'could',
        'would', 'should', 'there', 'their', 'them', 'these', 'those', 'than', 'then', 'that', 'this', 'with',
        'have', 'from', 'they', 'been', 'were', 'said', 'each', 'which', 'will', 'about', 'also', 'back',
        'after', 'first', 'well', 'year', 'work', 'only', 'over', 'think', 'where', 'being', 'every',
        'great', 'might', 'shall', 'still', 'those', 'under', 'while', 'without', 'another', 'around',
        'before', 'between', 'through', 'during', 'example', 'however', 'important', 'something',
        'document', 'summary', 'overview', 'content', 'section', 'page', 'table', 'file', 'text'
    }
    
    filtered = [w for w in words if w not in stop_words and len(w) >= min_length]
    
    # Count frequency
    word_counts = Counter(filtered)
    
    # Bigrams
    bigrams = []
    for i in range(len(filtered) - 1):
        bigrams.append(f"{filtered[i]} {filtered[i+1]}")
    bigram_counts = Counter(bigrams)
    
    # Combine heading topics with frequent bigrams
    topics = []
    
    # Add heading topics (highest priority)
    for h in heading_topics[:max_topics]:
        topics.append({
            'name': h.title(),
            'frequency': 1,
            'context': 'heading',
            'confidence': 0.9
        })
    
    # Add frequent bigrams that look like topics
    for bg, count in bigram_counts.most_common(30):
        if count >= 2 and len(bg) < 40:
            # Skip if too similar to existing
            is_duplicate = False
            bg_words = set(bg.split())
            for existing in topics:
                existing_words = set(existing['name'].lower().split())
                overlap = len(bg_words & existing_words) / max(len(bg_words), len(existing_words))
                if overlap > 0.5:
                    is_duplicate = True
                    existing['frequency'] += count
                    break
            if not is_duplicate and len(topics) < max_topics:
                topics.append({
                    'name': bg.title(),
                    'frequency': count,
                    'context': 'phrase',
                    'confidence': min(0.7, 0.3 + count * 0.05)
                })
    
    # Add single-word topics for high-frequency terms
    for word, count in word_counts.most_common(20):
        if count >= 3 and len(word) >= 4:
            is_duplicate = False
            for existing in topics:
                if word in existing['name'].lower():
                    is_duplicate = True
                    break
            if not is_duplicate and len(topics) < max_topics:
                topics.append({
                    'name': word.title(),
                    'frequency': count,
                    'context': 'term',
                    'confidence': min(0.6, 0.2 + count * 0.03)
                })
    
    # Sort by confidence descending
    topics.sort(key=lambda x: x['confidence'], reverse=True)
    
    return topics[:max_topics]

def deduplicate_topics(existing_topics, new_topics, similarity_threshold=0.7):
    """
    Merge new topics into existing, avoiding duplicates using simple word overlap.
    Returns list of merged topics.
    """
    result = list(existing_topics)
    
    for new_topic in new_topics:
        new_name = new_topic['name'].lower()
        new_words = set(new_name.split())
        
        is_duplicate = False
        for existing in result:
            existing_words = set(existing['name'].lower().split())
            overlap = len(new_words & existing_words) / max(len(new_words), len(existing_words)) if new_words or existing_words else 0
            
            if overlap >= similarity_threshold or new_name in existing['name'].lower() or existing['name'].lower() in new_name:
                is_duplicate = True
                existing['frequency'] = existing.get('frequency', 1) + new_topic.get('frequency', 1)
                break
        
        if not is_duplicate:
            result.append(new_topic)
    
    return result

def extract_document_topics(text, life_domain_id=None, source_id=None):
    """
    Full pipeline: extract topics from text and prepare for storage.
    """
    topics = extract_topics(text)
    
    for t in topics:
        t['life_domain_id'] = life_domain_id
        t['source_id'] = source_id
        t['source_type'] = 'document'
    
    return topics
