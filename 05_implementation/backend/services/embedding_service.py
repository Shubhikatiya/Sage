from sentence_transformers import SentenceTransformer
import chromadb
import os

# Initialize embedding model
model = SentenceTransformer('all-MiniLM-L6-v2')

# Initialize ChromaDB with a path tied to the database
import os
_db_name = os.path.basename(os.environ.get('DATABASE_URL', 'sage_v3.db')).replace('.db', '')
chroma_path = f'./chroma_db_{_db_name}'
chroma_client = chromadb.PersistentClient(path=chroma_path)

print(f"Vector store: {chroma_path}")

def get_embedding(text):
    embedding = model.encode(text)
    return embedding.tolist()

def chunk_text(text, chunk_size=512, overlap=50):
    words = text.split()
    chunks = []
    for i in range(0, len(words), chunk_size - overlap):
        chunk = ' '.join(words[i:i + chunk_size])
        if chunk:
            chunks.append(chunk)
    return chunks

def store_embedding(collection_name, id, text, metadata=None):
    collection = chroma_client.get_or_create_collection(name=collection_name)
    embedding = get_embedding(text)
    # Clean metadata - ChromaDB cannot handle None values
    clean_metadata = {}
    if metadata:
        for key, value in metadata.items():
            if value is not None:
                clean_metadata[key] = value
    collection.add(
        ids=[id],
        embeddings=[embedding],
        documents=[text],
        metadatas=[clean_metadata]
    )
    return True

def query_embeddings(collection_name, query_text, n_results=5):
    collection = chroma_client.get_or_create_collection(name=collection_name)
    query_embedding = get_embedding(query_text)
    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=n_results
    )
    return results
