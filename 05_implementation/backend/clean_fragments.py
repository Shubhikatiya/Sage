import sqlite3
import re

def clean_fragments(db_path):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # First: archive all extracted_entity and asset_extraction nodes
    cursor.execute("""
        SELECT id, title, source_type FROM knowledge_nodes
        WHERE is_archived = 0
        AND source_type IN ('extracted_entity', 'asset_extraction')
    """)
    extracted = cursor.fetchall()
    
    # Second: find short/broken titles among remaining
    cursor.execute("""
        SELECT id, title, source_type FROM knowledge_nodes
        WHERE is_archived = 0
        AND LENGTH(title) < 5
    """)
    short = cursor.fetchall()
    
    # Third: find nodes with newline chars or punctuation artifacts
    cursor.execute("""
        SELECT id, title, source_type FROM knowledge_nodes
        WHERE is_archived = 0
        AND (title LIKE '%\n%' OR title LIKE '%,%' OR title LIKE '%.%')
    """)
    broken = cursor.fetchall()
    
    all_fragments = {}
    for nid, title, stype in extracted + short + broken:
        all_fragments[nid] = (title, stype)
    
    print(f"Found {len(all_fragments)} fragment nodes in {db_path}:")
    for nid, (title, stype) in list(all_fragments.items())[:20]:
        print(f"  - {title!r} ({stype})")
    if len(all_fragments) > 20:
        print(f"  ... and {len(all_fragments) - 20} more")
    
    # Archive them (soft delete)
    for nid in all_fragments:
        cursor.execute("""
            UPDATE knowledge_nodes
            SET is_archived = 1, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (nid,))
    
    conn.commit()
    print(f"\nArchived {len(all_fragments)} fragment nodes.")
    conn.close()

if __name__ == '__main__':
    clean_fragments('sage_v4.db')
    print("Done.")
