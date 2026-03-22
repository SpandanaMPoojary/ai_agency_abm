'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';

export default function Login() {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const router = useRouter();

  const handleLogin = (e: React.FormEvent) => {
    e.preventDefault();
    if (username === 'admin' && password === 'admin') {
      // Very simple local session for mock auth
      sessionStorage.setItem('isAdmin', 'true');
      router.push('/');
    } else {
      setError('Invalid credentials. Use admin / admin');
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-brand-white">
      <div className="bg-white p-8 rounded-sm shadow-md border border-brand-grey w-full max-w-sm">
        <h1 className="text-2xl font-bold text-brand-black mb-6 uppercase text-center">ABM Command Center</h1>
        <form onSubmit={handleLogin} className="space-y-4">
          <div>
            <label className="block text-sm font-semibold text-brand-darkgrey mb-1">Username</label>
            <input 
              type="text" 
              value={username} onChange={e => setUsername(e.target.value)}
              className="w-full p-2 border border-brand-grey outline-none focus:border-brand-brown text-brand-black"
              required
            />
          </div>
          <div>
            <label className="block text-sm font-semibold text-brand-darkgrey mb-1">Password</label>
            <input 
              type="password" 
              value={password} onChange={e => setPassword(e.target.value)}
              className="w-full p-2 border border-brand-grey outline-none focus:border-brand-brown text-brand-black"
              required
            />
          </div>
          {error && <p className="text-red-600 text-sm">{error}</p>}
          <button 
            type="submit"
            className="w-full bg-brand-brown hover:bg-brand-black text-white font-medium py-2 uppercase tracking-wide transition-colors"
          >
            Authenticate
          </button>
        </form>
      </div>
    </div>
  );
}
