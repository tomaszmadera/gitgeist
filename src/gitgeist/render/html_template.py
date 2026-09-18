"""Standalone HTML5/Canvas template generator for live preview."""

import html
import json
from gitgeist.schemas.live_state import LiveSimulationState


def generate_live_html(state: LiveSimulationState) -> str:
    """Generate a self-contained HTML5 page rendering the live canvas simulation."""
    # Escape "</" so the JSON payload cannot close its own script tag early;
    # "<\/" is a valid JSON escape and parses back to "</".
    state_json = state.model_dump_json(indent=2).replace("</", "<\\/")
    repo_title = html.escape(state.repository_name or "Repository")
    mode_title = state.representation_mode.capitalize()

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Gitgeist Live Portrait - {repo_title} ({mode_title})</title>
  <style>
    * {{
      margin: 0;
      padding: 0;
      box-sizing: border-box;
    }}
    body {{
      background: {state.palette.background};
      color: {state.palette.foreground};
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
      overflow: hidden;
      width: 100vw;
      height: 100vh;
      display: flex;
      flex-direction: column;
    }}
    #canvas-container {{
      position: absolute;
      top: 0;
      left: 0;
      width: 100%;
      height: 100%;
      z-index: 1;
    }}
    canvas {{
      display: block;
      width: 100%;
      height: 100%;
    }}
    #hud {{
      position: absolute;
      top: 24px;
      left: 24px;
      z-index: 10;
      background: rgba(0, 0, 0, 0.45);
      backdrop-filter: blur(12px);
      -webkit-backdrop-filter: blur(12px);
      border: 1px solid rgba(255, 255, 255, 0.12);
      border-radius: 8px;
      padding: 16px 20px;
      pointer-events: none;
      user-select: none;
      max-width: 340px;
    }}
    #hud h1 {{
      font-size: 16px;
      font-weight: 600;
      letter-spacing: 0.5px;
      margin-bottom: 4px;
      color: {state.palette.accent};
    }}
    #hud .mode-badge {{
      display: inline-block;
      font-size: 11px;
      text-transform: uppercase;
      letter-spacing: 1px;
      padding: 2px 8px;
      border-radius: 4px;
      background: {state.palette.primary};
      color: #ffffff;
      margin-bottom: 8px;
      font-weight: bold;
    }}
    #hud .meta-row {{
      font-size: 12px;
      opacity: 0.85;
      line-height: 1.5;
    }}
    #hud .meta-label {{
      font-weight: 500;
      opacity: 0.6;
    }}
  </style>
</head>
<body>
  <div id="hud">
    <div class="mode-badge">{mode_title} Mode</div>
    <h1>{repo_title}</h1>
    <div class="meta-row"><span class="meta-label">Material:</span> {html.escape(state.dominant_material)}</div>
    <div class="meta-row"><span class="meta-label">Seed:</span> {state.seed}</div>
    <div class="meta-row"><span class="meta-label">Engine:</span> Gitgeist v{html.escape(state.engine_version)}</div>
  </div>

  <div id="canvas-container">
    <canvas id="gitgeist-canvas"></canvas>
  </div>

  <script id="gitgeist-state" type="application/json">
{state_json}
  </script>

  <script>
    (function() {{
      const state = JSON.parse(document.getElementById('gitgeist-state').textContent);
      const canvas = document.getElementById('gitgeist-canvas');
      const ctx = canvas.getContext('2d');

      let width = 0;
      let height = 0;
      let dpr = 1;

      function resize() {{
        dpr = window.devicePixelRatio || 1;
        width = window.innerWidth;
        height = window.innerHeight;
        canvas.width = width * dpr;
        canvas.height = height * dpr;
        ctx.scale(dpr, dpr);
      }}

      window.addEventListener('resize', resize);
      resize();

      // Pseudo-random deterministic generator from seed
      let s = state.seed;
      function random() {{
        s = (s * 9301 + 49297) % 233280;
        return s / 233280;
      }}

      const mode = state.representation_mode;
      const pal = state.palette;
      const dyn = state.dynamics;
      const geom = state.geometry;

      // Particle / element setup
      const count = Math.floor(60 + geom.density * 240);
      const elements = [];

      for (let i = 0; i < count; i++) {{
        elements.push({{
          x: (random() - 0.5) * 600,
          y: (random() - 0.5) * 600,
          angle: random() * Math.PI * 2,
          radius: 2 + random() * 8 * (1 - geom.fragmentation * 0.5),
          speed: 0.2 + random() * dyn.flow_speed,
          phase: random() * Math.PI * 2,
          color: random() > 0.6 ? pal.accent : (random() > 0.3 ? pal.primary : pal.secondary)
        }});
      }}

      let startTime = null;

      function drawAbstract(t) {{
        const cx = width / 2;
        const cy = height / 2;
        const pulse = 1 + Math.sin(t * dyn.pulse_frequency * Math.PI * 2) * dyn.breathing_amplitude;
        const sym = geom.symmetry_order;

        ctx.fillStyle = pal.background;
        ctx.fillRect(0, 0, width, height);

        // Ambient Aura
        const auraRadius = 250 * pulse;
        const auraGrad = ctx.createRadialGradient(cx, cy, 20, cx, cy, auraRadius);
        auraGrad.addColorStop(0, pal.aura);
        auraGrad.addColorStop(1, 'rgba(0, 0, 0, 0)');
        ctx.fillStyle = auraGrad;
        ctx.beginPath();
        ctx.arc(cx, cy, auraRadius, 0, Math.PI * 2);
        ctx.fill();

        // Symmetrical particle field
        ctx.save();
        ctx.translate(cx, cy);

        const symStep = (Math.PI * 2) / sym;

        for (let sIdx = 0; sIdx < sym; sIdx++) {{
          ctx.save();
          ctx.rotate(sIdx * symStep);

          for (let i = 0; i < elements.length; i++) {{
            const el = elements[i];
            const drift = Math.sin(t * dyn.flow_speed + el.phase) * (20 + dyn.turbulence * 50);
            const ex = (el.x + drift) * pulse * 0.6;
            const ey = (el.y + Math.cos(t * dyn.flow_speed + el.phase) * 15) * pulse * 0.6;

            ctx.fillStyle = el.color;
            ctx.beginPath();
            if (geom.sharpness > 0.6) {{
              // Angular crystal/polygon
              const sz = el.radius * (geom.sharpness * 1.5);
              ctx.rect(ex - sz / 2, ey - sz / 2, sz, sz);
            }} else {{
              // Soft circle
              ctx.arc(ex, ey, el.radius, 0, Math.PI * 2);
            }}
            ctx.fill();
          }}
          ctx.restore();
        }}
        ctx.restore();
      }}

      function drawCharacter(t) {{
        const cx = width / 2;
        const cy = height / 2;
        const pulse = 1 + Math.sin(t * dyn.pulse_frequency * Math.PI * 2) * dyn.breathing_amplitude;
        const spineSegments = geom.layer_count + 3;
        // Low symmetry_order produces asymmetric protrusions and offsets
        const asym = Math.max(0, Math.min(1, (3 - geom.symmetry_order) / 2));

        ctx.fillStyle = pal.background;
        ctx.fillRect(0, 0, width, height);

        // Central entity breathing aura
        const auraRadius = 280 * pulse;
        const auraGrad = ctx.createRadialGradient(cx, cy, 30, cx, cy, auraRadius);
        auraGrad.addColorStop(0, pal.aura);
        auraGrad.addColorStop(1, 'rgba(0, 0, 0, 0)');
        ctx.fillStyle = auraGrad;
        ctx.beginPath();
        ctx.arc(cx, cy, auraRadius, 0, Math.PI * 2);
        ctx.fill();

        ctx.save();
        ctx.translate(cx, cy);

        const spineHeight = 320;
        const segSpacing = spineHeight / spineSegments;

        // Draw segmented spine and ribs
        for (let i = 0; i < spineSegments; i++) {{
          const normY = (i / (spineSegments - 1)) - 0.5;
          const segY = normY * spineHeight;
          const segWidth = (1 - Math.abs(normY) * 1.4) * 160 * pulse;
          const ribOffset = Math.sin(t * dyn.pulse_frequency * Math.PI * 2 + i * 0.5) * (10 + dyn.turbulence * 20);
          // Deterministic per-segment jitter drives asymmetric limb widths
          const jitter = Math.sin(i * 12.9898) * 0.5 + Math.cos(i * 78.233) * 0.5;
          const leftWidth = segWidth * (1 - asym * 0.35 * (0.5 + 0.5 * jitter));
          const rightWidth = segWidth * (1 - asym * 0.35 * (0.5 - 0.5 * jitter));
          const coreX = jitter * 14 * asym;

          ctx.strokeStyle = i % 2 === 0 ? pal.primary : pal.secondary;
          ctx.lineWidth = 2 + (1 - geom.fragmentation) * 4;

          // Ribs / limbs with bilateral symmetry
          ctx.beginPath();
          if (geom.organic_ratio > 0.5) {{
            // Smooth organic curves
            ctx.moveTo(-leftWidth + ribOffset, segY);
            ctx.quadraticCurveTo(coreX, segY - 20 * pulse, rightWidth - ribOffset, segY);
          }} else {{
            // Mechanical angular geometry
            ctx.moveTo(-leftWidth + ribOffset, segY);
            ctx.lineTo(coreX, segY - 10 * pulse);
            ctx.lineTo(rightWidth - ribOffset, segY);
          }}
          ctx.stroke();

          // Central core node
          ctx.fillStyle = pal.accent;
          ctx.beginPath();
          ctx.arc(coreX, segY, 4 + (1 - Math.abs(normY)) * 6 * pulse, 0, Math.PI * 2);
          ctx.fill();
        }}

        // Peripheral ornaments / particles
        for (let i = 0; i < elements.length * 0.4; i++) {{
          const el = elements[i];
          const dist = (140 + el.radius * 12) * (1 + asym * 0.3 * Math.sin(i * 3.7));
          const ang = el.angle + t * 0.3 * dyn.flow_speed;
          const ox = Math.cos(ang) * dist * pulse;
          const oy = Math.sin(ang) * (dist * 0.7) * pulse;

          ctx.fillStyle = el.color;
          ctx.beginPath();
          ctx.arc(ox, oy, el.radius * 0.8, 0, Math.PI * 2);
          ctx.fill();
        }}

        ctx.restore();
      }}

      function render(timestamp) {{
        if (!startTime) startTime = timestamp;
        const elapsed = (timestamp - startTime) / 1000;

        if (mode === 'character') {{
          drawCharacter(elapsed);
        }} else {{
          drawAbstract(elapsed);
        }}

        requestAnimationFrame(render);
      }}

      requestAnimationFrame(render);
    }})();
  </script>
</body>
</html>
"""
