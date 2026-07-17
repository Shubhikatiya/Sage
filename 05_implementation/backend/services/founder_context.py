"""
Founder Context for Sage
This is the living memory of who the founder is and what their projects mean.
Used by the LLM and fallback synthesizer to generate human-like, context-aware responses.

Architecture: Four Layers
  - Life: Who the founder is (Self, Career, Finance, etc.)
  - Projects: What the founder is building (Sage, Kaal, ReRoot, Navgunjara)
  - Knowledge: What the founder is learning (AI, Human Development, Philosophy)
  - System: How Sage itself works (Memory, Tasks, Dashboard, etc.)
"""

FOUNDER_KNOWLEDGE = {
    "founder_name": "Shubhi Katiyar",
    "founder_principles": [
        "Builds structures before content (systems thinker)",
        "Oscillates between deep research and impulsive building",
        "Cares about human development, agency, and ancient wisdom meeting modern science",
        "Creates projects that are connected by a single thread of inquiry",
        "Values corrigibility over correctness",
    ],
    "layers": {
        "life": {
            "description": "Who the founder is — the human being behind the work",
            "domains": {
                "Self": {
                    "essence": "Identity, vision, health, habits, personal growth",
                    "why": "The foundation everything else builds on. Without clarity of self, all other work wobbles.",
                    "thread": "How do I become who I am capable of becoming?"
                },
                "Career": {
                    "essence": "Professional journey — not just jobs, but work that serves the thread",
                    "why": "Career is not separate from purpose. The founder seeks work that aligns with inquiry.",
                    "thread": "How do I build a career that serves my deeper questions?",
                    "status": "Active. Includes interview prep, resume work, applications."
                },
                "Entrepreneurship": {
                    "essence": "Business ideas, strategy, funding, incubators",
                    "why": "The founder wants to build sustainable systems that outlast individual effort.",
                    "thread": "How do we build organizations that serve human flourishing?"
                },
                "Finance": {
                    "essence": "Personal finance — NOT project finance (that belongs in Projects layer)",
                    "why": "Financial stability is infrastructure for everything else.",
                    "note": "If a document mentions 'Sage funding' or 'ReRoot budget', that belongs in the Projects layer, not here."
                },
                "Content Creation": {
                    "essence": "Strategy, platforms, scripts, calendar, brand",
                    "why": "The founder believes ideas must be shared to compound.",
                    "thread": "How do we share knowledge in ways that transform?"
                },
                "Community": {
                    "essence": "Mentors, collaborators, partners, network",
                    "why": "No one builds alone. The founder values relationships that challenge and support."
                },
                "Speaking": {
                    "essence": "Talks, workshops, presentations, conferences",
                    "why": "Direct human connection. The founder uses speaking to test ideas in real time."
                },
                "Writing": {
                    "essence": "Articles, blogs, books, documentation, newsletter",
                    "why": "Writing is thinking. The founder writes to clarify, not just to publish."
                },
                "Life Administration": {
                    "essence": "Documents, banking, insurance, legal, travel",
                    "why": "Boring but necessary. Sage handles this so the founder doesn't have to remember."
                },
                "Long-term Dreams": {
                    "essence": "5-year vision, 10-year vision, legacy",
                    "why": "The founder thinks in decades, not quarters. This keeps daily actions aligned."
                }
            }
        },
        "project": {
            "description": "What the founder is actively building",
            "domains": {
                "Sage": {
                    "essence": "AI Chief of Staff with infinite memory. Not a productivity app — it optimizes decision quality, not execution speed.",
                    "why": "Built because the founder keeps losing the thread across projects, months, and life phases. The real problem is context reconstruction cost — the tax of saying 'let me explain from the beginning'.",
                    "thread": "How do humans preserve understanding across time?",
                    "status": "Currently being built. MVP is chat + document memory + 'bring me back'.",
                    "sub_domains": ["Vision", "Architecture", "Roadmap", "Features", "Technical Design", "Research", "Product", "Users", "Documentation", "Development"]
                },
                "Kaal": {
                    "essence": "Temporal intelligence framework. Uses Jyotish (Vedic astrology) symbolic language to help people understand life transitions.",
                    "why": "People navigating major life transitions (career changes, quarter-life crises) blame themselves because they lack a framework for what they're experiencing. Kaal gives them that language.",
                    "thread": "How do people understand what is actually happening in their lives?",
                    "key_concepts": ["Life phases", "Jyotish symbolism", "Self-blame vs. phase intelligence", "Check-ins to insight to journal to clarity to action"],
                    "status": "Pitch deck exists. Concept proven. Needs development.",
                    "team": "Shubhi Katiyar"
                },
                "Navgunjara Foundation": {
                    "essence": "A Section 8 non-profit company. Ancient wisdom meets modern science.",
                    "why": "The founder believes traditional knowledge systems (Indian philosophy, Jyotish, yoga, Ayurveda) contain frameworks that modern psychology and self-help are only now rediscovering.",
                    "thread": "How do communities flourish when ancient wisdom and modern science work together?",
                    "status": "Registered as Section 8 company. Early stage.",
                    "note": "Navgunjara is the mythical beast from Indian mythology with parts of nine animals — symbolizing integration of many forms of knowledge."
                },
                "ReRoot": {
                    "essence": "Social enterprise about agency — helping people gain control over their own lives and decisions.",
                    "why": "The founder noticed that people don't fail because they lack talent. They fail because they lack agency — the belief that they can affect their own circumstances.",
                    "thread": "How do people gain agency?",
                    "status": "Explored fellowship applications, incubators, NGO partnerships. SIA rejection noted. Still alive as an idea.",
                    "connections": "ReRoot connects to agency, which connects to human development, which connects to Kaal, which connects to Sage. All one thread."
                },
                "Future Projects": {
                    "essence": "Ideas and concepts not yet started",
                    "why": "The founder constantly generates ideas. Sage captures them before they evaporate."
                }
            }
        },
        "knowledge": {
            "description": "What the founder is learning and researching — the second brain",
            "domains": {
                "AI": {
                    "essence": "Artificial Intelligence research and engineering",
                    "why": "The founder is an AI engineer who believes technology should help people understand themselves, not just automate tasks.",
                    "thread": "How can technology help people grow?",
                    "key_areas": ["LLMs", "Agents", "RAG", "MCP", "AI Engineering", "Research Papers"],
                    "note": "This is where AI research lives. Sage (the project) uses this knowledge but is distinct from it."
                },
                "Human Development": {
                    "essence": "Psychology, neuroscience, learning science, education",
                    "why": "The founder's life work circles back to human development. Every project ultimately serves this inquiry.",
                    "thread": "How do people become who they are capable of becoming?",
                    "key_areas": ["Psychology", "Neuroscience", "Learning Science", "Education", "Identity", "Decision Making"]
                },
                "Technology": {
                    "essence": "Software engineering and technical skills",
                    "key_areas": ["Python", "Backend", "Frontend", "Databases", "DevOps", "System Design"]
                },
                "Entrepreneurship": {
                    "essence": "Business theory — product, marketing, sales, operations, leadership",
                    "note": "This is knowledge ABOUT entrepreneurship. Active businesses live in the Projects layer."
                },
                "Philosophy": {
                    "essence": "Philosophical inquiry and frameworks",
                    "why": "The founder believes philosophy is not abstract — it is the operating system for living."
                },
                "Systems Thinking": {
                    "essence": "Complex systems and systems dynamics",
                    "why": "The founder sees connections everywhere. Systems thinking is their natural mode."
                },
                "Research Library": {
                    "essence": "Books, papers, videos, podcasts, references",
                    "why": "Knowledge must be organized to be useful. The Research Library is the raw material."
                },
                "Experiments": {
                    "essence": "Learning experiments, product experiments, failed ideas",
                    "why": "The founder values failed experiments as much as successes. They are data."
                }
            }
        },
        "system": {
            "description": "How Sage itself works — the infrastructure layer",
            "domains": {
                "Memory": {
                    "essence": "How Sage stores and retrieves information",
                    "types": ["Episodic (events)", "Semantic (facts)", "Project (context)", "Research (findings)", "Archive (dormant)"]
                },
                "Tasks": {
                    "essence": "Task management and tracking"
                },
                "Goals": {
                    "essence": "Goal setting and tracking"
                },
                "Decision Log": {
                    "essence": "Record of important decisions and their rationale"
                },
                "Knowledge Graph": {
                    "essence": "Connections between concepts, projects, and life domains"
                },
                "Dashboard": {
                    "essence": "Overview and status of everything"
                }
            }
        }
    },
    "recurring_inquiry": "Every project the founder builds is trying to answer the same underlying question: How do humans understand themselves, grow, and preserve that understanding across time?",
    "oscillation_pattern": "The founder oscillates between Mode A (research forever, perfect the philosophy) and Mode B (build immediately, act impulsively). Neither is wrong. Sage should recognize the rhythm.",
}


def get_project_context(project_name: str, layer: str = None) -> dict:
    """Get the founder's understanding of a specific project/domain."""
    # First try exact match in specified layer
    if layer and layer in FOUNDER_KNOWLEDGE["layers"]:
        layer_domains = FOUNDER_KNOWLEDGE["layers"][layer].get("domains", {})
        if project_name in layer_domains:
            return layer_domains[project_name]
        # Try case-insensitive
        for key, value in layer_domains.items():
            if key.lower() == project_name.lower():
                return value
    
    # Search across all layers
    for layer_key, layer_data in FOUNDER_KNOWLEDGE["layers"].items():
        domains = layer_data.get("domains", {})
        if project_name in domains:
            return domains[project_name]
        for key, value in domains.items():
            if key.lower() == project_name.lower():
                return value
    
    return {}


def get_layer_context(layer_name: str) -> dict:
    """Get context for an entire layer."""
    return FOUNDER_KNOWLEDGE["layers"].get(layer_name, {})


def get_all_domain_names() -> list:
    """Get all domain names across all layers."""
    names = []
    for layer_data in FOUNDER_KNOWLEDGE["layers"].values():
        names.extend(layer_data.get("domains", {}).keys())
    return names
