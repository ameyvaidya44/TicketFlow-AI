/**
 * pages/Login.jsx — Authentication page.
 */
import React, { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../contexts/AuthContext";
import toast from "react-hot-toast";
import { Zap, Mail, Lock, LogIn } from "lucide-react";
import Navbar from "../components/landing/Navbar";

export default function Login() {
  const { login } = useAuth();
  const navigate  = useNavigate();
  const [form,    setForm]    = useState({ email: "", password: "" });
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    try {
      await login(form.email, form.password);
      toast.success("Welcome back!");
      navigate("/dashboard");
    } catch (err) {
      const detail = err.response?.data?.detail;
      const message = typeof detail === "string"
        ? detail
        : Array.isArray(detail) && detail.length > 0
          ? detail[0].msg
          : "Invalid credentials";
      toast.error(message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-surface flex items-center justify-center p-4">
      <Navbar />
      {/* Glow background */}
      <div className="absolute inset-0 overflow-hidden pointer-events-none">
        <div className="absolute top-1/4 left-1/2 -translate-x-1/2 w-96 h-96 bg-brand-600/10 rounded-full blur-3xl" />
        <div className="absolute bottom-1/4 left-1/3 w-64 h-64 bg-accent-600/10 rounded-full blur-3xl" />
      </div>

      <div className="relative w-full max-w-sm animate-slide-up">

        {/* Logo */}
        <div className="text-center mb-8">
          <div className="inline-flex items-center gap-2 mb-4">
            <div className="w-10 h-10 rounded-xl bg-gradient-brand flex items-center justify-center shadow-glow">
              <Zap size={20} className="text-white" />
            </div>
            <span className="text-xl font-bold text-white">TicketFlow AI</span>
          </div>
          <p className="text-gray-400 text-sm">Sign in to your account</p>
        </div>

        {/* Card */}
        <div className="card">
          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="label">Email</label>
              <div className="relative">
                <Mail size={16} className="absolute left-3 top-3.5 text-gray-500" />
                <input
                  id="email"
                  type="email"
                  className="input pl-9"
                  placeholder="you@company.com"
                  value={form.email}
                  onChange={(e) => setForm({ ...form, email: e.target.value })}
                  required
                />
              </div>
            </div>

            <div>
              <label className="label">Password</label>
              <div className="relative">
                <Lock size={16} className="absolute left-3 top-3.5 text-gray-500" />
                <input
                  id="password"
                  type="password"
                  className="input pl-9"
                  placeholder="••••••••"
                  value={form.password}
                  onChange={(e) => setForm({ ...form, password: e.target.value })}
                  required
                />
              </div>
            </div>

            <button
              id="login-btn"
              type="submit"
              className="btn-primary w-full justify-center mt-2"
              disabled={loading}
            >
              {loading ? (
                <span className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
              ) : (
                <><LogIn size={16} />Sign In</>
              )}
            </button>
          </form>

          {/* Demo accounts */}
          <div className="mt-5 pt-4 border-t border-surface-border">
            <p className="text-xs text-gray-500 text-center mb-3">Demo accounts</p>
            <div className="grid grid-cols-3 gap-2">
              {[
                { label: "User",  email: "user@ticketflow.ai",  password: "user123" },
                { label: "Agent", email: "agent1@ticketflow.ai", password: "agent123" },
                { label: "Admin", email: "admin@ticketflow.ai", password: "admin123" },
              ].map((demo) => (
                <button
                  key={demo.label}
                  onClick={() => setForm({ email: demo.email, password: demo.password })}
                  className="text-xs py-1.5 rounded-lg bg-surface-hover border border-surface-border
                             text-gray-400 hover:text-white hover:border-brand-600/50 transition-colors"
                >
                  {demo.label}
                </button>
              ))}
            </div>
          </div>
        </div>

        <p className="text-center text-sm text-gray-500 mt-6">
          Don't have an account?{" "}
          <Link to="/register" className="text-brand-400 hover:text-brand-300 font-medium">
            Register
          </Link>
        </p>
      </div>
    </div>
  );
}
