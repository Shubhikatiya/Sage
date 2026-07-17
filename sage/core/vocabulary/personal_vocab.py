"""
Sage Personal Vocabulary (SPV)
A structured ontology for personal knowledge graph construction.

Adapted from Schema.org concepts but focused on life, work, and relationships
rather than web content. Provides a shared semantic vocabulary for the
multi-agent extraction pipeline.
"""
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from enum import Enum
import json


class VocabTermType(str, Enum):
    """The 6 top-level term categories in the personal vocabulary."""
    ENTITY = "entity"           # People, organizations, projects, products
    PROPERTY = "property"       # Attributes that describe entities
    ACTION = "action"           # Activities, tasks, events
    RELATIONSHIP = "relationship"  # How entities connect
    LAYER = "layer"             # Contextual layers (life, project, etc.)
    STATE = "state"             # Emotional, mental, or situational states


@dataclass
class VocabTerm:
    """
    A single term in the personal vocabulary.
    Equivalent to a Schema.org type or property but for personal context.
    """
    uri: str                      # Unique identifier: spv:Person, spv:worksOn
    term_type: VocabTermType
    label: str                    # Human-readable name
    description: str              # What this term means
    synonyms: List[str] = field(default_factory=list)
    parent_terms: List[str] = field(default_factory=list)  # URIs of broader terms
    properties: List[str] = field(default_factory=list)     # Applicable properties for ENTITY types
    domain: Optional[str] = None  # For PROPERTY: which entity types this applies to
    range: Optional[str] = None   # For PROPERTY: expected value type
    examples: List[str] = field(default_factory=list)
    confidence_weight: float = 1.0  # How strongly this term should be weighted in matching

    def to_subgraph_text(self) -> str:
        """
        Convert this term into a rich text representation for embedding.
        This creates the subgraph that gets vectorized for retrieval.
        """
        parts = [
            f"Term: {self.label}",
            f"Type: {self.term_type.value}",
            f"URI: {self.uri}",
            f"Description: {self.description}",
        ]
        if self.synonyms:
            parts.append(f"Also known as: {', '.join(self.synonyms)}")
        if self.parent_terms:
            parts.append(f"Broader concepts: {', '.join(self.parent_terms)}")
        if self.properties:
            parts.append(f"Has properties: {', '.join(self.properties)}")
        if self.examples:
            parts.append(f"Examples: {'; '.join(self.examples)}")
        return "\n".join(parts)


# ───────────────────────────────────────────────────────────────
# CORE VOCABULARY DEFINITIONS
# ───────────────────────────────────────────────────────────────

CORE_VOCABULARY: List[VocabTerm] = [
    # ─── ENTITY TYPES ───
    VocabTerm(
        uri="spv:Person",
        term_type=VocabTermType.ENTITY,
        label="Person",
        description="A human being, including the user, family members, friends, colleagues, or public figures.",
        synonyms=["individual", "human", "contact", "friend", "colleague", "family member"],
        properties=["spv:name", "spv:role", "spv:email", "spv:phone", "spv:worksOn", "spv:knows", "spv:hasSkill"],
        examples=["Shubhi Katiyar", "Elon Musk", "my mother", "the team lead"],
        confidence_weight=1.2
    ),
    VocabTerm(
        uri="spv:Organization",
        term_type=VocabTermType.ENTITY,
        label="Organization",
        description="A group of people organized for a purpose: companies, nonprofits, teams, schools, communities.",
        synonyms=["company", "business", "nonprofit", "team", "group", "institution", "startup"],
        properties=["spv:name", "spv:foundedBy", "spv:hasMember", "spv:location"],
        examples=["Navgunjara", "Google", "my university", "the marketing team"],
        confidence_weight=1.1
    ),
    VocabTerm(
        uri="spv:Project",
        term_type=VocabTermType.ENTITY,
        label="Project",
        description="A planned undertaking with a goal, timeline, and deliverables.",
        synonyms=["initiative", "undertaking", "endeavor", "campaign", "build", "product"],
        properties=["spv:name", "spv:status", "spv:deadline", "spv:hasParticipant", "spv:goal"],
        examples=["Sage", "ReRoot", "website redesign", "Q4 marketing campaign"],
        confidence_weight=1.2
    ),
    VocabTerm(
        uri="spv:Concept",
        term_type=VocabTermType.ENTITY,
        label="Concept",
        description="An abstract idea, framework, methodology, or domain-specific knowledge.",
        synonyms=["idea", "framework", "theory", "method", "approach", "principle", "strategy"],
        properties=["spv:name", "spv:description", "spv:relatedTo"],
        examples=["knowledge graph", "machine learning", "agile methodology", "stoicism"],
        confidence_weight=1.0
    ),
    VocabTerm(
        uri="spv:Resource",
        term_type=VocabTermType.ENTITY,
        label="Resource",
        description="A document, tool, link, book, article, or any reference material.",
        synonyms=["document", "tool", "article", "book", "link", "reference", "material"],
        properties=["spv:title", "spv:url", "spv:author", "spv:topic"],
        examples=["a PDF report", "a Notion page", "a YouTube video", "a research paper"],
        confidence_weight=0.9
    ),
    VocabTerm(
        uri="spv:Event",
        term_type=VocabTermType.ENTITY,
        label="Event",
        description="A specific occurrence in time: meetings, deadlines, milestones, trips, appointments.",
        synonyms=["meeting", "appointment", "deadline", "milestone", "trip", "conference", "launch"],
        properties=["spv:name", "spv:startDate", "spv:endDate", "spv:location", "spv:hasParticipant"],
        examples=["project kickoff", "dentist appointment", "product launch", "team offsite"],
        confidence_weight=1.0
    ),
    VocabTerm(
        uri="spv:Goal",
        term_type=VocabTermType.ENTITY,
        label="Goal",
        description="A desired outcome or objective the user wants to achieve.",
        synonyms=["objective", "target", "aim", "ambition", "intention", "resolution"],
        properties=["spv:name", "spv:status", "spv:deadline", "spv:progress"],
        examples=["learn Spanish by December", "launch Sage v1", "get fit", "save $10,000"],
        confidence_weight=1.1
    ),
    VocabTerm(
        uri="spv:Decision",
        term_type=VocabTermType.ENTITY,
        label="Decision",
        description="A choice or judgment made by the user, often with reasoning and consequences.",
        synonyms=["choice", "judgment", "resolution", "conclusion", "verdict"],
        properties=["spv:name", "spv:context", "spv:consequence", "spv:madeAt"],
        examples=["chose Python over Node.js", "decided to pivot the product", "hired Alice"],
        confidence_weight=1.0
    ),

    # ─── PROPERTIES ───
    VocabTerm(
        uri="spv:name",
        term_type=VocabTermType.PROPERTY,
        label="Name",
        description="The human-readable identifier of an entity.",
        domain="spv:Entity",
        range="Text",
        examples=["Project Alpha", "Alice Johnson"],
    ),
    VocabTerm(
        uri="spv:role",
        term_type=VocabTermType.PROPERTY,
        label="Role",
        description="The function or position a person holds in a context.",
        domain="spv:Person",
        range="Text",
        synonyms=["title", "position", "function", "capacity"],
        examples=["CEO", "backend engineer", "mother", "advisor"],
    ),
    VocabTerm(
        uri="spv:worksOn",
        term_type=VocabTermType.PROPERTY,
        label="Works On",
        description="The project or task a person is actively contributing to.",
        domain="spv:Person",
        range="spv:Project",
        synonyms=["contributes to", "leads", "manages", "owns", "responsible for"],
        examples=["Shubhi works on Sage", "Alice leads the redesign project"],
    ),
    VocabTerm(
        uri="spv:knows",
        term_type=VocabTermType.PROPERTY,
        label="Knows",
        description="A person or concept the user is familiar with.",
        domain="spv:Person",
        range="spv:Person|spv:Concept",
        synonyms=["acquainted with", "familiar with", "connected to", "friend of"],
        examples=["knows Python", "knows Elon Musk", "knows agile methodology"],
    ),
    VocabTerm(
        uri="spv:hasSkill",
        term_type=VocabTermType.PROPERTY,
        label="Has Skill",
        description="A capability or expertise a person possesses.",
        domain="spv:Person",
        range="Text|spv:Concept",
        synonyms=["skilled in", "expert at", "proficient with", "capable of"],
        examples=["has skill in Python", "expert at negotiation", "proficient with Figma"],
    ),
    VocabTerm(
        uri="spv:status",
        term_type=VocabTermType.PROPERTY,
        label="Status",
        description="The current state of a project, task, or goal.",
        domain="spv:Project|spv:Goal|spv:Task",
        range="Text",
        synonyms=["state", "phase", "condition", "progress"],
        examples=["active", "completed", "on hold", "planning", "blocked"],
    ),
    VocabTerm(
        uri="spv:deadline",
        term_type=VocabTermType.PROPERTY,
        label="Deadline",
        description="The date or time by which something must be completed.",
        domain="spv:Project|spv:Goal|spv:Event|spv:Task",
        range="DateTime",
        synonyms=["due date", "target date", "cutoff", "end date"],
        examples=["deadline is March 15", "due by end of Q2", "launch date is next month"],
    ),
    VocabTerm(
        uri="spv:goal",
        term_type=VocabTermType.PROPERTY,
        label="Goal Statement",
        description="The desired outcome or objective of a project or action.",
        domain="spv:Project|spv:Action",
        range="Text",
        synonyms=["objective", "purpose", "aim", "intention"],
        examples=["goal is to reduce churn by 20%", "aim to ship by Friday"],
    ),

    # ─── ACTIONS ───
    VocabTerm(
        uri="spv:Action",
        term_type=VocabTermType.ACTION,
        label="Action",
        description="An activity performed by or with a person.",
        synonyms=["activity", "task", "operation", "step", "effort"],
        properties=["spv:actor", "spv:object", "spv:startDate", "spv:status"],
        examples=["writing a report", "attending a meeting", "deploying code"],
    ),
    VocabTerm(
        uri="spv:CreateAction",
        term_type=VocabTermType.ACTION,
        label="Create Action",
        description="The act of making or producing something new.",
        parent_terms=["spv:Action"],
        synonyms=["make", "build", "produce", "author", "design", "draft", "compose"],
        examples=["created a presentation", "built a prototype", "wrote an article"],
        confidence_weight=1.1
    ),
    VocabTerm(
        uri="spv:ReviewAction",
        term_type=VocabTermType.ACTION,
        label="Review Action",
        description="The act of examining or evaluating something.",
        parent_terms=["spv:Action"],
        synonyms=["review", "evaluate", "assess", "audit", "inspect", "check"],
        examples=["reviewed the contract", "evaluated the proposal", "checked the code"],
    ),
    VocabTerm(
        uri="spv:CommunicateAction",
        term_type=VocabTermType.ACTION,
        label="Communicate Action",
        description="The act of conveying information to another person or group.",
        parent_terms=["spv:Action"],
        synonyms=["communicate", "discuss", "explain", "present", "report", "inform", "notify"],
        examples=["discussed with the team", "presented to stakeholders", "sent an email"],
    ),

    # ─── RELATIONSHIPS ───
    VocabTerm(
        uri="spv:relatedTo",
        term_type=VocabTermType.RELATIONSHIP,
        label="Related To",
        description="A general semantic connection between two entities.",
        synonyms=["connected to", "associated with", "linked to", "relevant to"],
        examples=["Sage is related to Navgunjara", "Python is related to machine learning"],
    ),
    VocabTerm(
        uri="spv:partOf",
        term_type=VocabTermType.RELATIONSHIP,
        label="Part Of",
        description="An entity is a component or member of a larger entity.",
        synonyms=["component of", "member of", "within", "inside", "belongs to"],
        examples=["Sage is part of Navgunjara", "backend is part of the project"],
    ),
    VocabTerm(
        uri="spv:dependsOn",
        term_type=VocabTermType.RELATIONSHIP,
        label="Depends On",
        description="One entity requires another to function or proceed.",
        synonyms=["requires", "needs", "relies on", "contingent on", "blocked by"],
        examples=["frontend depends on API", "launch depends on approval"],
    ),
    VocabTerm(
        uri="spv:leadsTo",
        term_type=VocabTermType.RELATIONSHIP,
        label="Leads To",
        description="One event or action causes or results in another.",
        synonyms=["causes", "results in", "produces", "enables", "triggers"],
        examples=["meeting leads to decision", "prototype leads to funding"],
    ),
    VocabTerm(
        uri="spv:influencedBy",
        term_type=VocabTermType.RELATIONSHIP,
        label="Influenced By",
        description="An entity is shaped or affected by another.",
        synonyms=["shaped by", "affected by", "inspired by", "driven by"],
        examples=["design influenced by Dieter Rams", "decision influenced by market research"],
    ),

    # ─── LAYERS ───
    VocabTerm(
        uri="spv:LifeLayer",
        term_type=VocabTermType.LAYER,
        label="Life Layer",
        description="The broadest context: health, family, relationships, values, and long-term life trajectory.",
        synonyms=["life", "personal", "wellbeing", "family", "health", "values"],
        examples=["health goals", "family relationships", "life values", "personal growth"],
    ),
    VocabTerm(
        uri="spv:ProjectLayer",
        term_type=VocabTermType.LAYER,
        label="Project Layer",
        description="Active work: projects, tasks, deadlines, teams, and deliverables.",
        synonyms=["work", "project", "task", "career", "professional"],
        examples=["Sage development", "Q4 roadmap", "client project", "job search"],
    ),
    VocabTerm(
        uri="spv:KnowledgeLayer",
        term_type=VocabTermType.LAYER,
        label="Knowledge Layer",
        description="Concepts, learnings, insights, and accumulated understanding.",
        synonyms=["knowledge", "learning", "insight", "understanding", "wisdom"],
        examples=["AI concepts", "business strategy", "lessons learned"],
    ),

    # ─── STATES ───
    VocabTerm(
        uri="spv:EmotionalState",
        term_type=VocabTermType.STATE,
        label="Emotional State",
        description="The user's current emotional condition.",
        synonyms=["feeling", "mood", "emotion", "sentiment", "morale"],
        examples=["feeling stressed", "excited about launch", "anxious about deadline"],
    ),
    VocabTerm(
        uri="spv:MentalState",
        term_type=VocabTermType.STATE,
        label="Mental State",
        description="The user's cognitive condition: focus, clarity, energy, overwhelm.",
        synonyms=["mindset", "focus", "clarity", "energy", "burnout", "flow"],
        examples=["in deep focus", "mentally drained", "high energy", "brain fog"],
    ),
    VocabTerm(
        uri="spv:SituationalState",
        term_type=VocabTermType.STATE,
        label="Situational State",
        description="The user's current life situation or circumstances.",
        synonyms=["situation", "circumstance", "context", "condition", "phase"],
        examples=["between jobs", "transitioning teams", "relocating", "in crisis"],
    ),
]


def get_term_by_uri(uri: str) -> Optional[VocabTerm]:
    """Look up a vocabulary term by its URI."""
    for term in CORE_VOCABULARY:
        if term.uri == uri:
            return term
    return None


def get_terms_by_type(term_type: VocabTermType) -> List[VocabTerm]:
    """Get all terms of a specific type."""
    return [t for t in CORE_VOCABULARY if t.term_type == term_type]


def build_term_index() -> Dict[str, VocabTerm]:
    """Build a lookup index by URI."""
    return {t.uri: t for t in CORE_VOCABULARY}


def export_vocabulary_json() -> str:
    """Export the full vocabulary as JSON for embedding."""
    vocab_dict = []
    for term in CORE_VOCABULARY:
        vocab_dict.append({
            "uri": term.uri,
            "type": term.term_type.value,
            "label": term.label,
            "description": term.description,
            "synonyms": term.synonyms,
            "parent_terms": term.parent_terms,
            "properties": term.properties,
            "domain": term.domain,
            "range": term.range,
            "examples": term.examples,
            "confidence_weight": term.confidence_weight,
            "subgraph_text": term.to_subgraph_text(),
        })
    return json.dumps(vocab_dict, indent=2)


# Convenience exports
ALL_ENTITY_TERMS = get_terms_by_type(VocabTermType.ENTITY)
ALL_PROPERTY_TERMS = get_terms_by_type(VocabTermType.PROPERTY)
ALL_ACTION_TERMS = get_terms_by_type(VocabTermType.ACTION)
ALL_RELATIONSHIP_TERMS = get_terms_by_type(VocabTermType.RELATIONSHIP)
