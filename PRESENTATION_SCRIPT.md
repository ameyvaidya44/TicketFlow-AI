# TicketFlow AI — Presentation Script
### System Architecture Walkthrough | 7–9 Minutes

---

## [OPENING — 30 seconds]

"Let me walk you through the complete system architecture of TicketFlow AI — an intelligent IT support ticket automation platform that uses a multi-agent AI pipeline to automatically classify, prioritize, route, and respond to support tickets — without human intervention, unless the system decides a human is actually needed."

---

## [TECH STACK — 45 seconds]

"Starting on the left, here's the actual tech stack powering this system.

The frontend is React with Tailwind CSS. The backend is FastAPI — Python's async web framework — served by Uvicorn. For machine learning we use Scikit-learn for our trained classification models, Sentence Transformers for generating text embeddings, and ChromaDB as our vector database. Note — there's no Docker in this project. Everything runs directly on the host machine."

---

## [FRONTEND + API LAYER — 45 seconds]

"The Frontend Layer is a React and Tailwind dashboard giving agents real-time ticket processing, confidence score visualization, and manual override capability. Agents can see exactly what the AI decided and why.

Below that is the API Gateway — FastAPI endpoints with async processing. The two key endpoints are POST /api/tickets/ for submitting a ticket, and GET /api/tickets/{id} for retrieving one. Every submission triggers the full AI pipeline."

---

## [NLP PREPROCESSING + CACHE — 1 minute]

"The first thing that happens when a ticket arrives is the NLP Processing Layer. The raw text goes through basic text cleaning, language detection, the spaCy NLP pipeline for tokenization and lemmatization, TF-IDF vectorization, and feature extraction.

Now — on the right you'll see the connection to Upstash Redis. This is a caching layer built specifically for this step. IT support tickets are highly repetitive — 'VPN not working', 'forgot my password', 'can't login' — these come in constantly. So instead of running spaCy every single time, we cache the preprocessing result in Upstash Redis with a 7-day TTL, keyed by a hash of the ticket text.

On a cache hit, this step takes 5 to 15 milliseconds. On a miss, it's 50 to 100 milliseconds. At a 40 to 60 percent hit rate, that's a meaningful saving across thousands of tickets."

---

## [CLASSIFICATION — 1 minute]

"Once preprocessed, the text enters the Classification Layer — 10 categories: Network, Auth, Software, Hardware, Access, Billing, Email, Security, Service Request, and Database.

This is a two-tier system. Tier 1 is ML classification — a Logistic Regression model for category and a Random Forest for priority, both trained on historical ticket data. If model confidence is above 0.70, we trust it.

If it drops below 0.70, we fall back to Tier 2 — keyword matching. This rule-based fallback ensures we always get a reasonable classification even when the ML model is uncertain."

---

## [PRIORITY + SLA — 45 seconds]

"In parallel, two more layers run.

Priority Prediction uses a Random Forest to determine Low, Medium, High, or Critical. Security tickets are always forced to Critical — hardcoded by design, no exceptions.

The SLA Prediction Layer calculates breach probability based on category, priority, user tier, time of day, and queue length. If that probability exceeds 75%, the ticket is automatically escalated to a human — regardless of AI confidence. SLA compliance is non-negotiable."

---

## [SENTIMENT — 30 seconds]

"There's also a Sentiment Analysis step running on every ticket. It uses keyword-based detection to classify the user's tone as POSITIVE, NEUTRAL, or NEGATIVE. If a user is detected as frustrated — negative tone with high confidence — the system applies a confidence penalty, making escalation to a human more likely. Frustrated users get human attention."

---

## [CONFIDENCE SCORING + ROUTING — 1 minute 15 seconds]

"This is the brain of the system — the Confidence Scoring and Routing Layer.

The composite confidence score is computed as:

> 0.60 × model confidence + 0.25 × vector similarity + 0.20 × domain keyword boost

It's not just trusting the ML model — it combines model certainty with how similar this ticket is to past resolved tickets, and whether the text contains domain keywords that confirm the classification. Sentiment penalties are then applied on top.

The routing decision falls into one of three outcomes:

- Above 0.78 → AUTO RESOLVE. The system handles it fully automatically.
- Between 0.55 and 0.78 → SUGGEST TO AGENT. AI generates a response, a human reviews before it's sent.
- Below 0.55 → ESCALATE TO HUMAN. No AI response. A human takes over completely.

There's also a Security Override — any security-classified ticket bypasses confidence scoring entirely and goes straight to escalation. Always."

---

## [LLM RESPONSE GENERATION — 1 minute]

"For tickets routed to AUTO RESOLVE or SUGGEST TO AGENT, the system generates an actual response using the LLM Response Generation layer.

This uses Retrieval-Augmented Generation — RAG. ChromaDB retrieves the top 3 most similar resolved tickets, extracts their solutions, and passes that as context to the language model. The LLM generates a professional, specific, actionable response — not a generic one.

The LLM provider is environment-switchable. In local development we use Ollama running Mistral locally. In production we switch to Qwen via the cloud API — one environment variable change, zero code changes. That's a factory pattern.

There's also a hallucination guard — after generation, we compute cosine similarity between the LLM response and the retrieved solution. If they're too different — below 0.55 — we flag it as a hallucination and fall back to the retrieved solution directly. The system never sends a made-up answer."

---

## [DATABASES — 30 seconds]

"Three storage layers on the right.

MongoDB is the primary database — tickets, users, audit logs, feedback. Upstash Redis is the NLP preprocessing cache. ChromaDB is the vector database storing embeddings of every resolved ticket and knowledge base article — powering both RAG retrieval and duplicate detection."

---

## [SECURITY + MONITORING — 30 seconds]

"The Security Layer runs a dual pipeline on every ticket — a rule engine plus ChromaDB attack similarity search — detecting phishing, malware, social engineering, and unauthorized access. Detected attacks force Critical priority, override routing to escalation, and broadcast a real-time WebSocket alert to all connected agents.

Loguru handles structured logging across the entire system — every pipeline run, every routing decision, every model prediction is logged for compliance and for feeding the retraining loop."

---

## [CLOSING — 30 seconds]

"So to summarize — a ticket comes in, gets preprocessed with Redis caching, classified by trained ML models, scored by a weighted confidence formula, routed to the right destination, and if appropriate, gets a RAG-generated LLM response with a hallucination guard. Every decision is logged, every agent approval feeds back into ChromaDB, and the models retrain automatically as more data accumulates.

The system is designed so humans are only involved when the AI genuinely isn't confident enough — which means agents spend their time on tickets that actually need them."

---

## Timing Reference

| Section | Time |
|---|---|
| Opening | 0:00 – 0:30 |
| Tech Stack | 0:30 – 1:15 |
| Frontend + API | 1:15 – 2:00 |
| NLP + Cache | 2:00 – 3:00 |
| Classification | 3:00 – 4:00 |
| Priority + SLA | 4:00 – 4:45 |
| Sentiment | 4:45 – 5:15 |
| Confidence + Routing | 5:15 – 6:30 |
| LLM Generation | 6:30 – 7:30 |
| Databases | 7:30 – 8:00 |
| Security + Monitoring | 8:00 – 8:30 |
| Closing | 8:30 – 9:00 |

---

> All claims in this script are verified against the actual codebase.
