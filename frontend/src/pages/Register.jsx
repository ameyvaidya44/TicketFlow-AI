/**
 * pages/Register.jsx — User registration page.
 */
import React, { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../contexts/AuthContext";
import toast from "react-hot-toast";
import { Zap, UserPlus } from "lucide-react";

const ROLES = ["user", "agent", "senior_engineer", "admin"];
const TIERS = ["Standard", "Premium", "Enterprise"];

export default function Register() {
  const { register } = useAuth();
  const navigate = useNavigate();
  const [form, setForm] = useState({
    name: "", email: "", password: "", role: "user", tier: "Standard",
  });
  const [loading, setLoading] = useState(false);

  const set = (k) => (e) => setForm({ ...form, [k]: e.target.value });

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    try {
      await register(form);
      toast.success("Account created! Please log in.");
      navigate("/login");
    } catch (err) {
      // Pydantic 422 returns detail as an array of {msg, loc, ...} objects
      const detail = err.response?.data?.detail;
      let message = "Registration failed";
      if (typeof detail === "string") {
        message = detail;
      } else if (Array.isArray(detail) && detail.length > 0) {
        message = detail[0].msg || message;
      }
      toast.error(message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-surface flex items-center justify-center p-4">
      <div className="absolute inset-0 overflow-hidden pointer-events-none">
        <div className="absolute top-1/3 right-1/3 w-80 h-80 bg-brand-600/10 rounded-full blur-3xl" />
      </div>

      <div className="relative w-full max-w-sm animate-slide-up">
        <div className="text-center mb-8">
          <div className="inline-flex items-center gap-2 mb-4">
            <div className="w-10 h-10 rounded-xl bg-gradient-brand flex items-center justify-center shadow-glow">
              <Zap size={20} className="text-white" />
            </div>
            <span className="text-xl font-bold text-white">TicketFlow AI</span>
          </div>
          <p className="text-gray-400 text-sm">Create your account</p>
        </div>

        <div className="card">
          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="label">Full Name</label>
              <input className="input" placeholder="Jane Smith" value={form.name} onChange={set("name")} required />
            </div>
            <div>
              <label className="label">Email</label>
              <input className="input" type="email" placeholder="jane@company.com" value={form.email} onChange={set("email")} required />
            </div>
            <div>
              <label className="label">Password</label>
              <input className="input" type="password" placeholder="Min 8 characters" value={form.password} onChange={set("password")} minLength={8} required />
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="label">Role</label>
                <select className="input" value={form.role} onChange={set("role")}>
                  {ROLES.map((r) => <option key={r} value={r}>{r}</option>)}
                </select>
              </div>
              <div>
                <label className="label">Tier</label>
                <select className="input" value={form.tier} onChange={set("tier")}>
                  {TIERS.map((t) => <option key={t} value={t}>{t}</option>)}
                </select>
              </div>
            </div>
            <button id="register-btn" type="submit" className="btn-primary w-full justify-center mt-2" disabled={loading}>
              {loading
                ? <span className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                : <><UserPlus size={16} />Create Account</>
              }
            </button>
          </form>
        </div>

        <p className="text-center text-sm text-gray-500 mt-6">
          Already have an account?{" "}
          <Link to="/login" className="text-brand-400 hover:text-brand-300 font-medium">Sign In</Link>
        </p>
      </div>
    </div>
  );
}
