import React from 'react';
import { motion } from 'framer-motion';
import { Database, Zap, ShieldAlert, Cpu, Eye, Radio, Thermometer } from 'lucide-react';
import './Docs.css';
import ParticleBackground from '../components/ParticleBackground';

export default function Docs() {
  const containerVariants = {
    hidden: { opacity: 0 },
    visible: { opacity: 1, transition: { staggerChildren: 0.15 } }
  };

  const itemVariants = {
    hidden: { opacity: 0, y: 30 },
    visible: { opacity: 1, y: 0, transition: { duration: 0.6, ease: "easeOut" } }
  };

  return (
    <div className="docs-container">
      <ParticleBackground />
      <motion.div 
        className="docs-header"
        initial={{ opacity: 0, y: -20 }}
        animate={{ opacity: 1, y: 0 }}
      >
        <h1 className="hero-title text-gradient" style={{ textAlign: 'center' }}>PARALLAX</h1>
        <p className="hero-subtitle" style={{ textAlign: 'center', margin: '0 auto' }}>
          "Is something present that statistically should not be there?"
        </p>
      </motion.div>

      <motion.div 
        variants={containerVariants}
        initial="hidden"
        animate="visible"
        className="docs-grid"
      >
        {/* Core Concept */}
        <motion.div className="doc-card glass-panel stage-card" variants={itemVariants}>
          <div className="card-icon"><ShieldAlert size={32} /></div>
          <h2>Core Concept</h2>
          <p>
            Modern defense systems ask: <em>"Can I see the object?"</em> PARALLAX changes the question to: 
            <em>"Is something present that statistically should not be there?"</em>
          </p>
          <p>
            Hidden objects disturb the environment—even if they are not visible. These disturbances can appear as subtle visual texture disruptions, temperature inconsistencies, or minor RF signal irregularities. Individually insignificant, but when fused and analyzed using AI, they form a detectable anomaly pattern.
          </p>
        </motion.div>

        {/* The 3 Pillars of Detection */}
        <motion.div className="doc-visual glass-panel" variants={itemVariants} style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem', padding: '2rem' }}>
          <h3 style={{ textAlign: 'center', color: 'var(--accent)', fontSize: '1.2rem', marginBottom: '1rem' }}>Multi-Modal Sensor Acquisition</h3>
          
          <div style={{ display: 'flex', alignItems: 'center', gap: '1rem', background: 'var(--bg-surface)', padding: '1rem', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border-light)' }}>
            <Eye color="var(--accent)" size={28} />
            <div>
              <strong style={{ display: 'block', color: 'var(--text-main)' }}>Visual Module</strong>
              <span style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>Detects irregular shapes, disturbed textures (camouflage), and unnatural motion.</span>
            </div>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '1rem', background: 'var(--bg-surface)', padding: '1rem', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border-light)' }}>
            <Thermometer color="#ff8e8b" size={28} />
            <div>
              <strong style={{ display: 'block', color: 'var(--text-main)' }}>Thermal Module</strong>
              <span style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>Maps temperature gradients and tracks temporal heat variation against the baseline.</span>
            </div>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '1rem', background: 'var(--bg-surface)', padding: '1rem', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border-light)' }}>
            <Radio color="#8be0a4" size={28} />
            <div>
              <strong style={{ display: 'block', color: 'var(--text-main)' }}>RF Sensing Module</strong>
              <span style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>Tracks RSSI signal strength variations and frequency spectrum deviations.</span>
            </div>
          </div>
        </motion.div>

        {/* AI ML Core */}
        <motion.div className="doc-visual glass-panel offset-visual" variants={itemVariants} style={{ display: 'flex', flexDirection: 'column', justifyContent: 'center' }}>
          <div className="diagram-container vertical">
            <div className="d-node small">Multi-Modal Inputs</div>
            <motion.div className="d-arrow-down" animate={{ y: [0, 10, 0] }} transition={{ repeat: Infinity, duration: 1.5 }}>↓</motion.div>
            
            <div style={{ display: 'flex', gap: '1rem' }}>
              <div className="d-node ae-node" style={{ padding: '0.5rem', fontSize: '0.8rem' }}>Autoencoders<br/><span style={{ fontSize: '0.65rem', color: 'var(--text-muted)' }}>MSE Loss</span></div>
              <div className="d-node ae-node" style={{ padding: '0.5rem', fontSize: '0.8rem' }}>Isolation Forest<br/><span style={{ fontSize: '0.65rem', color: 'var(--text-muted)' }}>Rare Data</span></div>
              <div className="d-node ae-node" style={{ padding: '0.5rem', fontSize: '0.8rem' }}>One-Class SVM<br/><span style={{ fontSize: '0.65rem', color: 'var(--text-muted)' }}>Classification</span></div>
            </div>

            <motion.div className="d-arrow-down" animate={{ y: [0, 10, 0] }} transition={{ repeat: Infinity, duration: 1.5, delay: 0.3 }}>↓</motion.div>
            <div className="d-node resnet-node">Sensor Fusion Engine</div>
            <motion.div className="d-arrow-down" animate={{ y: [0, 10, 0] }} transition={{ repeat: Infinity, duration: 1.5, delay: 0.6 }}>↓</motion.div>
            
            <div className="decision-split">
              <div className="d-node success-node">Baseline Normal</div>
              <div className="d-node alert-node">Concealed Threat</div>
            </div>
          </div>
        </motion.div>

        {/* AI & Machine Learning */}
        <motion.div className="doc-card glass-panel stage-card" variants={itemVariants}>
          <div className="card-icon"><Cpu size={32} /></div>
          <h2>AI & Machine Learning Core</h2>
          <p>
            Why anomaly detection? Because you don’t always know what the threat looks like—you only know what “normal” looks like.
          </p>
          <p>
            Our models include <strong>Autoencoders</strong> (where high reconstruction error = anomaly), <strong>Isolation Forests</strong> (to detect rare unusual data points), and <strong>One-Class SVMs</strong>. The outputs from the vision, thermal, and RF models are combined using a Neural Fusion layer.
          </p>
        </motion.div>

        {/* Applications & Demo */}
        <motion.div className="doc-card glass-panel stage-card" variants={itemVariants} style={{ gridColumn: '1 / -1', marginTop: '2rem' }}>
          <div className="card-icon" style={{ marginBottom: '1rem' }}><Database size={32} /></div>
          <h2>Applications & Conclusion</h2>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '2rem' }}>
            <div style={{ flex: '1 1 300px' }}>
              <strong style={{ color: 'var(--accent)', display: 'block', marginBottom: '0.5rem' }}>Applications</strong>
              <ul style={{ color: 'var(--text-muted)', lineHeight: '1.8', marginLeft: '1.2rem' }}>
                <li>Border surveillance</li>
                <li>Military reconnaissance</li>
                <li>Smart perimeter security</li>
                <li>Critical infrastructure protection</li>
              </ul>
            </div>
            <div style={{ flex: '1 1 300px' }}>
              <strong style={{ color: 'var(--accent)', display: 'block', marginBottom: '0.5rem' }}>Advantages</strong>
              <ul style={{ color: 'var(--text-muted)', lineHeight: '1.8', marginLeft: '1.2rem' }}>
                <li>Works even when objects are completely hidden.</li>
                <li>Multi-sensor reliability preventing spoofing.</li>
                <li>Real-time edge detection scalable to different environments.</li>
              </ul>
            </div>
          </div>
          <p style={{ marginTop: '1.5rem', fontStyle: 'italic', color: 'var(--text-dim)', textAlign: 'center', borderTop: '1px solid var(--border)', paddingTop: '1.5rem' }}>
            By combining computer vision, thermal sensing, RF analysis, and AI, PARALLAX enables the detection of concealed threats that traditional object-detection systems would miss.
          </p>
        </motion.div>

      </motion.div>
    </div>
  );
}
