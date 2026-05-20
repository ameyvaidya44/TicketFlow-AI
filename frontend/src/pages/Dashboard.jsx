/**
 * pages/Dashboard.jsx — Main dashboard with KPIs, charts, and live feed.
 */
import React, { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  AreaChart, Area, PieChart, Pie, Cell, BarChart, Bar,
  XAxis, YAxis, Tooltip, ResponsiveContainer, Legend,
} from "recharts";
import { analyticsAPI } from "../services/api";
import Loader from "../components/ui/Loader";
import { RoutingBadge, PriorityBadge, ConfidenceBar } from "../components/ui/Loader";
import { useNotifications } from "../contexts/NotificationContext";
import { Ticket, Zap, TrendingUp, AlertTriangle, CheckCircle2, Clock, Brain } from "lucide-react";

const ROUTING_COLORS = {
  AUTO_RESOLVE:      "#10b981",
  SUGGEST_TO_AGENT:  "#f59e0b",
  ESCALATE_TO_HUMAN: "#ef4444",
};

const CATEGORY_COLORS = [
  "#4169ff","#8b5cf6","#10b981","#f59e0b","#ef4444",
  "#06b6d4","#ec4899","#84cc16","#f97316","#a78bfa",
];

function StatCard({ icon: Icon, label, value, delta, color = "brand" }) {
  return (
    <div className="card-hover">
      <div className="flex items-start justify-between mb-3">
        <div className={`p-2.5 rounded-xl bg-${color}-500/15`}>
          <Icon size={18} className={`text-${color}-400`} />
        </div>
        {delta !== undefined && (
          <span className={`text-xs font-semibold px-2 py-0.5 rounded-full
            ${delta >= 0 ? "text-emerald-400 bg-emerald-500/10" : "text-red-400 bg-red-500/10"}`}>
            {delta >= 0 ? "+" : ""}{delta}%
          </span>
        )}
      </div>
      <div className="stat-value">{value}</div>
      <div className="stat-label">{label}</div>
    </div>
  );
}

export default function Dashboard() {
  const [data,    setData]    = useState(null);
  const [volume,  setVolume]  = useState([]);
  const [loading, setLoading] = useState(true);
  const [error,   setError]   = useState(false);
  const { liveTickets, alerts, slaWarnings } = useNotifications();
  const navigate = useNavigate();

  useEffect(() => {
    Promise.all([
      analyticsAPI.overview(),
      analyticsAPI.ticketVolume(14),
    ]).then(([ovRes, volRes]) => {
      setData(ovRes.data);
      setVolume(volRes.data.volume || []);
    }).catch(() => setError(true)).finally(() => setLoading(false));
  }, []);

  if (loading) return <Loader text="Loading dashboard…" />;

  if (error || !data) return (
    <div className="flex flex-col items-center justify-center h-64 gap-4 text-center">
      <AlertTriangle size={32} className="text-amber-400" />
      <div>
        <p className="text-gray-300 font-medium">Could not reach the backend</p>
        <p className="text-gray-500 text-sm mt-1">The server may be waking up — this takes ~30s on free tier.</p>
      </div>
      <button
        className="btn-primary mt-2"
        onClick={() => { setError(false); setLoading(true);
          Promise.all([analyticsAPI.overview(), analyticsAPI.ticketVolume(14)])
            .then(([ovRes, volRes]) => { setData(ovRes.data); setVolume(volRes.data.volume || []); })
            .catch(() => setError(true)).finally(() => setLoading(false));
        }}
      >
        Retry
      </button>
    </div>
  );

  const routingData = Object.entries(data?.routing_breakdown || {}).map(([name, value]) => ({
    name: name === "AUTO_RESOLVE" ? "Auto" : name === "SUGGEST_TO_AGENT" ? "Suggest" : "Escalate",
    value,
    color: ROUTING_COLORS[name],
  }));

  const categoryData = Object.entries(data?.by_category || {})
    .sort((a, b) => b[1] - a[1])
    .slice(0, 6)
    .map(([name, count], i) => ({ name, count, fill: CATEGORY_COLORS[i] }));

  return (
    <div className="space-y-6 animate-fade-in">

      {/* ── KPIs ── */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard icon={Ticket}       label="Total Tickets"        value={data?.total_tickets?.toLocaleString() || "0"} color="brand" />
        <StatCard icon={Zap}          label="Auto-Resolved"        value={`${Math.round((data?.auto_resolve_rate || 0) * 100)}%`} color="emerald" />
        <StatCard icon={AlertTriangle} label="SLA Breach Risk"     value={`${Math.round((data?.sla_breach_rate || 0) * 100)}%`} color="amber" />
        <StatCard icon={Brain}         label="Avg Processing"       value={`${data?.avg_processing_time_ms || 0}ms`} color="accent" />
      </div>

      {/* ── Charts row ── */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">

        {/* Volume chart */}
        <div className="card lg:col-span-2">
          <h3 className="text-sm font-semibold text-gray-300 mb-4">Ticket Volume (14 days)</h3>
          <ResponsiveContainer width="100%" height={200}>
            <AreaChart data={volume}>
              <defs>
                <linearGradient id="gTotal" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%"  stopColor="#4169ff" stopOpacity={0.3} />
                  <stop offset="95%" stopColor="#4169ff" stopOpacity={0}   />
                </linearGradient>
                <linearGradient id="gAuto" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%"  stopColor="#10b981" stopOpacity={0.3} />
                  <stop offset="95%" stopColor="#10b981" stopOpacity={0}   />
                </linearGradient>
              </defs>
              <XAxis dataKey="date" tick={{ fontSize: 11 }} tickFormatter={(d) => d.slice(5)} />
              <YAxis tick={{ fontSize: 11 }} />
              <Tooltip />
              <Area type="monotone" dataKey="total"        stroke="#4169ff" fill="url(#gTotal)" name="Total"   strokeWidth={2} />
              <Area type="monotone" dataKey="auto_resolved" stroke="#10b981" fill="url(#gAuto)" name="Auto"    strokeWidth={2} />
            </AreaChart>
          </ResponsiveContainer>
        </div>

        {/* Routing pie */}
        <div className="card">
          <h3 className="text-sm font-semibold text-gray-300 mb-4">Routing Split</h3>
          <ResponsiveContainer width="100%" height={140}>
            <PieChart>
              <Pie data={routingData} cx="50%" cy="50%" innerRadius={40} outerRadius={60}
                   dataKey="value" nameKey="name">
                {routingData.map((d, i) => <Cell key={i} fill={d.color} />)}
              </Pie>
              <Tooltip />
            </PieChart>
          </ResponsiveContainer>
          <div className="space-y-1.5 mt-2">
            {routingData.map((d) => (
              <div key={d.name} className="flex items-center justify-between text-xs">
                <div className="flex items-center gap-1.5">
                  <div className="w-2 h-2 rounded-full" style={{ background: d.color }} />
                  <span className="text-gray-400">{d.name}</span>
                </div>
                <span className="font-semibold text-white">{d.value}</span>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* ── Category breakdown ── */}
      <div className="card">
        <h3 className="text-sm font-semibold text-gray-300 mb-4">Tickets by Category</h3>
        <ResponsiveContainer width="100%" height={160}>
          <BarChart data={categoryData} layout="vertical">
            <XAxis type="number" tick={{ fontSize: 11 }} />
            <YAxis type="category" dataKey="name" tick={{ fontSize: 11 }} width={80} />
            <Tooltip />
            <Bar dataKey="count" radius={[0, 6, 6, 0]} name="Tickets">
              {categoryData.map((d, i) => <Cell key={i} fill={d.fill} />)}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>

      {/* ── Alerts panel ── */}
      {(alerts.length > 0 || slaWarnings.length > 0) && (
        <div className="card border-red-500/30">
          <h3 className="text-sm font-semibold text-red-400 mb-3 flex items-center gap-2">
            <AlertTriangle size={14} /> Active Alerts
          </h3>
          <div className="space-y-2">
            {alerts.slice(0, 3).map((a, i) => (
              <div key={i} className="flex items-center gap-3 p-3 rounded-xl bg-red-500/5 border border-red-500/20 text-sm">
                <span className="badge badge-escalate shrink-0">{a.severity || "P1"}</span>
                <span className="text-gray-300">{a.category}: {a.root_cause_hypothesis || "Spike detected"}</span>
              </div>
            ))}
            {slaWarnings.slice(0, 2).map((w, i) => (
              <div key={i} className="flex items-center gap-3 p-3 rounded-xl bg-amber-500/5 border border-amber-500/20 text-sm">
                <Clock size={14} className="text-amber-400 shrink-0" />
                <span className="text-gray-300">SLA: Ticket {w.ticket_id} — {Math.round(w.minutes_left)}min remaining</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* ── Live ticket feed ── */}
      {liveTickets.length > 0 && (
        <div className="card">
          <h3 className="text-sm font-semibold text-gray-300 mb-3">Live Ticket Feed</h3>
          <div className="space-y-2">
            {liveTickets.slice(0, 5).map((t, i) => (
              <div
                key={i}
                className="flex items-center gap-3 p-3 rounded-xl bg-surface hover:bg-surface-hover
                           border border-surface-border cursor-pointer transition-colors text-sm"
                onClick={() => navigate(`/tickets/${t.ticket_id}`)}
              >
                <span className="font-mono text-xs text-brand-400">{t.ticket_id}</span>
                <span className="flex-1 truncate text-gray-300">{t.subject}</span>
                <RoutingBadge decision={t.routing_decision} />
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
