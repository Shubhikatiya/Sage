"""
Backfill script: embed all existing KnowledgeNodes into the vector store.
Run once after deploying the semantic search feature.
"""
import sys
import os

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '05_implementation', 'backend'))

from database_v4 import SessionLocal
from models_v4 import KnowledgeNode
from services.knowledge_vector_store import sync_node


def backfill_knowledge_nodes():
    db = SessionLocal()
    try:
        # Initialize tables if they don't exist
        from database_v4 import init_db
        init_db()

        nodes = db.query(KnowledgeNode).filter(
            KnowledgeNode.is_archived == False
        ).all()

        print(f"Found {len(nodes)} knowledge nodes to embed.")
        synced = 0
        skipped = 0

        for node in nodes:
            # Skip nodes that shouldn't be embedded
            if node.source_type in {"extracted_entity", "asset_extraction"}:
                skipped += 1
                continue
            if not node.title or len(node.title.strip()) < 2:
                skipped += 1
                continue

            ok = sync_node(node)
            if ok:
                synced += 1
                if synced % 50 == 0:
                    print(f"  ... synced {synced} nodes")
            else:
                skipped += 1

        print(f"\nDone. Synced: {synced}, Skipped: {skipped}")
        print("Run this script once. Future nodes are auto-synced on creation.")
    finally:
        db.close()


if __name__ == "__main__":
    backfill_knowledge_nodes()
