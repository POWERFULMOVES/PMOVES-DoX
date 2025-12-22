"use client";

import React, { useEffect, useRef } from 'react';
import * as d3 from 'd3';
import { cn } from '@/lib/utils';

export interface ZetaVisualizerProps {
  frequencies: number[]; // Array of Zeta zero imaginary parts or derived frequencies
  amplitudes: number[]; // Signal strength at each frequency
  className?: string;
  width?: number;
  height?: number;
}

export function ZetaVisualizer({ frequencies, amplitudes, className, width = 400, height = 200 }: ZetaVisualizerProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    let animationFrameId: number;
    let time = 0;

    // Standard Riemann Zeta non-trivial zero imaginary parts (first few)
    // If frequencies prop is empty, default to these
    const zetaZeros = frequencies.length > 0 ? frequencies : [14.13, 21.02, 25.01, 30.42, 32.93];
    const amps = amplitudes.length > 0 ? amplitudes : zetaZeros.map(() => 0.5);

    const render = () => {
      // Clear canvas
      ctx.fillStyle = 'rgba(2, 6, 23, 0.2)'; // Fade out effect (slate-950 with alpha)
      ctx.fillRect(0, 0, width, height);

      const centerX = width / 2;
      const centerY = height / 2;

      // Draw "Zeta Ripples"
      // Each frequency creates a concentric wave pattern
      zetaZeros.forEach((freq, i) => {
        const amp = amps[i] || 0.1;
        const radiusBase = Math.min(width, height) / 4;
        
        // Calculate dynamic radius based on frequency and time
        // Higher frequency = faster ripple
        const phase = (time * freq * 0.05) % (Math.PI * 2);
        const radius = radiusBase + (Math.sin(phase) * radiusBase * 0.5 * amp);
        
        ctx.beginPath();
        ctx.arc(centerX, centerY, radius, 0, Math.PI * 2);
        
        // Color mapping: 
        // Low freq (violet/blue) -> High freq (red/orange)
        // Simple HSL shift
        const hue = 240 - (i * 20); // Blue down to Green/Red
        ctx.strokeStyle = `hsla(${hue}, 70%, 60%, ${0.3 + (Math.cos(phase)*0.2)})`;
        ctx.lineWidth = 2 * amp;
        ctx.stroke();

        // Draw spectral bars at bottom
        const barWidth = (width / zetaZeros.length) - 2;
        const barHeight = amp * (height * 0.3) * Math.abs(Math.sin(phase));
        ctx.fillStyle = `hsla(${hue}, 70%, 60%, 0.8)`;
        ctx.fillRect(i * (width / zetaZeros.length), height - barHeight, barWidth, barHeight);
      });

      time += 0.05;
      animationFrameId = requestAnimationFrame(render);
    };

    render();

    return () => {
      cancelAnimationFrame(animationFrameId);
    };
  }, [frequencies, amplitudes, width, height]);

  return (
    <div className={cn("relative border rounded-lg overflow-hidden bg-slate-950", className)}>
       <canvas 
         ref={canvasRef} 
         width={width} 
         height={height}
         className="w-full h-full block"
       />
       <div className="absolute top-2 left-2 pointer-events-none">
          <span className="text-[10px] uppercase tracking-wider text-slate-500 font-mono">Zeta Spectral Resonance</span>
       </div>
    </div>
  );
}
