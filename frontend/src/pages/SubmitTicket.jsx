/**
 * pages/SubmitTicket.jsx — Ticket submission form with real-time AI analysis result.
 */
import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import { ticketsAPI, imagesAPI } from "../services/api";
import { RoutingBadge, PriorityBadge, ConfidenceBar } from "../components/ui/Loader";
import ImageUpload from "../components/ImageUpload";
import toast from "react-hot-toast";
import { Send, CheckCircle2, Brain, Zap, Clock, AlertTriangle } from "lucide-react";

const CATEGORIES_HINT = [
  "Network / VPN issue", "Login / Password reset", "Software crash or bug",
  "Hardware malfunction", "Access permissions", "Billing question",
  "Email / Calendar issue", "Security incident", "New service request", "Database error",
];

export default function SubmitTicket() {
  const navigate = useNavigate();
  const [form, setForm] = useState({ subject: "", description: "", user_tier: "Standard" });
  const [loading,  setLoading]  = useState(false);
  const [result,   setResult]   = useState(null);
  const [imageFiles, setImageFiles] = useState([]);
  const [uploadingImages, setUploadingImages] = useState(false);

  const set = (k) => (e) => setForm({ ...form, [k]: e.target.value });

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (form.description.length < 20) {
      toast.error("Please provide more details (at least 20 characters)");
      return;
    }
    setLoading(true);
    try {
      const res = await ticketsAPI.submit(form);
      setResult(res.data);
      toast.success("Ticket submitted successfully!");

      // Upload images after ticket creation (non-blocking)
      if (imageFiles.length > 0 && res.data?.ticket_id) {
        setUploadingImages(true);
        try {
          await imagesAPI.upload(res.data.ticket_id, imageFiles);
          toast.success(`${imageFiles.length} image(s) uploaded!`);
        } catch (imgErr) {
          toast("Ticket submitted but image upload failed. You can retry from the ticket detail page.", { icon: "⚠️" });
        } finally {
          setUploadingImages(false);
          setImageFiles([]);
        }
      }
    } catch (err) {
      toast.error(err.response?.data?.detail || "Submission failed. Is the backend running?");
    } finally {
      setLoading(false);
    }
  };

  // ── Result view after submission ─────────────────────────────────
  if (result) {
    const ai = result.ai_analysis || {};
    const routing = ai.routing_decision;
    const routingMsg = {
      AUTO_RESOLVE:      { icon: CheckCircle2, color: "emerald", msg: "Your ticket was automatically resolved by AI!" },
      SUGGEST_TO_AGENT:  { icon: Clock,        color: "amber",   msg: "An agent will review the AI suggestion shortly." },
      ESCALATE_TO_AGENT: { icon: AlertTriangle, color: "orange", msg: "An agent will handle this ticket directly." },
      ESCALATE_TO_HUMAN: { icon: AlertTriangle, color: "red",    msg: "This has been escalated to a human specialist." },
    }[routing] || {};
    const Icon = routingMsg.icon || Zap;

    return (
      <div className="max-w-2xl mx-auto space-y-6 animate-slide-up">
        {/* Status banner */}
        <div className={`card border-${routingMsg.color}-500/30 bg-${routingMsg.color}-500/5`}>
          <div className="flex items-center gap-3">
            <div className={`p-3 rounded-xl bg-${routingMsg.color}-500/20`}>
              <Icon size={20} className={`text-${routingMsg.color}-400`} />
            </div>
            <div>
              <p className="font-semibold text-white">{result.message}</p>
              <p className="text-sm text-gray-400 mt-0.5">{routingMsg.msg}</p>
            </div>
          </div>
          <div className="mt-3 pt-3 border-t border-surface-border flex items-center gap-3 text-sm">
            <span className="font-mono text-brand-400">{result.ticket_id}</span>
            <span className="text-gray-500">•</span>
            <RoutingBadge decision={routing} />
            <PriorityBadge priority={ai.priority} />
          </div>
        </div>

        {/* AI Analysis breakdown */}
        <div className="card">
          <h3 className="text-sm font-semibold text-gray-200 mb-4 flex items-center gap-2">
            <Brain size={16} className="text-brand-400" /> AI Analysis
          </h3>
          <div className="grid grid-cols-2 gap-4 text-sm">
            <div>
              <span className="text-gray-500">Category</span>
              <p className="font-semibold text-white mt-0.5">{ai.category || "—"}</p>
            </div>
            <div>
              <span className="text-gray-500">Priority</span>
              <div className="mt-0.5"><PriorityBadge priority={ai.priority} /></div>
            </div>
            <div>
              <span className="text-gray-500">Sentiment</span>
              <p className="font-semibold text-white mt-0.5 capitalize">{ai.sentiment_label || "—"}</p>
            </div>
            <div>
              <span className="text-gray-500">SLA Breach Risk</span>
              <p className="font-semibold text-white mt-0.5">
                {ai.sla_breach_probability ? `${Math.round(ai.sla_breach_probability * 100)}%` : "—"}
              </p>
            </div>
          </div>

          {/* Confidence */}
          <div className="mt-4">
            <div className="flex items-center justify-between mb-1.5">
              <span className="text-xs text-gray-500">AI Confidence</span>
              <RoutingBadge decision={routing} />
            </div>
            <ConfidenceBar score={ai.confidence_score} />
          </div>
        </div>

        {/* Generated response */}
        {ai.generated_response ? (
          <div className="card">
            <h3 className="text-sm font-semibold text-gray-200 mb-3">AI Generated Response</h3>
            <div className="bg-surface rounded-xl p-4 border border-surface-border">
              <p className="text-sm text-gray-300 leading-relaxed whitespace-pre-wrap">
                {ai.generated_response}
              </p>
            </div>
            {ai.fallback_used && (
              <p className="text-xs text-amber-400 mt-2">⚠ Retrieved from knowledge base (LLM unavailable)</p>
            )}
          </div>
        ) : (
          <div className="card border-surface-border">
            <h3 className="text-sm font-semibold text-gray-200 mb-3">AI Generated Response</h3>
            <div className="bg-surface rounded-xl p-4 border border-surface-border flex items-start gap-3">
              <AlertTriangle size={16} className="text-amber-400 mt-0.5 shrink-0" />
              <p className="text-sm text-gray-400 leading-relaxed">
                {routing === "ESCALATE_TO_HUMAN"
                  ? "This ticket requires specialist review. A human agent will respond with a tailored solution."
                  : routing === "ESCALATE_TO_AGENT"
                  ? "AI confidence was insufficient to auto-generate a response. An agent will handle this directly."
                  : "AI response is being processed. Check back on the ticket detail page shortly."}
              </p>
            </div>
          </div>
        )}

        {/* Actions */}
        <div className="flex gap-3">
          <button onClick={() => navigate(`/tickets/${result.ticket_id}`)} className="btn-primary flex-1 justify-center">
            View Ticket Details
          </button>
          <button onClick={() => { setResult(null); setForm({ subject: "", description: "", user_tier: "Standard" }); setImageFiles([]); }}
            className="btn-secondary">
            Submit Another
          </button>
        </div>
      </div>
    );
  }

  // ── Submit form ───────────────────────────────────────────────────
  return (
    <div className="max-w-2xl mx-auto animate-slide-up">
      <div className="mb-6">
        <h1 className="page-title">Submit a Support Ticket</h1>
        <p className="page-subtitle">Our AI will analyze and handle your ticket in under 2 seconds.</p>
      </div>

      <div className="card">
        <form onSubmit={handleSubmit} className="space-y-5">
          <div>
            <label className="label">Subject *</label>
            <input
              id="ticket-subject"
              className="input"
              placeholder="Brief description of your issue"
              value={form.subject}
              onChange={set("subject")}
              maxLength={120}
              required
            />
          </div>

          <div>
            <label className="label">Description *</label>
            <textarea
              id="ticket-description"
              className="textarea"
              rows={6}
              placeholder="Provide as much detail as possible — what happened, when it started, what you've already tried…"
              value={form.description}
              onChange={set("description")}
              required
            />
            <p className="text-xs text-gray-500 mt-1">{form.description.length} chars · min 20</p>
          </div>

          {/* Image Upload */}
          <ImageUpload files={imageFiles} setFiles={setImageFiles} />

          {/* Quick examples */}
          <div>
            <p className="label">Quick examples</p>
            <div className="flex flex-wrap gap-2">
              {CATEGORIES_HINT.map((hint) => (
                <button
                  key={hint}
                  type="button"
                  onClick={() => setForm({ ...form, subject: hint })}
                  className="text-xs px-3 py-1.5 rounded-lg bg-surface-hover border border-surface-border
                             text-gray-400 hover:text-white hover:border-brand-600/50 transition-colors"
                >
                  {hint}
                </button>
              ))}
            </div>
          </div>

          <button
            id="submit-ticket-btn"
            type="submit"
            className="btn-primary w-full justify-center"
            disabled={loading}
          >
            {loading ? (
              <>
                <span className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                Running AI Pipeline…
              </>
            ) : (
              <><Send size={16} />Submit Ticket</>
            )}
          </button>
        </form>
      </div>
    </div>
  );
}
