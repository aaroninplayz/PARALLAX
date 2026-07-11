import React, { useEffect, useRef } from 'react';
import { motion, useScroll, useTransform, useMotionValue, useSpring } from 'framer-motion';
import { Link } from 'react-router-dom';
import { Shield, Eye, Database, Activity, Cpu, Code, Layers, HardDrive } from 'lucide-react';
import './Home.css';
import ParticleBackground from '../components/ParticleBackground';


// ═══════════════════════════════════════════════════════
//  LIVE FEED SIMULATION (WITH ANOMALIES)
// ═══════════════════════════════════════════════════════
function LiveFeedSimulation({ onAnomalyDetected }) {
  const canvasRef = useRef(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    const ctx = canvas.getContext('2d');
    let animationFrameId;
    let particles = [];
    let anomalies = [];
    
    let anomalyActive = false;
    let anomalyTimer = 0;
    let nextAnomalySpawnTime = 300; // 5 seconds initially

    const resize = () => {
      const parent = canvas.parentElement;
      canvas.width = parent.clientWidth;
      canvas.height = parent.clientHeight;
      initParticles();
    };

    class FeedParticle {
      constructor() {
        this.x = Math.random() * canvas.width;
        this.y = Math.random() * canvas.height;
        this.vx = (Math.random() - 0.5) * 0.3;
        this.vy = (Math.random() - 0.5) * 0.3;
        this.size = Math.random() * 6 + 3;
        this.angle = Math.random() * Math.PI * 2;
        this.spin = (Math.random() - 0.5) * 0.02;

        const r = Math.floor(139 + Math.random() * 40 - 20);
        const g = Math.floor(224 + Math.random() * 30 - 15);
        const b = Math.floor(164 + Math.random() * 50 - 25);
        this.colorStr = `${r}, ${g}, ${b}`;
        this.alpha = Math.random() * 0.4 + 0.2;
      }

      update() {
        this.angle += this.spin;
        this.x += this.vx + Math.sin(this.angle) * 0.5;
        this.y += this.vy + Math.cos(this.angle) * 0.5;

        // Wrap around seamlessly
        if (this.x < -30) this.x = canvas.width + 30;
        if (this.x > canvas.width + 30) this.x = -30;
        if (this.y < -30) this.y = canvas.height + 30;
        if (this.y > canvas.height + 30) this.y = -30;
      }

      draw() {
        const gradient = ctx.createRadialGradient(
          this.x, this.y, 0, 
          this.x, this.y, this.size * 2
        );

        gradient.addColorStop(0, `rgba(${this.colorStr}, ${this.alpha})`);
        gradient.addColorStop(1, `rgba(${this.colorStr}, 0)`);

        ctx.beginPath();
        ctx.arc(this.x, this.y, this.size * 2, 0, Math.PI * 2);
        ctx.fillStyle = gradient;
        ctx.fill();
      }
    }

    class AnomalyParticle extends FeedParticle {
      constructor() {
        super();
        this.size = Math.random() * 6 + 6; // slightly larger
        this.alpha = 0.8;
        this.detected = false;
        this.isDead = false;

        // Pick a side: 0=Top, 1=Right, 2=Bottom, 3=Left
        const side = Math.floor(Math.random() * 4);
        const margin = 60; // Start outside

        if (side === 0) {
           this.x = Math.random() * canvas.width;
           this.y = -margin;
           this.vx = (Math.random() - 0.5) * 1.5;
           this.vy = Math.random() * 1.5 + 0.5; // move down
        } else if (side === 1) {
           this.x = canvas.width + margin;
           this.y = Math.random() * canvas.height;
           this.vx = -(Math.random() * 1.5 + 0.5); // move left
           this.vy = (Math.random() - 0.5) * 1.5;
        } else if (side === 2) {
           this.x = Math.random() * canvas.width;
           this.y = canvas.height + margin;
           this.vx = (Math.random() - 0.5) * 1.5;
           this.vy = -(Math.random() * 1.5 + 0.5); // move up
        } else {
           this.x = -margin;
           this.y = Math.random() * canvas.height;
           this.vx = (Math.random() * 1.5 + 0.5); // move right
           this.vy = (Math.random() - 0.5) * 1.5;
        }
      }

      update() {
        // Drift linearly across the screen
        this.x += this.vx;
        this.y += this.vy;

        // Check if inside visible bounds (detected)
        // Require it to be fully inside by a small margin
        this.detected = this.x > 15 && this.x < canvas.width - 15 && 
                        this.y > 15 && this.y < canvas.height - 15;

        // Kill if it drifted completely off the opposite side
        this.isDead = this.x < -100 || this.x > canvas.width + 100 ||
                      this.y < -100 || this.y > canvas.height + 100;
      }

      draw() {
        const gradient = ctx.createRadialGradient(
          this.x, this.y, 0, 
          this.x, this.y, this.size * 2
        );

        // Red anomaly cloud
        gradient.addColorStop(0, `rgba(255, 100, 100, ${this.alpha})`);
        gradient.addColorStop(1, `rgba(255, 100, 100, 0)`);

        ctx.beginPath();
        ctx.arc(this.x, this.y, this.size * 2, 0, Math.PI * 2);
        ctx.fillStyle = gradient;
        ctx.fill();

        if (this.detected) {
          ctx.globalCompositeOperation = 'source-over';
          ctx.strokeStyle = 'rgba(255, 142, 139, 0.8)';
          ctx.lineWidth = 1;
          const boxSize = 36;
          ctx.strokeRect(this.x - boxSize/2, this.y - boxSize/2, boxSize, boxSize);
          
          ctx.fillStyle = 'rgba(255, 142, 139, 1)';
          ctx.font = 'bold 10px monospace';
          ctx.fillText("ANOMALY", this.x + boxSize/2 + 6, this.y - boxSize/2);
          ctx.globalCompositeOperation = 'screen';
        }
      }
    }

    const initParticles = () => {
      particles = [];
      anomalies = [];
      const numParticles = Math.floor((canvas.width * canvas.height) / 3000); 
      for (let i = 0; i < numParticles; i++) {
        particles.push(new FeedParticle());
      }
    };

    const animate = () => {
      // Clear canvas so the parent background shows through, or use a dark fill
      ctx.fillStyle = 'rgba(5, 5, 8, 1)'; 
      ctx.fillRect(0, 0, canvas.width, canvas.height);

      anomalyTimer++;
      if (anomalyTimer > nextAnomalySpawnTime) {
         anomalies.push(new AnomalyParticle());
         anomalyTimer = 0;
         nextAnomalySpawnTime = Math.random() * 400 + 400; // Between 6.5s and 13s
      }

      ctx.globalCompositeOperation = 'screen';

      particles.forEach(p => {
        p.update();
        p.draw();
      });

      let isAnyDetected = false;
      for (let i = anomalies.length - 1; i >= 0; i--) {
         const a = anomalies[i];
         a.update();
         a.draw();
         if (a.detected) isAnyDetected = true;
         if (a.isDead) anomalies.splice(i, 1);
      }

      ctx.globalCompositeOperation = 'source-over';

      if (isAnyDetected !== anomalyActive) {
         anomalyActive = isAnyDetected;
         onAnomalyDetected(anomalyActive);
      }

      animationFrameId = requestAnimationFrame(animate);
    };

    window.addEventListener('resize', resize);
    // Initialize immediately
    resize();
    animate();

    return () => {
      window.removeEventListener('resize', resize);
      cancelAnimationFrame(animationFrameId);
    };
  }, [onAnomalyDetected]);

  return (
    <canvas
      ref={canvasRef}
      style={{
        position: 'absolute',
        top: 0,
        left: 0,
        width: '100%',
        height: '100%'
      }}
    />
  );
}

// ═══════════════════════════════════════════════════════
//  HOME PAGE
// ═══════════════════════════════════════════════════════
export default function Home() {
  const [hasAnomaly, setHasAnomaly] = React.useState(false);

  return (
    <div className="home-container" style={{ background: 'transparent' }}>
      <ParticleBackground />

      {/* HERO SECTION */}
      <section className="hero-section">
        <motion.div 
          className="hero-content"
          initial={{ opacity: 0, y: 30 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.8, ease: "easeOut" }}
        >
          <h1 className="hero-title">
            Next-Generation <br />
            <span className="text-gradient">Threat Detection</span>
          </h1>
          <p className="hero-subtitle">
            Detect what is statistically out of place. PARALLAX fuses spatial reconstruction and semantic filtering to identify concealed anomalies with unprecedented accuracy.
          </p>
          
          <div className="hero-actions">
            <Link to="/dashboard" className="neo-button primary" style={{ padding: '1rem 2rem', fontSize: '1rem' }}>
              <Activity size={20} />
              Launch System
            </Link>
            <Link to="/docs" className="neo-button" style={{ padding: '1rem 2rem', fontSize: '1rem' }}>
              <Database size={20} />
              Read Documentation
            </Link>
          </div>
        </motion.div>

        <motion.div 
          className="hero-visual"
          initial={{ opacity: 0, x: 50 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ duration: 1, delay: 0.2, ease: "easeOut" }}
        >
          {/* Asymmetrical glass cards representing the system */}
          <div className="glass-card card-main">
            <div className="card-header">
              <Eye className="text-accent" />
              <span>LIVE FEED</span>
            </div>
            <div className="feed-placeholder">
              <LiveFeedSimulation onAnomalyDetected={setHasAnomaly} />
              <div className="scan-line" />
            </div>
            <div className="card-footer">
              STATUS: 
              {hasAnomaly ? (
                <span style={{ color: 'var(--danger)', marginLeft: '5px', fontWeight: 'bold' }}>ANOMALY DETECTED</span>
              ) : (
                <span className="text-success" style={{ marginLeft: '5px' }}>SECURE</span>
              )}
            </div>
          </div>

          <motion.div 
            className="glass-card card-small card-offset-1"
            animate={{ y: [0, -10, 0] }}
            transition={{ duration: 4, repeat: Infinity, ease: "easeInOut" }}
            style={{ borderColor: hasAnomaly ? 'var(--danger)' : '' }}
          >
            <Shield size={24} style={{ color: hasAnomaly ? 'var(--danger)' : 'var(--success)' }} />
            <div className="small-text">
              <span className="bold">Autoencoder</span>
              <span>Reconstruction Loss: {hasAnomaly ? '0.84' : '0.04'}</span>
            </div>
          </motion.div>

          <motion.div 
            className="glass-card card-small card-offset-2"
            animate={{ y: [0, 10, 0] }}
            transition={{ duration: 5, repeat: Infinity, ease: "easeInOut", delay: 1 }}
            style={{ borderColor: hasAnomaly ? 'var(--danger)' : '' }}
          >
            <Activity size={24} style={{ color: hasAnomaly ? 'var(--danger)' : 'var(--accent)' }} />
            <div className="small-text">
              <span className="bold">Classifier</span>
              <span>Confidence: {hasAnomaly ? '94% THREAT' : '98% SAFE'}</span>
            </div>
          </motion.div>
        </motion.div>
      </section>

      {/* DOCUMENTATION OVERVIEW SECTION */}
      <section className="docs-overview-section">
        <motion.div 
          className="docs-header"
          initial={{ opacity: 0, y: 30 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, amount: 0.5 }}
          transition={{ duration: 0.8 }}
        >
          <h2>System Architecture</h2>
          <p>A brief look under the hood of the PARALLAX detection pipeline.</p>
        </motion.div>

        <div className="docs-grid">
          <motion.div 
            className="glass-card docs-card"
            initial={{ opacity: 0, y: 30 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.5, delay: 0.1 }}
          >
            <div className="docs-card-icon"><Cpu /></div>
            <h3>Spatial Reconstruction</h3>
            <p>
              The first stage utilizes an advanced Autoencoder neural network. It continuously learns the "normal" state of the environment. 
              When a new frame is processed, the model attempts to reconstruct it. High reconstruction loss pinpoints the exact pixels where anomalies occur.
            </p>
          </motion.div>

          <motion.div 
            className="glass-card docs-card"
            initial={{ opacity: 0, y: 30 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.5, delay: 0.2 }}
          >
            <div className="docs-card-icon"><Layers /></div>
            <h3>Semantic Filtering</h3>
            <p>
              To eliminate false positives caused by natural elements like moving trees or shadows, the flagged regions are passed to a ResNet-18 classifier.
              This secondary model assesses the context and confirms if the anomaly is a genuine threat or benign noise.
            </p>
          </motion.div>

          <motion.div 
            className="glass-card docs-card"
            initial={{ opacity: 0, y: 30 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.5, delay: 0.3 }}
          >
            <div className="docs-card-icon"><Code /></div>
            <h3>Real-Time Telemetry</h3>
            <p>
              The dashboard is powered by a high-performance FastAPI backend, streaming inference results at 30 FPS via WebSockets.
              All video artifacts and metadata are recorded into an encrypted, military-grade storage ring buffer for later review.
            </p>
          </motion.div>

          <motion.div 
            className="glass-card docs-card"
            initial={{ opacity: 0, y: 30 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.5, delay: 0.4 }}
          >
            <div className="docs-card-icon"><HardDrive /></div>
            <h3>Encrypted Persistence</h3>
            <p>
              Anomalies are actively monitored and persisted using SQLite. Clip generation relies on a 300-frame ring buffer, guaranteeing you always have the lead-up footage to the event. The dashboard requires JWT authentication to view these records.
            </p>
          </motion.div>
        </div>

        <motion.div 
          className="docs-cta"
          initial={{ opacity: 0 }}
          whileInView={{ opacity: 1 }}
          viewport={{ once: true }}
          transition={{ duration: 0.8, delay: 0.5 }}
        >
          <Link to="/docs" className="neo-button" style={{ padding: '1rem 3rem', fontSize: '1.1rem' }}>
            View Full Documentation ↗
          </Link>
        </motion.div>
      </section>
    </div>
  );
}
