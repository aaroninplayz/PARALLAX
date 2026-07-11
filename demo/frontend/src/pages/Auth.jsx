import React, { useState, useEffect } from 'react';
import { Shield, Activity, User, Key, Terminal, Fingerprint } from 'lucide-react';
import './Docs.css';

const API = 'http://localhost:8000';

export default function Auth({ onLogin }) {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const [bootText, setBootText] = useState('');
  const bootSequence = [
    "INITIALIZING SECURE PROTOCOL...",
    "ESTABLISHING ENCRYPTED UPLINK...",
    "VERIFYING NODE IDENTITY...",
    "AWAITING CREDENTIALS..."
  ];

  useEffect(() => {
    let i = 0;
    const interval = setInterval(() => {
      if (i < bootSequence.length) {
        setBootText(prev => prev + bootSequence[i] + '\n');
        i++;
      } else {
        clearInterval(interval);
      }
    }, 300);
    return () => clearInterval(interval);
  }, []);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    try {
      const formData = new URLSearchParams();
      formData.append('username', username);
      formData.append('password', password);

      const res = await fetch(`${API}/auth/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
        body: formData
      });

      const data = await res.json();

      if (!res.ok) {
        throw new Error(data.detail || 'Authentication failed');
      }

      localStorage.setItem('parallax_token', data.access_token);
      onLogin(data.access_token);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{
      minHeight: '100vh',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      background: '#050505',
      fontFamily: '"Space Mono", monospace',
      position: 'relative',
      overflow: 'hidden'
    }}>
      {/* Dynamic Grid Background */}
      <div style={{
        position: 'absolute', inset: 0,
        backgroundImage: `
          linear-gradient(rgba(139, 224, 164, 0.05) 1px, transparent 1px), 
          linear-gradient(90deg, rgba(139, 224, 164, 0.05) 1px, transparent 1px)
        `,
        backgroundSize: '30px 30px',
        backgroundPosition: 'center center',
        zIndex: 0
      }} />

      {/* Scanning Line Effect */}
      <div className="scanner-line" style={{
        position: 'absolute',
        top: 0, left: 0, right: 0, height: '2px',
        background: 'var(--accent)',
        boxShadow: '0 0 20px var(--accent)',
        opacity: 0.5,
        zIndex: 1,
        animation: 'scan 4s linear infinite'
      }} />

      <style>
        {`
          @keyframes scan {
            0% { top: 0; opacity: 0; }
            10% { opacity: 0.5; }
            90% { opacity: 0.5; }
            100% { top: 100%; opacity: 0; }
          }
          .glitch {
            animation: glitch-anim 2s infinite linear alternate-reverse;
          }
          @keyframes glitch-anim {
            0% { clip-path: inset(10% 0 30% 0); }
            20% { clip-path: inset(80% 0 10% 0); }
            40% { clip-path: inset(40% 0 50% 0); }
            60% { clip-path: inset(90% 0 5% 0); }
            80% { clip-path: inset(20% 0 60% 0); }
            100% { clip-path: inset(50% 0 30% 0); }
          }
        `}
      </style>

      <div style={{
        position: 'relative',
        zIndex: 2,
        background: 'rgba(5, 5, 8, 0.85)',
        backdropFilter: 'blur(12px)',
        border: '1px solid rgba(139, 224, 164, 0.2)',
        padding: '3rem',
        width: '100%',
        maxWidth: '480px',
        boxShadow: '0 0 40px rgba(0, 0, 0, 0.8), inset 0 0 30px rgba(139, 224, 164, 0.03)',
      }}>
        
        {/* Terminal Boot Sequence */}
        <div style={{
          background: '#000',
          border: '1px solid rgba(139, 224, 164, 0.3)',
          padding: '1rem',
          marginBottom: '2rem',
          height: '100px',
          overflow: 'hidden',
          display: 'flex',
          flexDirection: 'column',
          justifyContent: 'flex-end',
          boxShadow: 'inset 0 0 10px rgba(139, 224, 164, 0.1)'
        }}>
          <pre style={{ 
            margin: 0, 
            fontSize: '0.65rem', 
            color: 'var(--accent)', 
            whiteSpace: 'pre-wrap',
            textShadow: '0 0 5px var(--accent)',
            opacity: 0.8
          }}>
            {bootText}
            <span style={{ animation: 'blink 1s step-end infinite' }}>_</span>
          </pre>
        </div>

        <div style={{ textAlign: 'center', marginBottom: '2.5rem' }}>
          <Shield size={54} strokeWidth={1} style={{ color: 'var(--accent)', margin: '0 auto', marginBottom: '1rem', filter: 'drop-shadow(0 0 12px var(--accent))' }} />
          <h1 style={{ fontSize: '1.8rem', letterSpacing: '8px', margin: 0, color: '#fff', fontWeight: 700, textShadow: '0 0 10px rgba(255,255,255,0.3)' }}>
            PARALLAX
          </h1>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '0.5rem', marginTop: '0.8rem' }}>
            <Activity size={12} style={{ color: 'var(--danger)' }} />
            <p style={{ fontSize: '0.7rem', color: 'var(--danger)', letterSpacing: '3px', margin: 0, fontWeight: 600 }}>RESTRICTED ACCESS</p>
          </div>
        </div>

        <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
          
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.6rem' }}>
            <label style={{ fontSize: '0.65rem', color: 'var(--accent)', letterSpacing: '2px', display: 'flex', alignItems: 'center', gap: '0.5rem', opacity: 0.8 }}>
              <Terminal size={12} /> OPERATOR ID
            </label>
            <div style={{ position: 'relative' }}>
              <User size={16} style={{ position: 'absolute', left: '1rem', top: '50%', transform: 'translateY(-50%)', color: 'var(--text-muted)' }} />
              <input 
                type="text" 
                value={username}
                onChange={e => setUsername(e.target.value)}
                required
                autoComplete="off"
                spellCheck="false"
                style={{
                  width: '100%',
                  background: 'rgba(0,0,0,0.6)',
                  border: '1px solid rgba(139, 224, 164, 0.2)',
                  padding: '1rem 1rem 1rem 3rem',
                  color: 'var(--accent)',
                  fontFamily: 'inherit',
                  fontSize: '0.9rem',
                  outline: 'none',
                  transition: 'all 0.3s',
                  letterSpacing: '1px'
                }}
                onFocus={e => {
                  e.target.style.borderColor = 'var(--accent)';
                  e.target.style.boxShadow = '0 0 15px rgba(139, 224, 164, 0.1)';
                }}
                onBlur={e => {
                  e.target.style.borderColor = 'rgba(139, 224, 164, 0.2)';
                  e.target.style.boxShadow = 'none';
                }}
              />
            </div>
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.6rem' }}>
            <label style={{ fontSize: '0.65rem', color: 'var(--accent)', letterSpacing: '2px', display: 'flex', alignItems: 'center', gap: '0.5rem', opacity: 0.8 }}>
              <Key size={12} /> DECRYPTION KEY
            </label>
            <div style={{ position: 'relative' }}>
              <Fingerprint size={16} style={{ position: 'absolute', left: '1rem', top: '50%', transform: 'translateY(-50%)', color: 'var(--text-muted)' }} />
              <input 
                type="password" 
                value={password}
                onChange={e => setPassword(e.target.value)}
                required
                style={{
                  width: '100%',
                  background: 'rgba(0,0,0,0.6)',
                  border: '1px solid rgba(139, 224, 164, 0.2)',
                  padding: '1rem 1rem 1rem 3rem',
                  color: 'var(--accent)',
                  fontFamily: 'inherit',
                  fontSize: '0.9rem',
                  outline: 'none',
                  transition: 'all 0.3s',
                  letterSpacing: '4px'
                }}
                onFocus={e => {
                  e.target.style.borderColor = 'var(--accent)';
                  e.target.style.boxShadow = '0 0 15px rgba(139, 224, 164, 0.1)';
                }}
                onBlur={e => {
                  e.target.style.borderColor = 'rgba(139, 224, 164, 0.2)';
                  e.target.style.boxShadow = 'none';
                }}
              />
            </div>
          </div>

          {error && (
            <div style={{ 
              background: 'rgba(239, 68, 68, 0.05)', 
              borderLeft: '2px solid var(--danger)', 
              padding: '0.8rem', 
              color: 'var(--danger)', 
              fontSize: '0.75rem', 
              letterSpacing: '1px',
              display: 'flex',
              alignItems: 'center',
              gap: '0.5rem'
            }}>
              <Activity size={14} className="glitch" />
              ACCESS DENIED: {error}
            </div>
          )}

          <button 
            type="submit" 
            disabled={loading}
            style={{
              background: 'transparent',
              color: 'var(--accent)',
              border: '1px solid var(--accent)',
              padding: '1.2rem',
              fontWeight: 600,
              letterSpacing: '3px',
              cursor: loading ? 'not-allowed' : 'pointer',
              display: 'flex',
              justifyContent: 'center',
              alignItems: 'center',
              gap: '0.8rem',
              marginTop: '1.5rem',
              transition: 'all 0.3s',
              position: 'relative',
              overflow: 'hidden'
            }}
            onMouseOver={e => {
              if(!loading) {
                e.target.style.background = 'var(--accent)';
                e.target.style.color = '#000';
                e.target.style.boxShadow = '0 0 20px var(--accent)';
              }
            }}
            onMouseOut={e => {
              if(!loading) {
                e.target.style.background = 'transparent';
                e.target.style.color = 'var(--accent)';
                e.target.style.boxShadow = 'none';
              }
            }}
          >
            {loading ? <Activity size={18} className="spin" /> : <Shield size={18} />}
            AUTHENTICATE
          </button>
        </form>

        <div style={{ position: 'absolute', bottom: '-25px', right: '0', fontSize: '0.5rem', color: 'rgba(139, 224, 164, 0.2)', fontFamily: 'monospace', letterSpacing: '1px' }}>
          SYS.VER: 4.1.0 // SEC: MIL-SPEC // NODE: PRX-99
        </div>
      </div>
    </div>
  );
}
