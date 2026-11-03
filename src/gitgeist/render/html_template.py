"""Standalone HTML5/Canvas template generator for live preview."""

import html
from gitgeist.render.page_common import (
    JS_FRAME,
    JS_HEAD,
    JS_HOVER_OPEN,
    JS_HOVER_TAIL,
    JS_PULSE,
    JS_RESIZE,
    JS_SCENE_VARS,
    JS_SEED,
    page_html,
)
from gitgeist.schemas.live_state import LiveSimulationState, OrbitsScene


def generate_live_html(state: LiveSimulationState) -> str:
    """Generate the self-contained HTML5 page of the character live simulation.

    Raises:
        TypeError: If state is not a LiveSimulationState.
        ValueError: If state is not a character state; the abstract portrait is drawn by
            ``generate_orbits_html`` from an ``OrbitsScene``.
    """
    if not isinstance(state, LiveSimulationState):
        raise TypeError(f"Expected LiveSimulationState, got {type(state).__name__}")
    if state.representation_mode != "character":
        raise ValueError("generate_live_html draws only the character representation; use generate_orbits_html")
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

        drawCharacter(elapsed);

        requestAnimationFrame(render);
      }}

      requestAnimationFrame(render);
    }})();
  </script>
</body>
</html>
"""


_ORBITS_CONSTANTS = """  var TAU = Math.PI * 2;
  var GROUND = '#121218';
  var BODY_LIGHTNESS = 45;
  var RING_WIDTH_MIN = 0.5;
  var RING_WIDTH_SPAN = 3.5;
  var STRAND_RADIUS_MIN = 0.55;
  var STRAND_RADIUS_SPAN = 0.4;
  var BREATHING = 0.04;
  var CRACK_LENGTH = 0.15;
  var FLICKER_MIN_HZ = 0.5;
  var FLICKER_SPAN_HZ = 2.5;
  var RECENT_LOOP_SHARE = 0.1;
  var RECENT_MONTHS = 3;
  var OUTLINE_POINTS = 36;
  var HUD_STRIP = 120;

"""

_ORBITS_PARTS = """  /* Seeded, frame-stable parts of the drawing. */
  var bodies = masses.map(function (mass, index) {
    var noise = [];
    for (var k = 0; k < OUTLINE_POINTS; k++) { noise.push(rand() * 2 - 1); }
    return { mass: mass, index: index, noise: noise, hatchAngle: rand() * Math.PI, breathPhase: rand() * TAU };
  });
  var cracks = spec.cracks.marks.map(function (mark) {
    var offsets = [];
    for (var k = 0; k < 4; k++) { offsets.push(rand() * 2 - 1); }
    return { mark: mark, offsets: offsets };
  });
  var totalShare = masses.reduce(function (sum, mass) { return sum + mass.file_share; }, 0);
  var dust = [];
  for (var d = 0; d < spec.footprint.element_count; d++) {
    var pick = rand() * totalShare;
    var owner = -1;
    for (var m = 0; m < masses.length && owner < 0; m++) {
      pick -= masses[m].file_share;
      if (pick <= 0) { owner = m; }
    }
    if (owner < 0 && masses.length > 0) { owner = masses.length - 1; }
    dust.push({
      owner: owner, dist: Math.sqrt(rand()) * 0.9, angle: rand() * TAU,
      phase: rand() * TAU, reach: 0.02 + rand() * 0.05
    });
  }
  var strands = spec.strands.paths.map(function (path) {
    var rate = 0.6 + 0.8 * ((path.phase * 7.3) % 1);
    return { path: path, rate: rate * (path.curvature < 0 ? -1 : 1) };
  });

"""

_ORBITS_DRAW = """  function outline(body, x, y, r) {
    var jitter = spec.edge.jitter;
    ctx.beginPath();
    if (jitter === 0) {
      ctx.arc(x, y, r, 0, TAU);
      return;
    }
    var pts = [];
    for (var k = 0; k < OUTLINE_POINTS; k++) {
      var a = k / OUTLINE_POINTS * TAU;
      var rr = r * (1 + jitter * body.noise[k]);
      pts.push([x + Math.cos(a) * rr, y + Math.sin(a) * rr]);
    }
    var last = pts[pts.length - 1];
    ctx.moveTo((last[0] + pts[0][0]) / 2, (last[1] + pts[0][1]) / 2);
    for (var i = 0; i < pts.length; i++) {
      var next = pts[(i + 1) % pts.length];
      ctx.quadraticCurveTo(pts[i][0], pts[i][1], (pts[i][0] + next[0]) / 2, (pts[i][1] + next[1]) / 2);
    }
    ctx.closePath();
  }

  var layout = [];

  function draw(t) {
    var loopTime = ((t % loopSeconds) + loopSeconds) % loopSeconds;
    var amp = pulseAmplitude(loopTime);
    /* The top strip is reserved for the HUD in both caption modes, so the picture is the same. */
    var strip = Math.min(HUD_STRIP, height * 0.3);
    var area = Math.max(1, height - strip);
    var R = Math.max(1, 0.5 * Math.min(spec.footprint.coverage * Math.min(width, height), area));
    var cx = width / 2;
    var cy = strip + area / 2;

    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    ctx.shadowBlur = 0;
    ctx.fillStyle = GROUND;
    ctx.fillRect(0, 0, width, height);

    /* strands: closed orbits around the footprint centre, each bead on its own phase */
    strands.forEach(function (strand) {
      var a = (STRAND_RADIUS_MIN + STRAND_RADIUS_SPAN * strand.path.phase) * R;
      var ecc = 0.35 * Math.abs(strand.path.curvature);
      var b = a * Math.sqrt(1 - ecc * ecc);
      var tilt = strand.path.curvature * Math.PI / 2;
      ctx.strokeStyle = 'hsla(0,0%,78%,0.28)';
      ctx.lineWidth = 1;
      ctx.beginPath();
      ctx.ellipse(cx, cy, a, b, tilt, 0, TAU);
      ctx.stroke();
      var theta = TAU * (strand.path.phase + speed * 0.25 * strand.rate * t);
      var bx = cx + a * Math.cos(theta) * Math.cos(tilt) - b * Math.sin(theta) * Math.sin(tilt);
      var by = cy + a * Math.cos(theta) * Math.sin(tilt) + b * Math.sin(theta) * Math.cos(tilt);
      ctx.fillStyle = 'hsla(0,0%,88%,0.8)';
      ctx.beginPath();
      ctx.arc(bx, by, 2.5, 0, TAU);
      ctx.fill();
    });

    layout = [];
    bodies.forEach(function (body) {
      var mass = body.mass;
      var breathe = 1 + BREATHING * amp * Math.sin(TAU * speed * t + body.breathPhase);
      var r = mass.radius * R * breathe;
      var x = cx + mass.x * R;
      var y = cy + mass.y * R;
      layout.push({ x: x, y: y, r: r });
      if (r < 0.5) { return; }
      var fill = hsl(mass.hue, saturation, BODY_LIGHTNESS, 1);
      var edge = hsl(mass.hue, saturation, BODY_LIGHTNESS + 18, 1);

      ctx.shadowColor = fill;
      ctx.shadowBlur = spec.edge.blur_px * dpr;
      ctx.fillStyle = fill;
      outline(body, x, y, r);
      ctx.fill();
      ctx.shadowBlur = 0;
      ctx.strokeStyle = edge;
      ctx.lineWidth = 1.2;
      ctx.stroke();

      /* nesting: concentric sub-discs, one per level of directory depth */
      var levels = spec.topology.nesting_levels;
      for (var k = 1; k <= levels; k++) {
        ctx.fillStyle = hsl(mass.hue, saturation, BODY_LIGHTNESS - 7 * k, 0.9);
        ctx.beginPath();
        ctx.arc(x, y, r * (1 - k / (levels + 1)), 0, TAU);
        ctx.fill();
      }

      /* growth rings, oldest innermost */
      var rings = spec.rings.thickness;
      var maxWidth = r / (rings.length + 1);
      for (var q = 0; q < rings.length; q++) {
        var lw = Math.min(RING_WIDTH_MIN + RING_WIDTH_SPAN * rings[q], maxWidth);
        if (lw <= 0) { continue; }
        ctx.strokeStyle = hsl(mass.hue, saturation, 72, 0.85);
        ctx.lineWidth = lw;
        ctx.beginPath();
        ctx.arc(x, y, r * (q + 1) / (rings.length + 1), 0, TAU);
        ctx.stroke();
      }

      /* hatching: parallel lines clipped to the body, spacing from the covered share */
      var coverage = spec.hatching.coverage;
      if (coverage > 0.005 && r > 2) {
        var spacing = 1 / coverage;
        var dx = Math.cos(body.hatchAngle);
        var dy = Math.sin(body.hatchAngle);
        ctx.save();
        outline(body, x, y, r);
        ctx.clip();
        ctx.strokeStyle = hsl(mass.hue, saturation, 80, 0.55);
        ctx.lineWidth = 1;
        ctx.beginPath();
        for (var o = -r; o <= r; o += spacing) {
          var ox = x - dy * o;
          var oy = y + dx * o;
          ctx.moveTo(ox - dx * r, oy - dy * r);
          ctx.lineTo(ox + dx * r, oy + dy * r);
        }
        ctx.stroke();
        ctx.restore();
      }
    });

    /* cracks: short jagged lines at a polar position on their body */
    ctx.strokeStyle = 'rgba(8,8,12,0.9)';
    ctx.lineWidth = 1.4;
    cracks.forEach(function (crack) {
      var place = layout[crack.mark.mass_index];
      if (!place || place.r < 2) { return; }
      var polar = crack.mark.v * TAU;
      var px = place.x + Math.cos(polar) * crack.mark.u * place.r;
      var py = place.y + Math.sin(polar) * crack.mark.u * place.r;
      var dir = crack.mark.angle * Math.PI / 180;
      var len = CRACK_LENGTH * place.r;
      ctx.beginPath();
      ctx.moveTo(px, py);
      for (var s = 1; s <= 4; s++) {
        var along = len * s / 4;
        var side = crack.offsets[s - 1] * len * 0.18;
        ctx.lineTo(px + Math.cos(dir) * along - Math.sin(dir) * side, py + Math.sin(dir) * along + Math.cos(dir) * side);
      }
      ctx.stroke();
    });

    /* focal knot: a bright disc on the owning body, flickering at its own rate */
    var knot = spec.knot;
    if (knot !== null && layout[knot.mass_index]) {
      var host = layout[knot.mass_index];
      var hostMass = masses[knot.mass_index];
      var hz = FLICKER_MIN_HZ + FLICKER_SPAN_HZ * knot.flicker;
      var glow = 0.55 + 0.45 * (0.5 + 0.5 * Math.sin(TAU * hz * t));
      var kr = knot.radius * host.r;
      ctx.shadowColor = hsl(hostMass.hue, saturation, 85, 1);
      ctx.shadowBlur = 10 * dpr;
      ctx.fillStyle = hsl(hostMass.hue, saturation, 88, glow);
      ctx.beginPath();
      ctx.arc(host.x + knot.offset_x * R, host.y + knot.offset_y * R, Math.max(0.5, kr), 0, TAU);
      ctx.fill();
      ctx.shadowBlur = 0;
    }

    /* dust: small points drifting over the bodies in proportion to their file share */
    dust.forEach(function (p) {
      var where = p.owner >= 0 ? layout[p.owner] : { x: cx, y: cy, r: R };
      var hue = p.owner >= 0 ? masses[p.owner].hue : null;
      var drift = p.phase + TAU * speed * 0.3 * t;
      var px = where.x + Math.cos(p.angle) * p.dist * where.r + Math.cos(drift) * p.reach * R;
      var py = where.y + Math.sin(p.angle) * p.dist * where.r + Math.sin(drift) * p.reach * R;
      ctx.fillStyle = hsl(hue, saturation, 78, 0.7);
      ctx.fillRect(px - 0.75, py - 0.75, 1.5, 1.5);
    });
  }

"""

_ORBITS_HIT = """      var hit = -1;
      var best = Infinity;
      layout.forEach(function (place, index) {
        var dist = Math.hypot(event.clientX - place.x, event.clientY - place.y);
        if (dist <= place.r && dist < best) { best = dist; hit = index; }
      });
"""

# The page draws only from the embedded OrbitsScene (spec docs/features/live-renderer-v2/spec.md).
# Every frame is a pure function of the scene and the animation time; all randomness comes from
# one mulberry32 generator seeded with the effective seed modulo 2^32.
_ORBITS_JS = (
    JS_HEAD + _ORBITS_CONSTANTS + JS_SEED + JS_SCENE_VARS + _ORBITS_PARTS + JS_RESIZE + JS_PULSE
    + _ORBITS_DRAW + JS_FRAME + JS_HOVER_OPEN + _ORBITS_HIT + JS_HOVER_TAIL
)


def generate_orbits_html(scene: OrbitsScene) -> str:
    """Generate the self-contained HTML5 page of the abstract ``orbits`` portrait.

    The page embeds the scene JSON and draws only from it; with ``scene.caption`` false it has
    no HUD and no hover box.

    Raises:
        TypeError: If scene is not an OrbitsScene.
    """
    if not isinstance(scene, OrbitsScene):
        raise TypeError(f"Expected OrbitsScene, got {type(scene).__name__}")
    return page_html(scene, "Abstract", _ORBITS_JS)
