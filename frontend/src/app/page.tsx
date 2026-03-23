'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';

type Lead = {
  id: string;
  account_id: string;
  name: string;
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
  const [initialLoading, setInitialLoading] = useState(true);
  const [sortByScore, setSortByScore] = useState(false);

  const sortedLeads = [...leads].sort((a, b) => {
    if (sortByScore) {
      return (b.lead_score || 0) - (a.lead_score || 0);
    }
    const valA = Number(a.id);
    const valB = Number(b.id);
    if (isNaN(valA) || isNaN(valB)) return 0;
    return valB - valA; // Default to newest first
  });

  const fetchLeads = async () => {
    try {
      const res = await fetch("http://127.0.0.1:8000/api/leads", { cache: 'no-store' });
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
      const res = await fetch("http://127.0.0.1:8000/api/research", {
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
      const res = await fetch("http://127.0.0.1:8000/api/target-specific", {
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

  const handleApprove = async (lead: Lead) => {
    setLoading(lead.id);
    try {
      const res = await fetch(`http://127.0.0.1:8000/api/approve-campaign/${lead.id}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" }
      });
      
      if (res.ok) {
        setStatus(prev => ({ ...prev, [lead.id]: "Launched Successfully" }));
        fetchLeads(); // Refresh list to get updated statuses from DB
      } else {
        const errorData = await res.json().catch(() => ({}));
        setStatus(prev => ({ ...prev, [lead.id]: errorData.detail || "Validation Failed" }));
      }
    } catch (err) {
      console.error(err);
      setStatus(prev => ({ ...prev, [lead.id]: "Connection Error" }));
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
            className="bg-white border border-brand-grey shadow-sm overflow-hidden"
          >
            <div className={`p-4 text-white flex justify-between items-center ${lead.status === 'SENT' || lead.status === 'Active' ? 'bg-brand-brown' : 'bg-brand-black'}`}>
              <div>
                <div className="flex items-center gap-3">
                  <h2 className="text-xl font-semibold tracking-wide">{lead.name}</h2>
                  <span className="bg-white text-brand-black px-2 py-0.5 text-xs font-bold rounded-sm shadow-sm">
                    Score: {lead.lead_score || 0}
                  </span>
                </div>
                <p className="text-brand-grey text-sm">{lead.company}</p>
              </div>
              <span className={`px-3 py-1 text-xs uppercase tracking-wider text-white border border-white/20 ${lead.status === 'SENT' || lead.status === 'Active' ? 'bg-green-600' : 'bg-brand-black/50'}`}>
                {lead.status === 'SENT' || lead.status === 'Active' ? 'Active' : 'Pending Review'}
              </span>
            </div>
            
            <div className="p-6">
              <div className="flex items-center justify-between mb-4 border-b border-brand-grey pb-2">
                <h3 className="text-sm font-semibold text-brand-darkgrey uppercase tracking-wider">Outreach Sequence</h3>
                <div className="flex bg-brand-white border border-brand-grey p-1 space-x-1">
                  {['Step 1 (LI)', 'Step 2 (Email)', 'Step 3 (LI)'].map((tab, i) => (
                    <button
                      key={i}
                      onClick={() => setStatus(prev => ({ ...prev, [`tab_${lead.id}`]: i.toString() }))}
                      className={`px-3 py-1 text-[10px] font-bold uppercase transition-colors ${
                        (status[`tab_${lead.id}`] || "0") === i.toString() 
                        ? 'bg-brand-black text-white' 
                        : 'text-brand-darkgrey hover:bg-brand-grey'
                      }`}
                    >
                      {tab}
                    </button>
                  ))}
                </div>
              </div>

              <div className="bg-brand-white p-5 border border-brand-grey text-brand-black mb-6 italic min-h-[120px] whitespace-pre-wrap relative group">
                <textarea
                  className="w-full bg-transparent border-none outline-none italic resize-none"
                  rows={4}
                  value={
                    (status[`tab_${lead.id}`] || "0") === "0" ? (lead.step_1 || lead.message) :
                    (status[`tab_${lead.id}`] || "1") === "1" ? (lead.step_2 || "No email generated.") :
                    (lead.step_3 || "No follow-up generated.")
                  }
                  onChange={(e) => handleUpdateSequence(lead.id, parseInt(status[`tab_${lead.id}`] || "0"), e.target.value)}
                />
                <div className="absolute top-2 right-2 opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none">
                  <span className="text-[9px] font-bold uppercase bg-brand-black text-white px-2 py-0.5 shadow-sm">Editable</span>
                </div>
              </div>

              {/* Human Notes Section */}
              <div className="mb-6">
                <label className="text-[10px] font-bold text-brand-darkgrey uppercase tracking-widest mb-1 block">Internal Human Notes</label>
                <input 
                  type="text"
                  placeholder="Add a human note for this account..."
                  className="w-full border-b border-brand-grey py-1 text-sm outline-none focus:border-brand-brown transition-colors bg-transparent italic"
                  value={lead.human_notes || ''}
                  onChange={(e) => handleUpdateNotes(lead.id, lead.account_id, e.target.value)}
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
                    Simulate Engagement (+20)
                  </button>
                </div>
                
                <div className="flex items-center space-x-4 w-full md:w-auto justify-end">
                  {(status[lead.id] || lead.status === 'SENT' || lead.status === 'Active') && (
                    <span className={`text-sm tracking-wide font-medium ${ (status[lead.id]?.includes("Success") || lead.status === 'SENT' || lead.status === 'Active') ? "text-green-700" : "text-red-700"}`}>
                      {status[lead.id] || (lead.status === 'Active' ? 'Active' : 'Completed')}
                    </span>
                  )}
                  
                  <button
                    onClick={() => handleApprove(lead)}
                    disabled={loading === lead.id || !!status[lead.id] || lead.status === 'SENT' || lead.status === 'Active'}
                    className="bg-brand-brown hover:bg-brand-black disabled:bg-brand-grey text-white px-6 py-2 uppercase tracking-wide font-bold transition-colors outline-none focus:ring-2 focus:ring-brand-brown focus:ring-offset-2"
                  >
                    {loading === lead.id ? 'Firing...' : (lead.status === 'SENT' || lead.status === 'Active' ? 'Already Fired' : 'Approve & Fire')}
                  </button>
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
