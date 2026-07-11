import React, { useEffect, useRef } from 'react';

export default function ParticleBackground() {
  const canvasRef = useRef(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    const ctx = canvas.getContext('2d');
    let animationFrameId;
    let particles = [];
    let lastScrollY = window.scrollY;

    const resize = () => {
      canvas.width = window.innerWidth;
      canvas.height = window.innerHeight;
      initParticles();
    };

    class Particle {
      constructor() {
        this.x = Math.random() * canvas.width;
        this.y = Math.random() * canvas.height;
        this.vx = (Math.random() - 0.5) * 0.3;
        this.vy = (Math.random() - 0.5) * 0.3;
        this.size = Math.random() * 8 + 2; // Larger sizes for softer clouds
        this.baseSize = this.size;
        this.angle = Math.random() * Math.PI * 2;
        this.spin = (Math.random() - 0.5) * 0.02;
        
        // Deep space/gas cloud aesthetic
        const r = Math.floor(139 + Math.random() * 40 - 20);
        const g = Math.floor(224 + Math.random() * 30 - 15);
        const b = Math.floor(164 + Math.random() * 50 - 25);
        this.colorStr = `${r}, ${g}, ${b}`;
        this.alpha = Math.random() * 0.4 + 0.1;
      }

      update(scrollDelta) {
        this.angle += this.spin;
        // Organic drift
        this.x += this.vx + Math.sin(this.angle) * 0.5;
        this.y += this.vy + Math.cos(this.angle) * 0.5;

        // Apply scroll force for parallax depth effect
        this.y -= scrollDelta * (this.baseSize * 0.15);

        // Wrap around seamlessly
        if (this.x < -50) this.x = canvas.width + 50;
        if (this.x > canvas.width + 50) this.x = -50;
        if (this.y < -50) this.y = canvas.height + 50;
        if (this.y > canvas.height + 50) this.y = -50;
      }

      draw() {
        // Draw soft radial gradient for a cloud/gas effect
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

    const initParticles = () => {
      particles = [];
      const numParticles = Math.floor((canvas.width * canvas.height) / 8000); // Dense cloud
      for (let i = 0; i < numParticles; i++) {
        particles.push(new Particle());
      }
    };

    const animate = () => {
      // Clear with dark background
      ctx.fillStyle = 'rgba(5, 5, 8, 1)'; 
      ctx.fillRect(0, 0, canvas.width, canvas.height);

      const currentScrollY = window.scrollY;
      const scrollDelta = currentScrollY - lastScrollY;
      lastScrollY = currentScrollY;

      // Enable global composite operation for glowing overlapping gas clouds
      ctx.globalCompositeOperation = 'screen';

      particles.forEach(p => {
        p.update(scrollDelta);
        p.draw();
      });

      // Reset
      ctx.globalCompositeOperation = 'source-over';

      animationFrameId = requestAnimationFrame(animate);
    };

    window.addEventListener('resize', resize);
    resize();
    animate();

    return () => {
      window.removeEventListener('resize', resize);
      cancelAnimationFrame(animationFrameId);
    };
  }, []);

  return (
    <canvas
      ref={canvasRef}
      style={{
        position: 'fixed',
        top: 0,
        left: 0,
        width: '100%',
        height: '100%',
        zIndex: -1,
        pointerEvents: 'none'
      }}
    />
  );
}
