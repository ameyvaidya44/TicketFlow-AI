"""
core/config.py — All application settings loaded from environment variables.
Uses pydantic-settings BaseSettings for automatic env variable binding.
"""

from pydantic_settings import BaseSettings
from pydantic import Field
from typing import Dict, List
import os


class Settings(BaseSettings):
    # ─── Application ───────────────────────────────────────────────────
    APP_NAME: str = "TicketFlow AI"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = Field(default=False, env="DEBUG")
    CORS_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:5173"]

    # ─── MongoDB ───────────────────────────────────────────────────────
    MONGODB_URL: str = Field(default="mongodb://localhost:27017", env="MONGODB_URL")
    DATABASE_NAME: str = "ticketflow_ai"

    # ─── JWT Authentication ────────────────────────────────────────────
    JWT_SECRET_KEY: str = Field(
        default="ticketflow-super-secret-change-in-production", env="JWT_SECRET_KEY"
    )
    # Alias used by security.py
    SECRET_KEY: str = Field(
        default="ticketflow-super-secret-change-in-production", env="JWT_SECRET_KEY"
    )
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440  # 24 hours
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # ─── Redis ────────────────────────────────────────────────────────
    REDIS_URL: str = Field(default="redis://localhost:6379", env="REDIS_URL")
    REDIS_HOST: str = Field(default="localhost", env="REDIS_HOST")
    REDIS_PORT: int = Field(default=6379, env="REDIS_PORT")

    # ─── Upstash Redis (NLP preprocessing cache) ──────────────────────
    UPSTASH_REDIS_REST_URL: str = Field(default="", env="UPSTASH_REDIS_REST_URL")
    UPSTASH_REDIS_REST_TOKEN: str = Field(default="", env="UPSTASH_REDIS_REST_TOKEN")

    # ─── LLM Provider ─────────────────────────────────────────────────
    # "auto"     → use cerebras if CEREBRAS_API_KEY is set, else ollama (default)
    # "cerebras" → Cerebras Inference API (fast, cloud)
    # "ollama"   → local Ollama (dev)
    # "qwen"     → Qwen / DashScope (production alternative)
    LLM_PROVIDER: str = Field(default="auto", env="LLM_PROVIDER")

    # ─── Cerebras (preferred cloud provider) ─────────────────────────
    CEREBRAS_API_KEY: str = Field(default="", env="CEREBRAS_API_KEY")
    CEREBRAS_MODEL: str = Field(default="llama-3.3-70b", env="CEREBRAS_MODEL")

    # ─── Ollama (local dev fallback) ─────────────────────────────────
    OLLAMA_URL: str = Field(default="http://localhost:11434", env="OLLAMA_URL")
    OLLAMA_MODEL: str = Field(default="mistral-nemo", env="OLLAMA_MODEL")
    OLLAMA_TEMPERATURE: float = 0.3
    OLLAMA_MAX_TOKENS: int = 250

    # ─── Qwen (production alternative) ───────────────────────────────
    QWEN_API_KEY: str = Field(default="", env="QWEN_API_KEY")
    QWEN_MODEL: str = Field(default="qwen-plus", env="QWEN_MODEL")
    QWEN_API_BASE: str = Field(
        default="https://dashscope-intl.aliyuncs.com/compatible-mode/v1",
        env="QWEN_API_BASE",
    )

    @property
    def resolved_llm_provider(self) -> str:
        """
        Resolve the effective LLM provider name.

        "auto" logic:
          - If CEREBRAS_API_KEY is set  → "cerebras"
          - Else                        → "ollama"

        Explicit values ("cerebras", "ollama", "qwen") are returned as-is.
        """
        provider = self.LLM_PROVIDER.lower().strip()
        if provider == "auto":
            return "cerebras" if self.CEREBRAS_API_KEY else "ollama"
        return provider

    # ─── ChromaDB ─────────────────────────────────────────────────────
    CHROMA_HOST: str = Field(default="localhost", env="CHROMA_HOST")
    CHROMA_PORT: int = Field(default=8001, env="CHROMA_PORT")
    CHROMA_TICKETS_COLLECTION: str = "resolved_tickets"
    CHROMA_ARTICLES_COLLECTION: str = "knowledge_articles"

    # ─── ML / AI Thresholds ───────────────────────────────────────────
    CONFIDENCE_HIGH_THRESHOLD: float = 0.85  # >= this → AUTO_RESOLVE
    CONFIDENCE_LOW_THRESHOLD: float = 0.60  # >= this → SUGGEST_TO_AGENT
    SLA_BREACH_THRESHOLD: float = 0.75  # SLA override trigger
    HALLUCINATION_SIM_THRESHOLD: float = 0.55  # min cosine sim for LLM response
    FEEDBACK_RETRAIN_THRESHOLD: int = 200  # feedback count before retraining
    DUPLICATE_EXACT_THRESHOLD: float = 0.95  # cosine sim for exact duplicate
    DUPLICATE_POSSIBLE_THRESHOLD: float = 0.85  # cosine sim for possible duplicate

    # ─── Sentence Transformer ─────────────────────────────────────────
    EMBEDDING_MODEL: str = "all-MiniLM-L6-v2"
    EMBEDDING_DIMENSION: int = 384

    # ─── Sentiment ────────────────────────────────────────────────────
    SENTIMENT_MODEL: str = "cardiffnlp/twitter-roberta-base-sentiment"
    SENTIMENT_NEGATIVE_THRESHOLD: float = 0.85  # trigger priority boost

    # ─── Root Cause Detection Thresholds (tickets per time window) ────
    ROOT_CAUSE_THRESHOLDS: Dict[str, Dict] = {
        "Network": {"count": 8, "window_minutes": 20},
        "Auth": {"count": 10, "window_minutes": 15},
        "Software": {"count": 5, "window_minutes": 30},
        "Security": {"count": 3, "window_minutes": 10},  # P0
        "Database": {"count": 5, "window_minutes": 15},
        "Email": {"count": 8, "window_minutes": 20},
        "Hardware": {"count": 6, "window_minutes": 60},
        "Access": {"count": 7, "window_minutes": 20},
        "Billing": {"count": 6, "window_minutes": 30},
        "ServiceRequest": {"count": 10, "window_minutes": 30},
    }

    # ─── SLA Limits (minutes) per domain × priority ───────────────────
    SLA_LIMITS: Dict[str, Dict[str, int]] = {
        "Network": {"Low": 2880, "Medium": 480, "High": 120, "Critical": 30},
        "Auth": {"Low": 1440, "Medium": 240, "High": 60, "Critical": 15},
        "Software": {"Low": 4320, "Medium": 1440, "High": 240, "Critical": 60},
        "Hardware": {"Low": 4320, "Medium": 1440, "High": 240, "Critical": 120},
        "Access": {"Low": 2880, "Medium": 480, "High": 120, "Critical": 30},
        "Billing": {"Low": 2880, "Medium": 1440, "High": 240, "Critical": 60},
        "Email": {"Low": 2880, "Medium": 480, "High": 120, "Critical": 60},
        "Security": {"Low": 30, "Medium": 30, "High": 30, "Critical": 5},
        "ServiceRequest": {"Low": 2880, "Medium": 480, "High": 120, "Critical": 30},
        "Database": {"Low": 1440, "Medium": 240, "High": 60, "Critical": 5},
    }

    # ─── Domain keywords for confidence boost ─────────────────────────
    DOMAIN_KEYWORDS: Dict[str, list] = {
    "Network": [
        "vpn", "wifi", "internet", "ping", "dns", "firewall",
        "network", "connection", "timeout", "connectivity",
        "routing", "gateway", "port", "bandwidth", "latency",
        "router", "switch", "wan", "lan", "ip", "packet",
        "tcp", "udp", "http", "https", "ssh", "rdp",
        "connection timeout", "connection refused", "network unreachable",
        "cannot connect", "no internet", "network error",
    ],
    "Auth": [
        "password", "login", "locked", "otp", "2fa", "token",
        "sso", "authentication", "credentials", "unlock", "reset",
        "account", "access denied", "permission denied", "unauthorized",
        "forbidden", "mfa", "multi factor", "password reset",
        "account lockout", "sign in", "sign up", "login failed",
    ],
    "Security": [
        "phishing", "malware", "virus", "ransomware", "breach",
        "hack", "suspicious", "attack", "injection", "exploit",
        "vulnerability", "compromised", "unauthorized access",
        "security", "threat", "suspicious activity", "data breach",
        "infection", "exploit", "sql injection", "xss",
    ],
        "Database": [
        # Main database terms
        "database", "db", "sql", "query", "mysql", "postgres",
        "oracle", "mongodb", "redis", "mongodb", "mariadb",
        
        # Database issues
        "access denied", "permission denied", "connection refused",
        "connection timeout", "cannot connect", "database down",
        "database crash", "database error", "database unavailable",
        "database offline", "database is down",
        
        # Technical terms
        "sql", "schema", "table", "row", "column", "index",
        "replication", "backup", "restore", "transaction",
        "slow query", "connection pool", "data corruption",
        "disk space", "out of memory", "lock", "deadlock",
        "slave", "master", "synchronization", "lag",
        
        # Production database
        "production database", "prod database", "production db",
        "database server", "database service",
    ],
    "Billing": [
        # VERY specific - avoid false positives
        "invoice", "payment", "refund", "subscription", "billing",
        "credit card", "charge", "duplicate charge", "overcharge",
        "payment method", "payment failed", "upgrade", "downgrade",
        "receipt", "bill", "pricing", "cost", "subscription renewal",
        "cancellation", "billing address", "invoice number",
    ],
    "Software": [
        "crash", "error", "install", "update", "freeze", "exception",
        "bug", "performance", "slow", "lag", "unresponsive", "hangs",
        "failure", "not working", "broken", "unable to", "cannot",
        "app crash", "application error", "javascript", "exception",
        "debug", "warning", "failed", "warning message",
    ],
    "Hardware": [
        "laptop", "screen", "keyboard", "printer", "battery", "usb",
        "monitor", "device", "hardware", "physical", "broken",
        "defective", "damaged", "not working", "flickering", "display",
        "disconnected", "hard drive", "motherboard", "fan", "power",
        "overheating", "storage", "memory", "ram", "ssd",
    ],
    "Email": [
        "email", "inbox", "attachment", "spam", "mailbox", "smtp",
        "calendar", "outlook", "gmail", "mail", "message", "send",
        "receive", "delivery", "sync", "email not receiving",
        "email not sending", "mail delivery", "mail server",
        "imap", "pop3", "email client", "outlook sync",
    ],
        "Access": [
        # Core access terms
        "access", "permission", "grant", "revoke", "denied",
        "access denied", "permission denied", "access error",
        
        # Role/Group terms
        "role", "admin", "restricted", "group", "membership",
        "can't access", "no access", "need access", "unable to access",
        
        # File/Folder terms
        "folder access", "file access", "directory access",
        "shared folder", "share", "sharepoint",
        
        # System access
        "login", "logon", "sign in", "authentication",
        "credentials", "username", "password",
        "access control", "acl", "group policy", "ldap",
        "active directory", "ad group", "domain",
    ],
    "ServiceRequest": [
        "request", "new", "setup", "provision", "create", "onboarding",
        "enable", "activate", "install", "configure", "license",
        "can you", "please", "need", "want", "setup", "new user",
        "new account", "new email", "new laptop", "provisioning",
    ],
}

    # ─── Auto-resolve targets per domain ─────────────────────────────
    AUTO_RESOLVE_TARGETS: Dict[str, float] = {
        "Network": 0.35,
        "Auth": 0.65,
        "Software": 0.45,
        "Hardware": 0.25,
        "Access": 0.40,
        "Billing": 0.50,
        "Email": 0.45,
        "Security": 0.05,  # almost never auto-resolve
        "ServiceRequest": 0.55,
        "Database": 0.20,
    }

    # ─── Ticket ID prefix ─────────────────────────────────────────────
    TICKET_ID_PREFIX: str = "TKT"

    # ─── HITL Enhancement settings (Phase 1+) ────────────────────────
    # Higher threshold for sensitive categories
    BILLING_AUTO_RESOLVE_THRESHOLD: float = 0.92
    SECURITY_AUTO_RESOLVE_THRESHOLD: float = 1.0  # effectively never auto-resolve

    # Concurrency limits for the AI pipeline
    MAX_CONCURRENT_PIPELINES: int = 20

    # Department taxonomy
    DEPARTMENT_TAXONOMY: List[str] = [
        "NETWORK",
        "SOFTWARE",
        "DATABASE",
        "SECURITY",
        "BILLING",
        "HR_FACILITIES",
    ]

    # Category → Department mapping
    CATEGORY_TO_DEPARTMENT: Dict[str, str] = {
        "Network": "NETWORK",
        "Auth": "SOFTWARE",
        "Software": "SOFTWARE",
        "Hardware": "HR_FACILITIES",
        "Access": "SOFTWARE",
        "Billing": "BILLING",
        "Email": "NETWORK",
        "Security": "SECURITY",
        "ServiceRequest": "HR_FACILITIES",
        "Database": "DATABASE",
    }

    # Escalation chain timeouts (minutes)
    ESCALATION_L2_TIMEOUT_MINUTES: int = 15
    ESCALATION_L3_TIMEOUT_MINUTES: int = 30

    # ─── Image upload settings ────────────────────────────────────────
    MAX_IMAGE_SIZE_MB: int = 5
    MAX_IMAGES_PER_TICKET: int = 3
    UPLOAD_DIR: str = "uploads/tickets"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
        # Allow extra fields from env without causing validation errors
        extra = "ignore"


# Singleton settings instance — import this everywhere
settings = Settings()
