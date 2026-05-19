"""
models/ticket.py — Pydantic models for ticket creation, storage, and API responses.
"""

from pydantic import BaseModel, Field, field_validator
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum

# ─── Enums ────────────────────────────────────────────────────────────


class TicketStatus(str, Enum):
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    RESOLVED = "resolved"
    CLOSED = "closed"
    DUPLICATE = "duplicate"


class TicketPriority(str, Enum):
    LOW = "Low"
    MEDIUM = "Medium"
    HIGH = "High"
    CRITICAL = "Critical"


class TicketCategory(str, Enum):
    NETWORK = "Network"
    AUTH = "Auth"
    SOFTWARE = "Software"
    HARDWARE = "Hardware"
    ACCESS = "Access"
    BILLING = "Billing"
    EMAIL = "Email"
    SECURITY = "Security"
    SERVICE_REQUEST = "ServiceRequest"
    DATABASE = "Database"


class RoutingDecision(str, Enum):
    AUTO_RESOLVE = "AUTO_RESOLVE"
    SUGGEST_TO_AGENT = "SUGGEST_TO_AGENT"
    ESCALATE_TO_AGENT = "ESCALATE_TO_AGENT"
    ESCALATE_TO_HUMAN = "ESCALATE_TO_HUMAN"


class SentimentLabel(str, Enum):
    POSITIVE = "POSITIVE"
    NEUTRAL = "NEUTRAL"
    NEGATIVE = "NEGATIVE"


class AgentAction(str, Enum):
    APPROVED = "approved"
    EDITED = "edited"
    REJECTED = "rejected"
    ESCALATED = "escalated"


# ─── Nested schemas (used inside TicketDocument) ──────────────────────


class ConfidenceBreakdown(BaseModel):
    """Detailed decomposition of the composite confidence score."""

    model_prob_component: float = Field(ge=0.0, le=1.0)
    similarity_component: float = Field(ge=0.0, le=1.0)
    keyword_component: float = Field(ge=0.0, le=1.0)


class SimilarTicket(BaseModel):
    """A past resolved ticket retrieved from ChromaDB."""

    ticket_id: str
    summary: str
    solution: str
    similarity_score: float = Field(ge=0.0, le=1.0)
    resolution_time_hours: Optional[float] = None
    category: str


class LIMEFeature(BaseModel):
    """A single word and its importance weight from LIME."""

    word: str
    weight: float  # positive = supports, negative = opposes


class LIMEExplanation(BaseModel):
    """Full LIME explanation for a ticket classification."""

    predicted_class: str
    explanation_confidence: float
    top_positive_features: List[LIMEFeature]
    top_negative_features: List[LIMEFeature]


class ThreatAnalysis(BaseModel):
    """Output of the security threat detection pipeline."""

    threat_detected: bool = False
    threat_type: str = (
        "none"  # phishing|malware|data_breach|unauthorized_access|social_engineering|insider_threat|none
    )
    severity: str = "none"  # critical|high|medium|low|none
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    recommended_action: str = ""
    indicators: List[str] = []
    escalation_level: Optional[str] = None  # L1|L2|L3
    escalation_timer_started: bool = False


class SafetyValidation(BaseModel):
    """Output of the safety guardrails check on generated responses."""

    is_safe: bool = True
    violations: List[Dict[str, Any]] = []
    response_hash: str = ""
    was_sanitized: bool = False


class StageTimings(BaseModel):
    """Per-stage timing breakdown for the AI pipeline."""

    preprocessing_ms: Optional[int] = None
    classification_ms: Optional[int] = None
    retrieval_ms: Optional[int] = None
    sentiment_ms: Optional[int] = None
    confidence_ms: Optional[int] = None
    sla_prediction_ms: Optional[int] = None
    routing_ms: Optional[int] = None
    llm_generation_ms: Optional[int] = None
    safety_check_ms: Optional[int] = None
    total_ms: Optional[int] = None


class AIAnalysis(BaseModel):
    """Complete output of the AI pipeline for a ticket."""

    # Classification agent output
    category: str
    category_probabilities: Dict[str, float] = {}
    model_confidence: float = Field(ge=0.0, le=1.0)

    # Priority
    priority: TicketPriority
    priority_confidence: Optional[float] = None

    # Sentiment agent
    sentiment_label: SentimentLabel = SentimentLabel.NEUTRAL
    sentiment_score: float = Field(default=0.0, ge=0.0, le=1.0)
    is_frustrated: bool = False

    # Decision agent
    confidence_score: float = Field(ge=0.0, le=1.0)
    confidence_breakdown: Optional[ConfidenceBreakdown] = None
    routing_decision: RoutingDecision

    # Override flags
    sla_override: bool = False
    security_override: bool = False
    sla_breach_probability: float = Field(default=0.0, ge=0.0, le=1.0)
    estimated_resolution_hours: Optional[float] = None

    # Duplicate detection
    duplicate_of: Optional[str] = None  # parent ticket_id
    is_possible_duplicate: bool = False
    possible_duplicate_id: Optional[str] = None

    # Retriever agent output
    similar_tickets: List[SimilarTicket] = []
    top_similarity_score: float = 0.0

    # Response agent output
    generated_response: Optional[str] = None
    hallucination_detected: bool = False
    fallback_used: bool = False
    model_used: Optional[str] = None
    generation_time_ms: Optional[int] = None

    # Explainability
    lime_explanation: Optional[LIMEExplanation] = None

    # Processing metadata
    processing_time_ms: Optional[int] = None
    model_version: Optional[str] = None

    # ── HITL Enhancement fields (Phase 1) ─────────────────────────────
    time_sensitivity: Optional[str] = None  # IMMEDIATE / SAME_DAY / STANDARD
    department: Optional[str] = None  # mapped department
    threat_analysis: Optional[ThreatAnalysis] = None
    safety_validation: Optional[SafetyValidation] = None
    stage_timings: Optional[StageTimings] = None
    zero_shot_used: bool = False  # True if Ollama fallback classification was used

    # ── Security pipeline fields (Phase 2) ────────────────────────────
    threat_level: Optional[str] = None  # normal | suspicious | attack
    threat_type: Optional[str] = (
        None  # sql_injection | xss | brute_force | unauthorized_access | ddos | none
    )
    threat_confidence: Optional[float] = None  # 0.0 – 1.0
    triggered_rules: List[str] = []  # list of rule names that fired
    detection_reason: Optional[str] = None  # human-readable explanation

    # ── Image attachments ─────────────────────────────────────────────
    images: List[Dict[str, Any]] = Field(
        default_factory=list
    )  # [{filename, original_name, url, uploaded_at}]


class ResolutionData(BaseModel):
    """Data filled in when a ticket is resolved."""

    agent_id: Optional[str] = None
    action: Optional[AgentAction] = None
    final_response: Optional[str] = None
    resolution_time_hours: Optional[float] = None
    sla_breached: bool = False
    resolved_at: Optional[datetime] = None
    notes: Optional[str] = None


class TicketMetadata(BaseModel):
    """Derived metadata used for ML features."""

    user_tier: str = "Standard"  # Free / Standard / Premium / Enterprise
    submission_hour: int = 0  # 0-23
    submission_day: int = 0  # 0=Monday, 6=Sunday
    word_count: int = 0
    urgency_keyword_count: int = 0
    question_mark_count: int = 0
    exclamation_count: int = 0
    all_caps_word_count: int = 0
    duplicate_count: int = 0  # how many dupes linked to this ticket
    root_cause_group_id: Optional[str] = None


# ─── Request schemas ──────────────────────────────────────────────────


class TicketCreate(BaseModel):
    """Body of POST /api/tickets/ from the user."""

    subject: str = Field(
        min_length=5, max_length=200, description="Brief subject line for the ticket"
    )
    description: str = Field(
        min_length=20,
        max_length=5000,
        description="Detailed description of the issue (min 20 chars)",
    )
    # Optional — AI will predict if not given
    category: Optional[TicketCategory] = None
    # Optional attachment (base64 encoded image or plain text)
    attachment_text: Optional[str] = Field(default=None, max_length=10000)

    @field_validator("subject")
    @classmethod
    def subject_not_blank(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Subject cannot be blank")
        return v.strip()

    @field_validator("description")
    @classmethod
    def description_not_blank(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Description cannot be blank")
        return v.strip()


class TicketStatusUpdate(BaseModel):
    """Body of PATCH /api/tickets/{id}/status."""

    status: TicketStatus
    notes: Optional[str] = None


# ─── Database document schema ─────────────────────────────────────────


class SecurityLog(BaseModel):
    """A single entry in the ticket's security action log."""

    action: str  # security_analysis | manual_escalation | acknowledged | resolved
    actor: str  # user_id of who performed the action
    timestamp: str  # ISO datetime string
    threat_level: Optional[str] = None
    threat_type: Optional[str] = None
    confidence: Optional[float] = None
    triggered_rules: List[str] = []
    reason: Optional[str] = None


class TicketDocument(BaseModel):
    """
    Full ticket document as stored in MongoDB.
    The _id field is excluded since Motor handles it.
    """

    ticket_id: str  # TKT-XXXX
    user_id: str
    subject: str
    description: str
    cleaned_text: Optional[str] = None  # spaCy-preprocessed version
    attachment_text: Optional[str] = None
    language: str = "en"

    created_at: datetime
    updated_at: datetime
    status: TicketStatus = TicketStatus.OPEN

    ai_analysis: Optional[AIAnalysis] = None
    resolution: Optional[ResolutionData] = None
    metadata: Optional[TicketMetadata] = None

    # ── Security fields ───────────────────────────────────────────────
    is_escalated: bool = False
    security_logs: List[SecurityLog] = []

    class Config:
        use_enum_values = True
        populate_by_name = True


# ─── Response schemas ─────────────────────────────────────────────────


class TicketResponse(BaseModel):
    """API response for a single ticket with full AI analysis."""

    ticket_id: str
    subject: str
    description: str
    status: str
    created_at: datetime
    updated_at: datetime
    ai_analysis: Optional[AIAnalysis] = None
    resolution: Optional[ResolutionData] = None
    metadata: Optional[TicketMetadata] = None


class TicketListItem(BaseModel):
    """Condensed ticket for list views (agent queue, tracking)."""

    ticket_id: str
    subject: str
    status: str
    created_at: datetime

    # AI highlights only (not full analysis)
    category: Optional[str] = None
    priority: Optional[str] = None
    confidence_score: Optional[float] = None
    routing_decision: Optional[str] = None
    sentiment_label: Optional[str] = None
    sla_breach_probability: Optional[float] = None
    is_frustrated: Optional[bool] = None


class TicketSubmitResponse(BaseModel):
    """Response immediately after ticket submission with AI result."""

    ticket_id: str
    message: str
    status: str
    ai_analysis: Optional[AIAnalysis] = None
    estimated_resolution_hours: Optional[float] = None


class TicketListResponse(BaseModel):
    """Paginated list of tickets."""

    tickets: List[TicketListItem]
    total: int
    page: int
    page_size: int
    total_pages: int
