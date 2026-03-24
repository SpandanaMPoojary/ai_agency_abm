'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';

type Lead = {
  id: string;
  account_id: string;
  name: string;
  first_name?: string;
  company: string;
  profile_url: string;
  message: string;
  step_1?: string;
  step_2?: string;
  step_3?: string;
  agent_id: string;
  status?: string;
  lead_score?: number;
  human_notes?: string;
};

export default function Dashboard() {
  const router = useRouter();
  const BACKEND_URL = "http://127.0.0.1:8000";
  const [isAuthenticated, setIsAuthenticated] = useState(false);

  const [icp, setIcp] = useState('');
  const [limit, setLimit] = useState(5);
  const [platform, setPlatform] = useState('linkedin');
  const [targetUrl, setTargetUrl] = useState('');
  const [ordering, setOrdering] = useState(false);
  const [targeting, setTargeting] = useState(false);
  
  const [loading, setLoading] = useState<string | null>(null);
  const [status, setStatus] = useState<Record<string, string>>({});
  const [leads, setLeads] = useState<Lead[]>([]);
  const [localEdits, setLocalEdits] = useState<Record<string, { step_1?: string, step_2?: string, step_3?: string, notes?: string }>>({});
  const [initialLoading, setInitialLoading] = useState(true);
  const [sortByScore, setSortByScore] = useState(false);

  const sortedLeads = [...leads].sort((a, b) => {
    // Primary sort: lead_score (Descending)
    const scoreA = a.lead_score || 0;
    const scoreB = b.lead_score || 0;
    if (scoreA !== scoreB) return scoreB - scoreA;
    
    // Secondary sort: newest first (using ID)
    return Number(b.id) - Number(a.id);
  });

  const fetchLeads = async () => {
    try {
      const res = await fetch(`${BACKEND_URL}/api/leads`, { cache: 'no-store' });
      if (res.ok) {
        const data = await res.json();
        console.log("Fetched leads:", data.leads);
        setLeads(data.leads || []);
      }
    } catch (err) {
      console.error("Failed to fetch leads:", err);
    } finally {
      setInitialLoading(false);
    }
  };

  useEffect(() => {
    if (typeof window !== 'undefined') {
      const isAdmin = sessionStorage.getItem('isAdmin');
      if (!isAdmin) {
        router.push('/login');
      } else {
        setIsAuthenticated(true);
        fetchLeads();
      }
    }
  }, [router]);

  const handleOrderAgents = async (e: React.FormEvent) => {
    e.preventDefault();
    setOrdering(true);
    setStatus({});
    try {
      const res = await fetch(`${BACKEND_URL}/api/research`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        cache: 'no-store',
        body: JSON.stringify({ icp_description: icp, limit, platform })
      });
      if (res.ok) {
        const data = await res.json();
        console.log("Research output:", data.leads);
        setLeads(data.leads || []);
      } else {
        alert("Failed to order agents.");
      }
    } catch (err) {
      alert("Error connecting to backend API.");
    }
    setOrdering(false);
  };

  const handleTargetSpecific = async (e: React.FormEvent) => {
    e.preventDefault();
    setTargeting(true);
    try {
      const res = await fetch(`${BACKEND_URL}/api/target-specific`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ url: targetUrl, icp_context: icp || "B2B AI Automation" })
      });
      if (res.ok) {
        const data = await res.json();
        setLeads(prev => [data.lead, ...prev]);
        setTargetUrl('');
      } else {
        alert("Failed to target specific lead.");
      }
    } catch (err) {
      alert("Error connecting to backend API.");
    }
    setTargeting(false);
  };

  const handleReject = async (id: string) => {
    try {
      const resp = await fetch(`${BACKEND_URL}/api/reject-campaign/${id}`, { method: 'POST' });
      if (resp.ok) {
        fetchLeads();
      }
    } catch (err) {
      console.error(err);
    }
  };

  const handleApprove = async (lead: Lead) => {
    setLoading(lead.id);
    try {
      const res = await fetch(`${BACKEND_URL}/api/approve-campaign/${lead.id}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        cache: 'no-store'
      });
      if (res.ok) {
        fetchLeads();
      } else {
        alert("Failed to approve campaign.");
      }
    } catch (err) {
      alert("Error approving campaign.");
    }
    setLoading(null);
  };

  const handleCheckAcceptance = async (id: string) => {
    setLoading(`check_${id}`);
    try {
      const res = await fetch(`${BACKEND_URL}/api/check-acceptance/${id}`, { method: 'POST' });
      const data = await res.json();
      
      if (res.ok) {
        if (data.status === 'pending') {
          alert("Connection not yet found in LinkedIn Connections. Please wait 24h for Phantombuster to sync!");
        }
        fetchLeads();
      } else {
        alert(`Error: ${data.detail || "Failed to check acceptance status"}`);
      }
    } catch (err) {
      console.error(err);
      alert("Error checking acceptance status.");
    }
    setLoading(null);
  };

  const handleGenerateFollowups = async (leadId: string) => {
    setLoading(`followup_${leadId}`);
    try {
      const res = await fetch(`${BACKEND_URL}/api/generate-followups/${leadId}`, {
        method: "POST"
      });
      if (res.ok) {
        fetchLeads();
      }
    } catch (err) {
      console.error(err);
      alert("Failed to generate followups.");
    }
    setLoading(null);
  };

  const handleFireLinkedInDM = async (leadId: string) => {
    setLoading(`fire_dm_${leadId}`);
    try {
      const res = await fetch(`${BACKEND_URL}/api/fire-linkedin-dm/${leadId}`, { method: "POST" });
      const data = await res.json();
      if (res.ok) {
        alert(data.message || "LinkedIn DM Fired!");
        fetchLeads();
      } else {
        alert(`Error: ${data.detail}`);
      }
    } catch (err) {
      console.error(err);
      alert("Failed to fire LinkedIn DM.");
    }
    setLoading(null);
  };

  const handleFireColdEmail = async (leadId: string) => {
    setLoading(`fire_email_${leadId}`);
    try {
      const res = await fetch(`${BACKEND_URL}/api/fire-cold-email/${leadId}`, { method: "POST" });
      const data = await res.json();
      if (res.ok) {
        alert(data.message || "Cold Email Fired!");
        fetchLeads();
      } else {
        alert(`Error: ${data.detail}`);
      }
    } catch (err) {
      console.error(err);
      alert("Failed to fire Cold Email.");
    }
    setLoading(null);
  };

  const handleClearLeads = async () => {
    if (!confirm("Are you sure you want to clear all leads? This will delete everything from the database.")) return;
    try {
      const res = await fetch("http://127.0.0.1:8000/api/clear-leads", { method: "DELETE" });
      if (res.ok) {
        setLeads([]);
        setStatus({});
      }
    } catch (err) {
      alert("Failed to clear leads.");
    }
  };

  const handleSimulateClick = async (leadId: string) => {
    try {
      const res = await fetch("http://127.0.0.1:8000/api/webhooks/activity", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ lead_id: Number(leadId), activity: "LINK_CLICKED" })
      });
      if (res.ok) {
        fetchLeads(); // Refresh to see new score
      }
    } catch (err) {
      console.error("Simulation failed:", err);
    }
  };

  const handleUpdateSequence = async (leadId: string, step: number, newText: string) => {
    try {
      const payload: any = {};
      if (step === 0) payload.step_1 = newText;
      if (step === 1) payload.step_2 = newText;
      if (step === 2) payload.step_3 = newText;

      const res = await fetch(`http://127.0.0.1:8000/api/sequences/${leadId}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
      });
      if (res.ok) {
        setLeads(prev => prev.map(l => l.id === leadId ? { ...l, [`step_${step + 1}`]: newText } : l));
      }
    } catch (err) {
      console.error("Update failed:", err);
    }
  };

  const handleUpdateNotes = async (leadId: string, accountId: string, notes: string) => {
    try {
      const res = await fetch(`http://127.0.0.1:8000/api/leads/${accountId}/notes`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ notes })
      });
      if (res.ok) {
        setLeads(prev => prev.map(l => l.id === leadId ? { ...l, human_notes: notes } : l));
      }
    } catch (err) {
      console.error("Notes update failed:", err);
    }
  };

  const handleUpdateProfileUrl = async (leadId: string, accountId: string, newUrl: string) => {
    try {
      const res = await fetch(`http://127.0.0.1:8000/api/leads/${accountId}/url`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ url: newUrl })
      });
      if (res.ok) {
        setLeads(prev => prev.map(l => l.id === leadId ? { ...l, profile_url: newUrl } : l));
      }
    } catch (err) {
      console.error("URL update failed:", err);
    }
  };

  if (!isAuthenticated) return (
    <div className="min-h-screen flex items-center justify-center bg-brand-white">
      <p className="font-bold uppercase tracking-widest text-brand-darkgrey">Authenticating...</p>
    </div>
  );

  return (
    <main className="min-h-screen p-8 md:p-16 max-w-5xl mx-auto bg-brand-white">
      <header className="mb-8 border-b-2 border-brand-black flex justify-between items-end pb-4">
        <div>
          <h1 className="text-4xl font-bold tracking-tight text-brand-black uppercase">ABM Command Center</h1>
          <p className="text-brand-darkgrey mt-2 text-lg">Order specialized agents and approve generated campaigns.</p>
        </div>
        <div className="flex items-center space-x-6">
          <Link 
            href="/lead-scores"
            className="text-sm font-semibold uppercase text-brand-brown hover:text-brand-black transition-colors border-b-2 border-brand-brown"
          >
            📊 Lead Scores
          </Link>
          <button 
            onClick={() => setSortByScore(!sortByScore)}
            className={`text-sm font-semibold uppercase transition-colors ${sortByScore ? 'text-brand-brown' : 'text-brand-darkgrey'}`}
          >
            {sortByScore ? "★ Sorted by Score" : "☆ Sort by Score"}
          </button>
          <button 
            onClick={handleClearLeads}
            className="text-sm font-semibold uppercase text-red-600 hover:text-red-800 transition-colors"
          >
            Clear All Data
          </button>
          <button 
            onClick={fetchLeads}
            disabled={initialLoading}
            className="text-sm font-semibold uppercase text-brand-brown hover:text-brand-black transition-colors flex items-center"
          >
            {initialLoading ? "Refreshing..." : "↻ Refresh Leads"}
          </button>
          <button 
            onClick={() => { sessionStorage.removeItem('isAdmin'); router.push('/login'); }}
            className="text-sm font-semibold uppercase text-brand-darkgrey hover:text-brand-black transition-colors"
          >
            Logout
          </button>
        </div>
      </header>

      {/* Agent Order Form */}
      <section className="mb-12 bg-white p-6 md:p-8 border border-brand-grey shadow-sm relative overflow-hidden">
        <div className="absolute top-0 left-0 w-1 h-full bg-brand-brown" />
        <h2 className="text-xl font-bold tracking-wide uppercase mb-6 text-brand-black">Dispatch Agents</h2>
        <form onSubmit={handleOrderAgents} className="space-y-6">
          <div>
            <label className="block text-sm font-semibold mb-2 text-brand-darkgrey uppercase tracking-wider">Target Audience (ICP)</label>
            <textarea
              className="w-full border border-brand-grey p-3 outline-none focus:border-brand-brown text-brand-black transition-colors"
              rows={3}
              value={icp} onChange={e => setIcp(e.target.value)}
              placeholder="e.g. Founders of AI automation agencies..."
              required
            />
          </div>
          <div className="flex flex-col md:flex-row gap-6">
            <div className="flex-1">
              <label className="block text-sm font-semibold mb-2 text-brand-darkgrey uppercase tracking-wider">Amount</label>
              <input
                type="number" min="1" max="5"
                value={limit} onChange={e => setLimit(Number(e.target.value))}
                className="w-full border border-brand-grey p-3 outline-none focus:border-brand-brown text-brand-black transition-colors"
              />
            </div>
            <div className="flex-1">
              <label className="block text-sm font-semibold mb-2 text-brand-darkgrey uppercase tracking-wider">Target Platform</label>
              <select
                value={platform} onChange={e => setPlatform(e.target.value)}
                className="w-full border border-brand-grey p-3 outline-none focus:border-brand-brown text-brand-black transition-colors"
              >
                <option value="linkedin">LinkedIn</option>
                <option value="twitter">Twitter</option>
              </select>
            </div>
          </div>
          <button
            type="submit"
            disabled={ordering}
            className="w-full md:w-auto bg-brand-black hover:bg-brand-brown text-white px-8 py-3 uppercase tracking-wider font-semibold disabled:bg-brand-grey transition-colors disabled:cursor-not-allowed"
          >
            {ordering ? "Agents Running... (Approx 30s)" : "Execute Search & Generate"}
          </button>
        </form>
      </section>

      {/* Manual Target Section */}
      <section className="mb-12 border-2 border-dashed border-brand-grey p-6 bg-brand-white/50">
        <h2 className="text-lg font-bold tracking-wide uppercase mb-4 text-brand-darkgrey">Target Specific Profile</h2>
        <form onSubmit={handleTargetSpecific} className="flex gap-4">
          <input
            type="url"
            className="flex-1 border border-brand-grey p-3 outline-none focus:border-brand-brown text-brand-black transition-colors"
            placeholder="Paste LinkedIn or Twitter URL here..."
            value={targetUrl}
            onChange={e => setTargetUrl(e.target.value)}
            required
          />
          <button
            type="submit"
            disabled={targeting}
            className="bg-brand-brown hover:bg-brand-black text-white px-8 py-3 uppercase tracking-wider font-semibold disabled:bg-brand-grey transition-colors"
          >
            {targeting ? "Processing..." : "Target Now"}
          </button>
        </form>
        <p className="text-[10px] uppercase font-bold text-brand-darkgrey mt-2 tracking-widest">
          AI will research the profile and generate a personalized 3-step sequence automatically.
        </p>
      </section>

      {/* Leads List */}
      <section className="space-y-8">
        {leads.length > 0 && <h2 className="text-xl font-bold tracking-wide uppercase text-brand-black border-b border-brand-grey pb-2">Generated Campaigns</h2>}
        
        {sortedLeads.map((lead) => (
          <article 
            key={lead.id} 
            className={`bg-white border border-brand-grey shadow-sm overflow-hidden ${lead.status === 'REJECTED' ? 'opacity-50 grayscale' : ''}`}
          >
            <div className={`p-4 text-white flex justify-between items-center transition-colors duration-500 ${ (lead.status === 'SENT' || lead.status === 'Active' || lead.status === 'CONNECTION_SENT' || status[lead.id]?.includes("Sent")) ? 'bg-brand-brown' : (lead.status === 'REJECTED' ? 'bg-brand-grey' : 'bg-brand-black')}`}>
              <div>
                <p className="text-[10px] font-bold uppercase tracking-widest text-white/60 mb-1">
                  Attn: {lead.first_name || 'Decision Maker'}
                </p>
                <div className="flex items-center gap-3">
                  <h2 className="text-xl font-semibold tracking-wide">{lead.name}</h2>
                  <span className="bg-white text-brand-black px-2 py-0.5 text-xs font-bold rounded-sm shadow-sm">
                    Score: {lead.lead_score || 0}
                  </span>
                </div>
                <p className="text-brand-grey text-sm">{lead.company}</p>
              </div>
              <span className={`px-3 py-1 text-xs uppercase tracking-wider text-white border border-white/20 ${(lead.status === 'CLICKED' || lead.status === 'INTERESTED' || lead.status === 'ACCEPTED' || lead.status === 'CONNECTED') ? 'bg-green-600' : (lead.status === 'CONNECTION_SENT' || lead.status === 'Active' ? 'bg-brand-brown' : 'bg-brand-black/50')}`}>
                {(status[lead.id] || lead.status || 'Pending Review').replace('_', ' ')}
              </span>
            </div>
            
            <div className="p-6">
              <div className="flex items-center justify-between mb-4 border-b border-brand-grey pb-2">
                <h3 className="text-sm font-semibold text-brand-darkgrey uppercase tracking-wider">LinkedIn Connection Note</h3>
              </div>

              <div className="bg-brand-white p-5 border border-brand-grey text-brand-black mb-6 italic min-h-[120px] whitespace-pre-wrap relative group">
                <textarea
                  className="w-full bg-transparent border-none outline-none italic resize-none overflow-y-auto"
                  rows={6}
                  value={
                    localEdits[lead.id]?.step_1 ?? (lead.step_1 || lead.message)
                  }
                  onChange={(e) => {
                    setLocalEdits(prev => ({
                      ...prev,
                      [lead.id]: { ...prev[lead.id], step_1: e.target.value }
                    }));
                  }}
                  onBlur={(e) => {
                    handleUpdateSequence(lead.id, 0, e.target.value);
                  }}
                />
                <div className="absolute top-2 right-2 opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none">
                  <span className="text-[9px] font-bold uppercase bg-brand-black text-white px-2 py-0.5 shadow-sm">Editable</span>
                </div>
              </div>

              {/* Human Notes Section */}
              <div className="mb-6">
                <label className="text-[10px] font-bold text-brand-darkgrey uppercase tracking-widest mb-1 block">Account Strategy / Notes</label>
                <input 
                  type="text"
                  placeholder="Draft internal strategy or notes for this lead..."
                  className="w-full border-b border-brand-grey py-1 text-sm outline-none focus:border-brand-brown transition-colors bg-transparent italic text-brand-black"
                  value={localEdits[lead.id]?.notes ?? (lead.human_notes || '')}
                  onChange={(e) => {
                    setLocalEdits(prev => ({
                      ...prev,
                      [lead.id]: { ...prev[lead.id], notes: e.target.value }
                    }));
                  }}
                  onBlur={(e) => handleUpdateNotes(lead.id, lead.account_id, e.target.value)}
                />
              </div>
              
              <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
                <div className="flex items-center space-x-6">
                  <a 
                    href={lead.profile_url} 
                    target="_blank" 
                    rel="noopener noreferrer"
                    className={`text-brand-brown hover:text-brand-black font-semibold text-sm transition-colors uppercase tracking-wide border-b border-transparent hover:border-brand-black ${lead.status === 'SENT' || lead.status === 'Active' ? 'opacity-50' : ''}`}
                  >
                    View Profile &rarr;
                  </a>
                  <button 
                    onClick={() => handleSimulateClick(lead.id)}
                    className="text-[10px] font-bold uppercase tracking-tighter bg-brand-white border border-brand-grey px-2 py-1 hover:bg-brand-grey transition-colors text-brand-darkgrey"
                  >
                    Simulate Engagement (+20 Pts)
                  </button>
                </div>
                <div className="flex items-center space-x-4 w-full md:w-auto justify-end">
                  {/* Phase 1: Connection */}
                  {(lead.status === 'draft' || !lead.status || lead.status === 'PENDING') && (
                    <div className="flex gap-2">
                       <button
                        onClick={() => handleReject(lead.id)}
                        className="bg-brand-grey hover:bg-brand-black text-brand-black hover:text-white px-4 py-2 uppercase tracking-wide font-bold transition-colors"
                      >
                        Reject
                      </button>
                      <button
                        onClick={() => handleApprove(lead)}
                        disabled={loading === lead.id}
                        className="bg-brand-black hover:bg-brand-brown text-white px-6 py-2 uppercase tracking-wide font-bold transition-colors"
                      >
                        {loading === lead.id ? 'Firing...' : 'Approve & Fire'}
                      </button>
                    </div>
                  )}

                  {/* Stage Status Indication & Acceptance Check */}
                  {lead.status === 'CONNECTION_SENT' && (
                    <div className="flex flex-col items-end gap-2">
                       <button className="bg-green-600 text-white px-6 py-2 uppercase tracking-wide font-bold cursor-default opacity-90 transition-all duration-500 whitespace-nowrap">
                        ✓ Connection Sent
                      </button>
                      <button 
                        onClick={() => handleCheckAcceptance(lead.id)}
                        disabled={loading === `check_${lead.id}`}
                        className="text-[10px] font-bold uppercase tracking-widest text-brand-darkgrey hover:text-brand-brown transition-colors"
                      >
                        {loading === `check_${lead.id}` ? "Checking..." : "Check Status (Wait 24h) ↻"}
                      </button>
                    </div>
                  )}

                  {lead.status === 'REJECTED' && (
                    <span className="text-brand-darkgrey font-bold uppercase tracking-wider italic">
                      Lead Rejected
                    </span>
                  )}

                  {/* Phase 2: Follow-ups */}
                  {(lead.status === 'CONNECTED' || lead.status === 'ACCEPTED' || lead.status === 'CLICKED') && (
                    <div className="mt-8 pt-6 border-t border-brand-grey w-full">
                      <div className="flex items-center justify-between xl:justify-start xl:gap-6 mb-4">
                        <h3 className="text-sm font-semibold text-brand-darkgrey uppercase tracking-wider">Phase 2: Follow-ups</h3>
                        {!lead.step_2 && (
                           <button
                            onClick={() => handleGenerateFollowups(lead.id)}
                            disabled={loading === `followup_${lead.id}`}
                            className="bg-brand-brown hover:bg-brand-black text-white px-4 py-1.5 uppercase tracking-wide text-xs font-bold transition-colors shadow-sm"
                          >
                            {loading === `followup_${lead.id}` ? 'Drafting AI Message...' : 'Generate Follow-ups'}
                          </button>
                        )}
                      </div>

                      {lead.step_2 && (
                        <div className="space-y-6 w-full">
                          {/* LinkedIn Follow-up */}
                          <div>
                            <div className="flex items-center justify-between mb-2">
                              <label className="text-[10px] font-bold text-brand-darkgrey uppercase tracking-widest block">LinkedIn DM</label>
                              <button
                                onClick={() => handleFireLinkedInDM(lead.id)}
                                disabled={loading === `fire_dm_${lead.id}`}
                                className="text-[10px] font-bold uppercase tracking-widest bg-brand-black hover:bg-brand-brown text-white px-3 py-1 transition-colors"
                              >
                                {loading === `fire_dm_${lead.id}` ? 'Firing...' : 'Fire LinkedIn DM'}
                              </button>
                            </div>
                            <div className="bg-brand-white p-4 border border-brand-grey text-brand-black italic min-h-[100px] whitespace-pre-wrap relative group">
                              <textarea
                                className="w-full bg-transparent border-none outline-none italic resize-none overflow-y-auto"
                                rows={5}
                                value={localEdits[lead.id]?.step_2 ?? (lead.step_2 || '')}
                                onChange={(e) => {
                                  setLocalEdits(prev => ({
                                    ...prev,
                                    [lead.id]: { ...prev[lead.id], step_2: e.target.value }
                                  }));
                                }}
                                onBlur={(e) => handleUpdateSequence(lead.id, 1, e.target.value)}
                              />
                            </div>
                          </div>

                          {/* Cold Email */}
                          <div>
                            <div className="flex items-center justify-between mb-2">
                              <label className="text-[10px] font-bold text-brand-darkgrey uppercase tracking-widest block">Cold Email</label>
                              <button
                                onClick={() => handleFireColdEmail(lead.id)}
                                disabled={loading === `fire_email_${lead.id}`}
                                className="text-[10px] font-bold uppercase tracking-widest bg-brand-black hover:bg-brand-brown text-white px-3 py-1 transition-colors"
                              >
                                {loading === `fire_email_${lead.id}` ? 'Firing...' : 'Fire Cold Email'}
                              </button>
                            </div>
                            <div className="bg-brand-white p-4 border border-brand-grey text-brand-black italic min-h-[100px] whitespace-pre-wrap relative group">
                              <textarea
                                className="w-full bg-transparent border-none outline-none italic resize-none overflow-y-auto"
                                rows={5}
                                value={localEdits[lead.id]?.step_3 ?? (lead.step_3 || '')}
                                onChange={(e) => {
                                  setLocalEdits(prev => ({
                                    ...prev,
                                    [lead.id]: { ...prev[lead.id], step_3: e.target.value }
                                  }));
                                }}
                                onBlur={(e) => handleUpdateSequence(lead.id, 2, e.target.value)}
                              />
                            </div>
                          </div>
                        </div>
                      )}
                    </div>
                  )}

                  {lead.status === 'CLICKED' && (
                    <div className="flex gap-2 justify-end">
                      <span className="bg-red-600 text-white font-bold uppercase tracking-widest px-6 py-2 shadow-sm flex items-center gap-2">
                        🔥 HOT LEAD - GO TO CRM
                      </span>
                    </div>
                  )}

                  {lead.status === 'INTERESTED' && (
                    <span className="bg-green-100 text-green-800 px-4 py-2 font-bold uppercase border border-green-800">
                      🔥 High Interest - Needs Manual Reply
                    </span>
                  )}
                </div>
              </div>
            </div>
          </article>
        ))}
        {ordering && leads.length === 0 && (
          <div className="p-12 text-center text-brand-darkgrey italic text-lg border border-brand-grey border-dashed">
            Agents are currently browsing {platform} and generating content...
          </div>
        )}
      </section>
    </main>
  );
}
