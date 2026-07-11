import React, { useState, useEffect, useRef, useCallback } from 'react';
import { BrowserRouter, Routes, Route, Link, useLocation } from 'react-router-dom';
import { Activity, Clock, Settings, Shield } from 'lucide-react';
import Home from './pages/Home';
import Docs from './pages/Docs';
import Auth from './pages/Auth';
import './index.css';

const API = 'http://localhost:8000';

const getToken = () => localStorage.getItem('parallax_token');
const getTokenQuery = () => {
  const token = getToken();
  return token ? `?token=${token}` : '';
};

const apiFetch = async (url, options = {}) => {
  const token = getToken();
  const headers = { ...options.headers };
  if (token) headers['Authorization'] = `Bearer ${token}`;
  
  const res = await fetch(`${API}${url}`, { ...options, headers });
  if (res.status === 401) {
    localStorage.removeItem('parallax_token');
    window.location.reload();
  }
  return res;
};

// ═══════════════════════════════════════════════════════
//  LIVE TAB (Dashboard Component)
// ═══════════════════════════════════════════════════════
function LiveTab() {
  const [isConnected, setIsConnected] = useState(false);
  const [metadata, setMetadata] = useState(null);
  const imgRef = useRef(null);
  const wsRef = useRef(null);

  const connectWebSocket = useCallback(() => {
    if (wsRef.current) return;
    const ws = new WebSocket(`ws://localhost:8000/ws${getTokenQuery()}`);
    ws.onopen = () => setIsConnected(true);
    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        if (data.image && imgRef.current) {
          imgRef.current.src = `data:image/jpeg;base64,${data.image}`;
        }
        if (data.metadata) setMetadata(data.metadata);
      } catch (err) {
        console.error("WS parse error", err);
      }
    };
    ws.onclose = () => { setIsConnected(false); wsRef.current = null; };
    ws.onerror = () => { setIsConnected(false); wsRef.current = null; };
    wsRef.current = ws;
  }, []);

  const disconnectWebSocket = useCallback(() => {
    if (wsRef.current) { wsRef.current.close(); wsRef.current = null; }
    setIsConnected(false);
    setMetadata(null);
    if (imgRef.current) imgRef.current.src = "";
  }, []);

  const startEngine = async () => {
    try {
      await apiFetch(`/start-processing`, { method: 'POST' });
      connectWebSocket();
    } catch (err) { console.error("Start failed:", err); }
  };

  const stopEngine = async () => {
    try {
      await apiFetch(`/stop-processing`, { method: 'POST' });
      disconnectWebSocket();
    } catch (err) { console.error("Stop failed:", err); }
  };

  useEffect(() => {
    return () => disconnectWebSocket();
  }, [disconnectWebSocket]);

  return (
    <div className="live-tab" style={{ display: 'flex', flexDirection: 'column', gap: '2rem', alignItems: 'center' }}>
      <div className={`video-container glass-panel ${metadata?.is_anomalous ? 'anomaly-detected' : ''}`} style={{ position: 'relative', width: '100%', maxWidth: '1000px', aspectRatio: '16/9', overflow: 'hidden' }}>
        <img ref={imgRef} alt="" style={{ width: '100%', height: '100%', objectFit: 'cover' }} />
        {!isConnected && (
          <div style={{ position: 'absolute', inset: 0, display: 'flex', flexDirection: 'column', justifyContent: 'center', alignItems: 'center', color: 'var(--text-dim)' }}>
            <Activity size={48} style={{ opacity: 0.3, marginBottom: '1rem' }} />
            <p>AWAITING SIGNAL</p>
          </div>
        )}

        {isConnected && metadata && (
          <div style={{ position: 'absolute', bottom: 0, left: 0, width: '100%', padding: '1.5rem', background: 'linear-gradient(to top, rgba(0,0,0,0.8), transparent)', display: 'flex', gap: '2rem', alignItems: 'flex-end' }}>
            <div style={{ display: 'flex', flexDirection: 'column' }}>
              <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)', fontWeight: 'bold' }}>LOSS</span>
              <span style={{ fontSize: '1.2rem' }}>{(metadata.score || 0).toFixed(4)}</span>
            </div>
            <div style={{ display: 'flex', flexDirection: 'column' }}>
              <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)', fontWeight: 'bold' }}>FPS</span>
              <span style={{ fontSize: '1.2rem' }}>{metadata.fps || 0}</span>
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', marginLeft: 'auto', alignItems: 'flex-end' }}>
              <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)', fontWeight: 'bold' }}>STATUS</span>
              <span style={{ fontSize: '1.2rem', color: metadata.warming_up ? '#f59e0b' : (metadata.is_anomalous ? 'var(--danger)' : 'var(--success)'), fontWeight: 'bold' }}>
                {metadata.warming_up ? 'CALIBRATING...' : (metadata.is_anomalous ? 'ANOMALY DETECTED' : 'SECURE')}
              </span>
            </div>
          </div>
        )}

        {isConnected && metadata?.is_anomalous && !metadata?.warming_up && (
          <div className="glass-panel" style={{ position: 'absolute', bottom: '100px', right: '1.5rem', padding: '1rem', display: 'flex', flexDirection: 'column', gap: '0.5rem', maxWidth: '200px' }}>
            {metadata.patch_image && (
              <img src={`data:image/jpeg;base64,${metadata.patch_image}`} alt="anomaly" style={{ width: '100%', borderRadius: 'var(--radius-sm)' }} />
            )}
            <button className="neo-button" style={{ fontSize: '0.8rem', padding: '0.5rem' }} onClick={() => apiFetch(`/feedback`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ label: 'false_positive' }) })}>
              ✓ False Positive
            </button>
            <button className="neo-button" style={{ fontSize: '0.8rem', padding: '0.5rem', color: 'var(--danger)' }} onClick={() => apiFetch(`/feedback`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ label: 'true_anomaly' }) })}>
              ⚠ True Anomaly
            </button>
          </div>
        )}
      </div>

      <div style={{ display: 'flex', gap: '1rem' }}>
        <button className="neo-button primary" onClick={startEngine} disabled={isConnected} style={{ opacity: isConnected ? 0.5 : 1 }}>
          <Activity size={18} /> INITIALIZE SYSTEM
        </button>
        <button className="neo-button" onClick={stopEngine} disabled={!isConnected} style={{ opacity: !isConnected ? 0.5 : 1 }}>
          HALT OPERATIONS
        </button>
      </div>
    </div>
  );
}

// ═══════════════════════════════════════════════════════
//  CUSTOM VIDEO PLAYER (Minimalist)
// ═══════════════════════════════════════════════════════
function MinimalPlayer({ src, downloadName }) {
  const videoRef = useRef(null);
  const containerRef = useRef(null);
  const [playing, setPlaying] = useState(false);
  const [progress, setProgress] = useState(0);
  const [duration, setDuration] = useState(0);

  const togglePlay = (e) => {
    if (e) e.preventDefault();
    if (!videoRef.current) return;
    if (playing) { videoRef.current.pause(); }
    else { videoRef.current.play(); }
    setPlaying(!playing);
  };

  const skipForward = (e) => {
    if (e) e.preventDefault();
    if (!videoRef.current) return;
    videoRef.current.currentTime = Math.min(videoRef.current.currentTime + 10, duration);
  };

  const skipBackward = (e) => {
    if (e) e.preventDefault();
    if (!videoRef.current) return;
    videoRef.current.currentTime = Math.max(videoRef.current.currentTime - 10, 0);
  };

  const toggleFullScreen = (e) => {
    if (e) e.preventDefault();
    if (!containerRef.current) return;
    if (!document.fullscreenElement) {
      containerRef.current.requestFullscreen().catch(err => {
        console.error(`Error attempting to enable fullscreen: ${err.message}`);
      });
    } else {
      document.exitFullscreen();
    }
  };

  const onTimeUpdate = () => {
    if (!videoRef.current) return;
    setProgress(videoRef.current.currentTime);
  };

  const onLoadedMetadata = () => {
    if (!videoRef.current) return;
    setDuration(videoRef.current.duration);
  };

  const seek = (e) => {
    e.preventDefault();
    if (!videoRef.current || !duration) return;
    const rect = e.currentTarget.getBoundingClientRect();
    const ratio = (e.clientX - rect.left) / rect.width;
    videoRef.current.currentTime = ratio * duration;
  };

  const formatTime = (t) => {
    if (!t || isNaN(t)) return '0:00';
    const m = Math.floor(t / 60);
    const s = Math.floor(t % 60);
    return `${m}:${s.toString().padStart(2, '0')}`;
  };

  const btnStyle = {
    background: 'none', border: 'none', color: 'var(--text-main)',
    cursor: 'pointer', fontSize: '1.1rem', padding: '0 4px', lineHeight: 1,
    display: 'flex', alignItems: 'center', justifyContent: 'center'
  };

  return (
    <div ref={containerRef} style={{ borderRadius: 'var(--radius-sm)', overflow: 'hidden', background: '#000', position: 'relative', display: 'flex', flexDirection: 'column' }}>
      <video
        ref={videoRef}
        src={src}
        onTimeUpdate={onTimeUpdate}
        onLoadedMetadata={onLoadedMetadata}
        onEnded={() => setPlaying(false)}
        onClick={togglePlay}
        style={{ width: '100%', maxHeight: '80vh', display: 'block', cursor: 'pointer', objectFit: 'contain' }}
      />
      {/* Controls overlay */}
      <div style={{
        display: 'flex', alignItems: 'center', gap: '0.75rem',
        padding: '0.6rem 1rem', background: 'rgba(0,0,0,0.85)',
        borderTop: '1px solid rgba(255,255,255,0.05)'
      }}>
        <button type="button" onClick={skipBackward} style={btnStyle} title="Skip backward 10s">↺</button>
        <button type="button" onClick={togglePlay} style={{...btnStyle, width: '20px'}} title={playing ? 'Pause' : 'Play'}>
          {playing ? '⏸' : '▶'}
        </button>
        <button type="button" onClick={skipForward} style={btnStyle} title="Skip forward 10s">↻</button>

        {/* Time */}
        <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)', fontFamily: 'monospace', minWidth: '70px', textAlign: 'center' }}>
          {formatTime(progress)} / {formatTime(duration)}
        </span>

        {/* Progress bar */}
        <div
          onClick={seek}
          style={{
            flex: 1, height: '6px', background: 'rgba(255,255,255,0.2)',
            borderRadius: '3px', cursor: 'pointer', position: 'relative'
          }}
        >
          <div style={{
            width: duration ? `${(progress / duration) * 100}%` : '0%',
            height: '100%', background: 'var(--accent)', borderRadius: '3px',
            transition: 'width 0.1s linear'
          }} />
        </div>

        {/* Fullscreen */}
        <button type="button" onClick={toggleFullScreen} style={btnStyle} title="Full Screen">⛶</button>

        {/* Download */}
        <a href={src} download={downloadName || 'clip.mp4'} style={{
          color: 'var(--text-muted)', textDecoration: 'none', fontSize: '1.1rem',
          padding: '0 4px', transition: 'var(--transition)'
        }} title="Download clip">
          ⬇
        </a>
      </div>
    </div>
  );
}

// ═══════════════════════════════════════════════════════
//  RECORDS TAB (Redesigned)
// ═══════════════════════════════════════════════════════
function RecordsTab() {
  const [sessions, setSessions] = useState([]);
  const [selectedSession, setSelectedSession] = useState(null);
  const [sessionDetail, setSessionDetail] = useState(null);
  const [filteredAnomalies, setFilteredAnomalies] = useState([]);
  const [activeSubTab, setActiveSubTab] = useState('sessions'); // 'sessions' or 'filtered'
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchSessions();
    const interval = setInterval(fetchSessions, 10000);
    return () => clearInterval(interval);
  }, []);

  const fetchSessions = async () => {
    try {
      const res = await apiFetch(`/sessions`);
      const data = await res.json();
      setSessions(data.sessions || []);
    } catch (err) { console.error("Failed to load sessions", err); }
    setLoading(false);
  };

  const fetchFiltered = async () => {
    try {
      const res = await apiFetch(`/filtered-anomalies`);
      const data = await res.json();
      setFilteredAnomalies(data.anomalies || []);
    } catch (err) { console.error("Failed to load filtered", err); }
  };

  const loadSession = async (sessionId) => {
    setSelectedSession(sessionId);
    try {
      const res = await apiFetch(`/sessions/${sessionId}`);
      const data = await res.json();
      setSessionDetail(data);
    } catch (err) { console.error("Failed to load session detail", err); }
  };

  const updateAnomalyStatus = async (sessionId, anomalyId, status) => {
    try {
      await apiFetch(`/anomalies/${sessionId}/${anomalyId}/status`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ status })
      });
      if (activeSubTab === 'sessions') loadSession(sessionId);
      else fetchFiltered();
    } catch (err) { console.error("Failed to update status", err); }
  };

  const deleteAnomaly = async (sessionId, anomalyId) => {
    try {
      await apiFetch(`/anomalies/${sessionId}/${anomalyId}`, { method: 'DELETE' });
      if (activeSubTab === 'sessions') loadSession(sessionId);
      else fetchFiltered();
    } catch (err) { console.error("Failed to delete anomaly", err); }
  };

  const purgeAllFiltered = async () => {
    if (!window.confirm('Permanently delete ALL filtered (false positive) data across all sessions?')) return;
    try {
      const res = await apiFetch(`/filtered-anomalies/purge`, { method: 'DELETE' });
      const data = await res.json();
      console.log(`Purged ${data.deleted_count} items`);
      setFilteredAnomalies([]);
    } catch (err) { console.error("Purge failed", err); }
  };

  // Switch to filtered tab: load data
  useEffect(() => {
    if (activeSubTab === 'filtered') fetchFiltered();
  }, [activeSubTab]);

  if (loading) {
    return <div style={{ display: 'flex', justifyContent: 'center', minHeight: '40vh', alignItems: 'center', color: 'var(--text-dim)' }}>Loading sessions...</div>;
  }

  const sessionAnomalies = (sessionDetail?.anomalies || []).filter(a => a.status !== 'false_positive');

  // ── Anomaly Card Component ──
  const AnomalyCard = ({ a, showSession, canRestore }) => (
    <div style={{
      background: 'var(--bg-surface)', border: '1px solid var(--border)',
      borderRadius: 'var(--radius-sm)', overflow: 'hidden'
    }}>
      {/* Header row */}
      <div style={{ padding: '1rem', display: 'flex', justifyContent: 'space-between', alignItems: 'center', borderBottom: '1px solid var(--border)' }}>
        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.2rem' }}>
          {showSession && <span style={{ fontSize: '0.7rem', color: 'var(--text-dim)', letterSpacing: '1px' }}>SESSION: {a.session_id}</span>}
          <span style={{ fontWeight: 600, fontSize: '0.95rem' }}>{a.start_time_human}</span>
          <span style={{ color: 'var(--danger)', fontSize: '0.8rem', fontFamily: 'monospace' }}>
            Score: {a.peak_score?.toFixed(4)} | {a.duration_seconds?.toFixed(1)}s | {a.frame_count} frames
          </span>
        </div>
      </div>

      {/* Content: Photo + Video side by side */}
      <div style={{ display: 'flex', gap: '1px', background: 'var(--border)' }}>
        {/* Thumbnail */}
        <div style={{ flex: '0 0 40%', background: '#000', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
          <img
            src={`${API}/anomalies/${a.session_id}/${a.anomaly_id}/thumbnail${getTokenQuery()}`}
            alt="Detected object"
            style={{ width: '100%', height: '200px', objectFit: 'cover' }}
          />
        </div>
        {/* Video */}
        <div style={{ flex: 1 }}>
          <MinimalPlayer
            src={`${API}/anomalies/${a.session_id}/${a.anomaly_id}/clip${getTokenQuery()}`}
            downloadName={`${a.anomaly_id}.webm`}
          />
        </div>
      </div>

      {/* Actions */}
      <div style={{ padding: '0.75rem 1rem', display: 'flex', gap: '0.75rem', justifyContent: 'flex-end', borderTop: '1px solid var(--border)' }}>
        {!canRestore && (
          <button className="neo-button" style={{ fontSize: '0.8rem', padding: '0.4rem 1rem' }}
            onClick={() => updateAnomalyStatus(a.session_id, a.anomaly_id, 'false_positive')}>
            Mark as False Positive
          </button>
        )}
        {canRestore && (
          <>
            <button className="neo-button" style={{ fontSize: '0.8rem', padding: '0.4rem 1rem' }}
              onClick={() => updateAnomalyStatus(a.session_id, a.anomaly_id, 'anomaly')}>
              Restore to History
            </button>
            <button className="neo-button" style={{ fontSize: '0.8rem', padding: '0.4rem 1rem', border: '1px solid var(--danger)', color: 'var(--danger)' }}
              onClick={() => deleteAnomaly(a.session_id, a.anomaly_id)}>
              Delete
            </button>
          </>
        )}
      </div>
    </div>
  );

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
      {/* Top-level sub-tabs */}
      <div style={{ display: 'flex', gap: '1rem', justifyContent: 'center' }}>
        <button
          className={`neo-button ${activeSubTab === 'sessions' ? 'primary' : ''}`}
          onClick={() => setActiveSubTab('sessions')}
          style={{ padding: '0.6rem 1.5rem', fontSize: '0.9rem' }}
        >
          Sessions
        </button>
        <button
          className={`neo-button ${activeSubTab === 'filtered' ? 'primary' : ''}`}
          onClick={() => setActiveSubTab('filtered')}
          style={{ padding: '0.6rem 1.5rem', fontSize: '0.9rem' }}
        >
          Filtered Data
        </button>
      </div>

      {/* ── SESSIONS TAB ── */}
      {activeSubTab === 'sessions' && (
        <div style={{ display: 'flex', gap: '1.5rem', minHeight: '60vh' }}>
          {/* Sidebar */}
          <div className="glass-panel" style={{ width: '300px', padding: '1.5rem', display: 'flex', flexDirection: 'column', gap: '1rem', overflowY: 'auto', maxHeight: '70vh' }}>
            <h3 style={{ fontSize: '0.8rem', color: 'var(--text-muted)', letterSpacing: '2px' }}>SESSIONS</h3>
            {sessions.length === 0 && <p style={{ color: 'var(--text-dim)' }}>No recorded sessions yet.</p>}
            {sessions.map((s) => (
              <div
                key={s.session_id}
                onClick={() => loadSession(s.session_id)}
                style={{
                  padding: '1rem', background: selectedSession === s.session_id ? 'var(--accent-dim)' : 'var(--bg-surface)',
                  border: selectedSession === s.session_id ? '1px solid var(--accent)' : '1px solid var(--border)',
                  borderRadius: 'var(--radius-sm)', cursor: 'pointer', transition: 'var(--transition)'
                }}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.5rem' }}>
                  <span style={{ fontWeight: 600 }}>{s.start_time_human || s.session_id}</span>
                  {s.status === 'active' && <span style={{ fontSize: '0.6rem', background: 'rgba(139, 224, 164, 0.2)', color: 'var(--success)', padding: '2px 6px', borderRadius: '50px' }}>LIVE</span>}
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.8rem', color: 'var(--text-muted)' }}>
                  <span>{s.anomaly_count || 0} anomalies</span>
                  {s.duration_seconds && <span>{Math.round(s.duration_seconds / 60)}m</span>}
                </div>
              </div>
            ))}
          </div>

          {/* Main Panel */}
          <div className="glass-panel" style={{ flex: 1, padding: '2rem', display: 'flex', flexDirection: 'column', gap: '1.5rem', overflowY: 'auto', maxHeight: '70vh' }}>
            {!selectedSession && (
              <div style={{ flex: 1, display: 'flex', justifyContent: 'center', alignItems: 'center', color: 'var(--text-dim)' }}>
                <p>Select a session to view records</p>
              </div>
            )}

            {selectedSession && sessionDetail && (
              <>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', borderBottom: '1px solid var(--border)', paddingBottom: '1rem' }}>
                  <h3 style={{ fontSize: '1.2rem', fontWeight: 600 }}>Session: {sessionDetail.start_time_human || selectedSession}</h3>
                  {sessionDetail.has_video && (
                    <a href={`${API}/sessions/${selectedSession}/video${getTokenQuery()}`} className="neo-button" download>
                      ⬇ Full Session Video
                    </a>
                  )}
                </div>

                {sessionAnomalies.length === 0 && (
                  <p style={{ color: 'var(--text-dim)', textAlign: 'center', marginTop: '2rem' }}>No anomalies detected in this session.</p>
                )}

                <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
                  {sessionAnomalies.map((a) => (
                    <AnomalyCard key={a.anomaly_id} a={a} showSession={false} canRestore={false} />
                  ))}
                </div>
              </>
            )}
          </div>
        </div>
      )}

      {/* ── FILTERED DATA TAB ── */}
      {activeSubTab === 'filtered' && (
        <div className="glass-panel" style={{ padding: '2rem', display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', borderBottom: '1px solid var(--border)', paddingBottom: '1rem' }}>
            <div>
              <h3 style={{ fontSize: '1.2rem', fontWeight: 600 }}>Filtered Data (False Positives)</h3>
              <p style={{ color: 'var(--text-muted)', fontSize: '0.85rem', marginTop: '0.3rem' }}>{filteredAnomalies.length} items across all sessions</p>
            </div>
            {filteredAnomalies.length > 0 && (
              <button
                className="neo-button"
                style={{ border: '1px solid var(--danger)', color: 'var(--danger)', padding: '0.6rem 1.2rem' }}
                onClick={purgeAllFiltered}
              >
                Purge All
              </button>
            )}
          </div>

          {filteredAnomalies.length === 0 && (
            <p style={{ color: 'var(--text-dim)', textAlign: 'center', marginTop: '2rem' }}>No filtered data. All clear.</p>
          )}

          <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem', overflowY: 'auto', maxHeight: '60vh' }}>
            {filteredAnomalies.map((a) => (
              <AnomalyCard key={`${a.session_id}_${a.anomaly_id}`} a={a} showSession={true} canRestore={true} />
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

// ═══════════════════════════════════════════════════════
//  SETTINGS TAB (Glassmorphic)
// ═══════════════════════════════════════════════════════
function SettingsTab() {
  const [retention, setRetention] = useState(30);
  const [saved, setSaved] = useState(false);
  const [cleanupMsg, setCleanupMsg] = useState('');
  const [preAnomaly, setPreAnomaly] = useState(10);
  const [postAnomaly, setPostAnomaly] = useState(15);
  const [recordFullSessions, setRecordFullSessions] = useState(false);
  const [timingSaved, setTimingSaved] = useState(false);

  // Autoencoder state
  const [calibDelay, setCalibDelay] = useState(5);
  const [calibDuration, setCalibDuration] = useState(10);
  const [autoRecalibrate, setAutoRecalibrate] = useState(0);
  const [aeSaved, setAeSaved] = useState(false);

  const [cameraSource, setCameraSource] = useState('built_in');
  const [externalConnected, setExternalConnected] = useState(false);
  const [cameraSaved, setCameraSaved] = useState(false);

  useEffect(() => {
    apiFetch(`/config/retention`).then(r => r.json()).then(d => setRetention(d.retention_days)).catch(() => {});
    apiFetch(`/config/recording`).then(r => r.json()).then(d => {
      if (d.ring_buffer_seconds !== undefined) setPreAnomaly(d.ring_buffer_seconds);
      if (d.post_anomaly_seconds !== undefined) setPostAnomaly(d.post_anomaly_seconds);
      if (d.record_full_sessions !== undefined) setRecordFullSessions(d.record_full_sessions);
    }).catch(() => {});
    apiFetch(`/config/autoencoder`).then(r => r.json()).then(d => {
      if (d.calibration_delay_seconds !== undefined) setCalibDelay(d.calibration_delay_seconds);
      if (d.calibration_duration_seconds !== undefined) setCalibDuration(d.calibration_duration_seconds);
      if (d.auto_recalibrate_minutes !== undefined) setAutoRecalibrate(d.auto_recalibrate_minutes);
    }).catch(() => {});
    apiFetch(`/config/camera-source`).then(r => r.json()).then(d => {
      setCameraSource(d.source);
      setExternalConnected(d.external_connected);
    }).catch(() => {});
  }, []);

  // Poll external camera connection status
  useEffect(() => {
    if (cameraSource !== 'external') return;
    const interval = setInterval(() => {
      apiFetch(`/config/camera-source`).then(r => r.json()).then(d => {
        setExternalConnected(d.external_connected);
      }).catch(() => {});
    }, 3000);
    return () => clearInterval(interval);
  }, [cameraSource]);

  const saveRetention = async () => {
    try {
      await apiFetch(`/config/retention/${retention}`, { method: 'POST' });
      setSaved(true);
      setTimeout(() => setSaved(false), 2000);
    } catch (err) { console.error(err); }
  };

  const saveTimings = async () => {
    try {
      await apiFetch(`/config/recording`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ 
          ring_buffer_seconds: preAnomaly, 
          post_anomaly_seconds: postAnomaly,
          record_full_sessions: recordFullSessions
        })
      });
      setTimingSaved(true);
      setTimeout(() => setTimingSaved(false), 2000);
    } catch (err) { console.error(err); }
  };

  const saveAutoencoder = async () => {
    try {
      await apiFetch(`/config/autoencoder`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ 
          calibration_delay_seconds: calibDelay, 
          calibration_duration_seconds: calibDuration,
          auto_recalibrate_minutes: autoRecalibrate
        })
      });
      setAeSaved(true);
      setTimeout(() => setAeSaved(false), 2000);
    } catch (err) { console.error(err); }
  };

  const toggleCameraSource = async (source) => {
    try {
      await apiFetch(`/config/camera-source`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ source })
      });
      setCameraSource(source);
      setCameraSaved(true);
      setTimeout(() => setCameraSaved(false), 2000);
    } catch (err) { console.error(err); }
  };

  const runCleanup = async () => {
    setCleanupMsg('Running...');
    try {
      const res = await apiFetch(`/cleanup/run`, { method: 'POST' });
      const data = await res.json();
      setCleanupMsg(`✓ Cleanup completed (retention: ${data.retention_days} days)`);
    } catch (err) { setCleanupMsg('✗ Cleanup failed'); }
    setTimeout(() => setCleanupMsg(''), 4000);
  };

  const inputStyle = {
    width: '80px', padding: '0.5rem', background: 'var(--bg-surface)',
    border: '1px solid var(--border)', color: 'var(--text-main)',
    borderRadius: 'var(--radius-xs)', textAlign: 'center'
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem', maxWidth: '640px', margin: '0 auto' }}>
      {/* Camera Source */}
      <div className="glass-panel" style={{ padding: '2rem', display: 'flex', flexDirection: 'column', gap: '1rem' }}>
        <h3 style={{ fontSize: '1.1rem', fontWeight: 600 }}>Camera Source</h3>
        <p style={{ color: 'var(--text-muted)' }}>Choose between the built-in webcam or an external camera streamed from a phone/tablet.</p>
        
        <div style={{ display: 'flex', gap: '0.75rem' }}>
          <button
            className={`neo-button ${cameraSource === 'built_in' ? 'primary' : ''}`}
            onClick={() => toggleCameraSource('built_in')}
            style={{ padding: '0.6rem 1.2rem', fontSize: '0.85rem' }}
          >
            🖥️ Built-in Webcam
          </button>
          <button
            className={`neo-button ${cameraSource === 'external' ? 'primary' : ''}`}
            onClick={() => toggleCameraSource('external')}
            style={{ padding: '0.6rem 1.2rem', fontSize: '0.85rem' }}
          >
            📱 External Camera
          </button>
        </div>

        {cameraSaved && (
          <p style={{ color: 'var(--success)', fontSize: '0.85rem' }}>
            ✓ Camera source updated. Stop and restart the engine to apply.
          </p>
        )}

        {cameraSource === 'external' && (
          <div style={{ 
            background: 'var(--bg-surface)', border: '1px solid var(--border)', 
            borderRadius: 'var(--radius-sm)', padding: '1.25rem', 
            display: 'flex', flexDirection: 'column', gap: '0.75rem', marginTop: '0.5rem' 
          }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              <span style={{ 
                width: '8px', height: '8px', borderRadius: '50%', display: 'inline-block',
                background: externalConnected ? 'var(--success)' : 'var(--text-dim)',
                boxShadow: externalConnected ? '0 0 8px var(--success)' : 'none'
              }} />
              <span style={{ fontSize: '0.85rem', color: externalConnected ? 'var(--success)' : 'var(--text-muted)' }}>
                {externalConnected ? 'Remote camera connected' : 'Waiting for remote camera...'}
              </span>
            </div>

            <div style={{ fontSize: '0.82rem', color: 'var(--text-muted)', lineHeight: '1.7' }}>
              <strong style={{ color: 'var(--accent)', display: 'block', marginBottom: '0.3rem' }}>Setup Instructions:</strong>
              <ol style={{ marginLeft: '1.2rem' }}>
                <li>Deploy the <code style={{ color: 'var(--accent)' }}>remote-camera</code> folder to Vercel/Netlify</li>
                <li>Open the deployed URL on your phone</li>
                <li>Enter the backend URL: <code style={{ 
                  color: 'var(--accent)', background: 'rgba(168, 177, 255, 0.1)', 
                  padding: '2px 6px', borderRadius: '4px', userSelect: 'all' 
                }}>http://{window.location.hostname}:8000</code></li>
                <li>Tap <strong>Start Streaming</strong> on the phone</li>
                <li>Stop and restart the PARALLAX engine above</li>
              </ol>
            </div>
          </div>
        )}
      </div>

      {/* Recording Settings */}
      <div className="glass-panel" style={{ padding: '2rem', display: 'flex', flexDirection: 'column', gap: '1rem' }}>
        <h3 style={{ fontSize: '1.1rem', fontWeight: 600 }}>Recording Settings</h3>
        <p style={{ color: 'var(--text-muted)' }}>Control anomaly clip buffers and full session recording behavior.</p>
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1.2rem' }}>
          
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.8rem' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
              <label style={{ color: 'var(--text-muted)', minWidth: '180px' }}>Pre-Anomaly (seconds)</label>
              <input type="number" min="1" max="60" value={preAnomaly} onChange={(e) => setPreAnomaly(parseInt(e.target.value) || 1)} style={inputStyle} />
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
              <label style={{ color: 'var(--text-muted)', minWidth: '180px' }}>Post-Anomaly (seconds)</label>
              <input type="number" min="1" max="60" value={postAnomaly} onChange={(e) => setPostAnomaly(parseInt(e.target.value) || 1)} style={inputStyle} />
            </div>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '1rem', borderTop: '1px solid var(--border)', paddingTop: '1rem' }}>
            <label style={{ color: 'var(--text-muted)', minWidth: '220px', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              <input 
                type="checkbox" 
                checked={recordFullSessions} 
                onChange={(e) => setRecordFullSessions(e.target.checked)} 
                style={{ width: '18px', height: '18px', accentColor: 'var(--accent)' }}
              />
              Save empty sessions continuously
            </label>
          </div>

          <button className="neo-button primary" onClick={saveTimings} style={{ alignSelf: 'flex-start', marginTop: '0.5rem' }}>
            {timingSaved ? '✓ Saved' : 'Save Recording Settings'}
          </button>
        </div>
      </div>

      {/* Autoencoder Settings */}
      <div className="glass-panel" style={{ padding: '2rem', display: 'flex', flexDirection: 'column', gap: '1rem' }}>
        <h3 style={{ fontSize: '1.1rem', fontWeight: 600 }}>Autoencoder Neural Settings</h3>
        <p style={{ color: 'var(--text-muted)' }}>Configure how the anomaly engine calibrates to the environment.</p>
        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.8rem' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
            <label style={{ color: 'var(--text-muted)', minWidth: '220px' }}>Calibration Delay (seconds)</label>
            <input type="number" min="0" max="60" value={calibDelay} onChange={(e) => setCalibDelay(parseInt(e.target.value) || 0)} style={inputStyle} />
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
            <label style={{ color: 'var(--text-muted)', minWidth: '220px' }}>Calibration Duration (seconds)</label>
            <input type="number" min="1" max="60" value={calibDuration} onChange={(e) => setCalibDuration(parseInt(e.target.value) || 1)} style={inputStyle} />
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
            <label style={{ color: 'var(--text-muted)', minWidth: '220px' }}>Auto-Recalibrate Interval (minutes)</label>
            <input type="number" min="0" max="1440" value={autoRecalibrate} onChange={(e) => setAutoRecalibrate(parseInt(e.target.value) || 0)} style={inputStyle} />
          </div>
          <span style={{ fontSize: '0.75rem', color: 'var(--text-dim)', marginTop: '-0.3rem', marginBottom: '0.5rem' }}>Set interval to 0 to disable automatic recalibration.</span>
          <button className="neo-button primary" onClick={saveAutoencoder} style={{ alignSelf: 'flex-start' }}>
            {aeSaved ? '✓ Saved' : 'Save Autoencoder Settings'}
          </button>
        </div>
      </div>

      {/* Data Retention */}
      <div className="glass-panel" style={{ padding: '2rem', display: 'flex', flexDirection: 'column', gap: '1rem' }}>
        <h3 style={{ fontSize: '1.1rem', fontWeight: 600 }}>Data Retention</h3>
        <p style={{ color: 'var(--text-muted)' }}>Anomaly clips and session videos older than this will be automatically deleted.</p>
        <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
          <label style={{ color: 'var(--text-muted)' }}>Retention Period (days)</label>
          <input type="number" min="1" max="365" value={retention} onChange={(e) => setRetention(parseInt(e.target.value) || 1)} style={inputStyle} />
          <button className="neo-button primary" onClick={saveRetention}>{saved ? '✓ Saved' : 'Save'}</button>
        </div>
      </div>

      {/* Manual Cleanup */}
      <div className="glass-panel" style={{ padding: '2rem', display: 'flex', flexDirection: 'column', gap: '1rem' }}>
        <h3 style={{ fontSize: '1.1rem', fontWeight: 600 }}>Manual Cleanup</h3>
        <p style={{ color: 'var(--text-muted)' }}>Immediately purge expired sessions based on the current retention policy.</p>
        <button className="neo-button" style={{ border: '1px solid var(--danger)', color: 'var(--danger)' }} onClick={runCleanup}>Run Cleanup Now</button>
        {cleanupMsg && <p style={{ color: 'var(--success)' }}>{cleanupMsg}</p>}
      </div>
    </div>
  );
}

// ═══════════════════════════════════════════════════════
//  DASHBOARD LAYOUT (Wraps Live, History, Settings)
// ═══════════════════════════════════════════════════════
function DashboardLayout() {
  const [activeTab, setActiveTab] = useState('live');
  const [token, setToken] = useState(getToken());

  if (!token) {
    return <Auth onLogin={setToken} />;
  }

  return (
    <div style={{ width: '100%' }}>
      <div style={{ display: 'flex', gap: '1rem', marginBottom: '2rem', justifyContent: 'center' }}>
        {['live', 'records', 'settings'].map((tab) => (
          <button
            key={tab}
            className={`neo-button ${activeTab === tab ? 'primary' : ''}`}
            onClick={() => setActiveTab(tab)}
            style={{ padding: '0.5rem 1.5rem' }}
          >
            {tab.toUpperCase()}
          </button>
        ))}
      </div>
      
      {activeTab === 'live' && <LiveTab />}
      {activeTab === 'records' && <RecordsTab />}
      {activeTab === 'settings' && <SettingsTab />}
    </div>
  );
}

// ═══════════════════════════════════════════════════════
//  MAIN NAVIGATION & ROUTING
// ═══════════════════════════════════════════════════════
function AppContent() {
  const location = useLocation();
  const token = getToken();

  return (
    <div className="app-container">
      <header className="top-nav">
        <Link to="/" className="logo" style={{ display: 'flex', alignItems: 'center', gap: '10px', textDecoration: 'none' }}>
          <img src="/Untitled-1.png" alt="Logo" style={{ height: '32px', width: 'auto' }} />
          <span style={{ fontWeight: 'bold', fontSize: '1.2rem', letterSpacing: '2px', color: 'var(--text-main)' }}>PARALLAX</span>
        </Link>
        <nav className="nav-links" style={{ display: 'flex', alignItems: 'center', gap: '2rem' }}>
          <Link to="/" className={`nav-link ${location.pathname === '/' ? 'active' : ''}`}>Home</Link>
          <Link to="/docs" className={`nav-link ${location.pathname === '/docs' ? 'active' : ''}`}>Documentation</Link>
          <Link to="/dashboard" className={`nav-link ${location.pathname.startsWith('/dashboard') ? 'active' : ''}`}>Dashboard</Link>
          {token && (
            <button 
              onClick={() => { localStorage.removeItem('parallax_token'); window.location.href = '/dashboard'; }}
              style={{ background: 'none', border: '1px solid var(--danger)', color: 'var(--danger)', padding: '0.3rem 0.8rem', borderRadius: '4px', cursor: 'pointer', fontSize: '0.8rem' }}
            >
              LOGOUT
            </button>
          )}
        </nav>
      </header>

      <main className="main-content">
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/docs" element={<Docs />} />
          <Route path="/dashboard/*" element={<DashboardLayout />} />
        </Routes>
      </main>
    </div>
  );
}

export default function App() {
  return (
    <BrowserRouter>
      <AppContent />
    </BrowserRouter>
  );
}
