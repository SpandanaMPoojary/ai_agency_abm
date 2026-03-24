"use client";

import { useState, useEffect } from "react";
import Link from "next/link";

type AccountScore = {
  id: number;
  company_name: string;
  first_name: string;
  industry: string;
  lead_score: number;
  status: string;
  website: string;
};

export default function LeadScoresPage() {
  const [accounts, setAccounts] = useState<AccountScore[]>([]);
  const [loading, setLoading] = useState(true);

  const fetchScores = async () => {
    try {
      const res = await fetch("http://127.0.0.1:8000/api/leads/scores");
      const data = await res.json();
      setAccounts(data.accounts || []);
    } catch (err) {
      console.error("Failed to fetch scores:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchScores();
  }, []);

  return (
    <main className="min-h-screen bg-brand-white font-sans text-brand-black p-8">
      <div className="max-w-6xl mx-auto">
        <header className="flex justify-between items-center mb-12 border-b-2 border-brand-black pb-6">
          <div>
            <h1 className="text-4xl font-black tracking-tighter uppercase italic">
              Lead <span className="text-brand-brown">Scores</span>
            </h1>
            <p className="text-brand-darkgrey font-medium tracking-tight mt-1">
              Top Engaged Accounts & Revenue Opportunities
            </p>
          </div>
          <Link 
            href="/"
            className="bg-brand-black text-white px-6 py-2 uppercase tracking-wide font-bold hover:bg-brand-brown transition-colors"
          >
            &larr; Command Center
          </Link>
        </header>

        {loading ? (
          <div className="text-center py-20">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-brand-brown mx-auto"></div>
            <p className="mt-4 font-bold uppercase tracking-widest text-brand-darkgrey">Loading Rankings...</p>
          </div>
        ) : (
          <div className="bg-white border-2 border-brand-black shadow-[8px_8px_0px_0px_rgba(0,0,0,1)]">
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="bg-brand-black text-white uppercase tracking-widest text-sm">
                  <th className="p-4 border-r border-white/20">Rank</th>
                  <th className="p-4 border-r border-white/20">Name</th>
                  <th className="p-4 border-r border-white/20">Status</th>
                  <th className="p-4 text-center">Engagement Score</th>
                </tr>
              </thead>
              <tbody>
                {accounts.map((acc, index) => (
                  <tr key={acc.id} className="border-b border-brand-grey hover:bg-brand-white transition-colors">
                    <td className="p-4 font-black text-2xl text-brand-brown tabular-nums border-r border-brand-grey">
                      #{index + 1}
                    </td>
                    <td className="p-4 border-r border-brand-grey">
                      <div className="font-bold text-lg">{acc.first_name || acc.company_name}</div>
                      <div className="text-xs text-brand-darkgrey uppercase tracking-tighter">{acc.company_name}</div>
                    </td>
                    <td className="p-4 border-r border-brand-grey">
                      <span className={`px-3 py-1 text-[10px] font-black uppercase tracking-widest rounded-full ${
                        acc.status === 'ENGAGED' ? 'bg-green-100 text-green-800' : 'bg-brand-grey text-brand-darkgrey'
                      }`}>
                        {acc.status}
                      </span>
                    </td>
                    <td className="p-4 text-center">
                      <span className="text-3xl font-black tracking-tighter text-brand-black">
                        {acc.lead_score}
                      </span>
                    </td>
                  </tr>
                ))}
                {accounts.length === 0 && (
                  <tr>
                    <td colSpan={4} className="p-20 text-center font-bold text-brand-darkgrey uppercase tracking-widest">
                      No scored leads found. Fire some campaigns first!
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </main>
  );
}
