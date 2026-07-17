import requests

BASE_URL = "http://127.0.0.1:8006"

DOMAINS = [
    {"name": "Self", "description": "Physical, mental, emotional, spiritual well-being"},
    {"name": "Career", "description": "Professional identity, skills, reputation"},
    {"name": "Sage", "description": "AI Chief of Staff product and mission"},
    {"name": "Kaal", "description": "Time philosophy and temporal intelligence project"},
    {"name": "Navgunjara Foundation", "description": "Ancient wisdom meets modern science initiative"},
    {"name": "ReRoot", "description": "Human flourishing and transformation platform"},
    {"name": "AI Research", "description": "General AI/ML exploration and experiments"},
    {"name": "Human Development Research", "description": "Psychology, neuroscience, growth"},
    {"name": "Technology Mastery", "description": "Tools, systems, technical skills"},
    {"name": "Entrepreneurship", "description": "Business building, ventures, investments"},
    {"name": "Writing", "description": "Articles, essays, books, content"},
    {"name": "Speaking", "description": "Talks, podcasts, workshops, teaching"},
    {"name": "Community", "description": "Networks, relationships, collaborations"},
    {"name": "Finance", "description": "Wealth, budgeting, financial planning"},
    {"name": "Research Library", "description": "Books, papers, notes, knowledge base"},
    {"name": "Experiments", "description": "Personal and professional experiments"},
    {"name": "Life Administration", "description": "Logistics, health, legal, daily ops"},
    {"name": "Long-term Dreams", "description": "Vision, legacy, 10+ year aspirations"},
]

SUBDOMAINS = {
    "Sage": [
        {"name": "Sage / Product", "description": "Product vision, features, roadmap"},
        {"name": "Sage / Engineering", "description": "Technical architecture, implementation"},
        {"name": "Sage / Research", "description": "AI research, memory systems, retrieval"},
        {"name": "Sage / Business", "description": "Strategy, monetization, go-to-market"},
        {"name": "Sage / Users", "description": "User research, feedback, community"},
    ]
}

def seed():
    print("Seeding life domains...")

    # Get existing domains first
    existing = set()
    try:
        resp = requests.get(f"{BASE_URL}/api/life-domains")
        if resp.status_code == 200:
            for d in resp.json():
                existing.add(d['name'])
    except:
        pass
    
    for domain in DOMAINS:
        if domain['name'] in existing:
            print(f"  Skipped (exists): {domain['name']}")
            continue
        
        resp = requests.post(f"{BASE_URL}/api/life-domains", json=domain)
        if resp.status_code == 200:
            created = resp.json()
            print(f"  Created: {created['name']}")
            existing.add(created['name'])
            
            # Create subdomains if any
            if created['name'] in SUBDOMAINS:
                for sub in SUBDOMAINS[created['name']]:
                    sub['parent_id'] = created['id']
                    sub_resp = requests.post(f"{BASE_URL}/api/life-domains", json=sub)
                    if sub_resp.status_code == 200:
                        print(f"    -> {sub['name']}")
        else:
            print(f"  Failed: {domain['name']} ({resp.status_code})")
    
    print("\nDone! Open http://localhost:8000/ to see your life domains.")

if __name__ == "__main__":
    seed()
