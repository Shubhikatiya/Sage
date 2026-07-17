from services.embedding_service import query_embeddings

def retrieve_memories(query, life_domain_id=None, n_results=5):
    results = query_embeddings(
        'memories',
        query,
        n_results=n_results
    )
    
    memories = []
    if results['ids']:
        for i, id_list in enumerate(results['ids']):
            for j, doc_id in enumerate(id_list):
                memories.append({
                    'id': doc_id,
                    'content': results['documents'][i][j] if results['documents'] else '',
                    'metadata': results['metadatas'][i][j] if results['metadatas'] else {},
                    'distance': results['distances'][i][j] if results['distances'] else 0
                })
    
    return memories
