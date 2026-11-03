"""Page code shared by the abstract ``orbits`` and the character ``creature`` live pages.

Both pages use the same CSS, HUD and hover box markup, the same seed reading and mulberry32
generator, the same timeline pulse, window resize and frame loop, and the same hover tooltip
text (stage 5 spec C10). The orbits page assembled from these parts is byte-identical to the
0.10.0 page (``tests/test_orbits_snapshot.py``). Everything else (constants, seeded parts,
drawing, hit test) belongs to the style.
"""

import html

from gitgeist.schemas.live_state import CreatureScene, OrbitsScene

PAGE_CSS = """
    * { margin: 0; padding: 0; box-sizing: border-box; }
    body {
      background: #121218;
      color: #e8e8ee;
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
      overflow: hidden;
      width: 100vw;
      height: 100vh;
    }
    #canvas-container { position: absolute; top: 0; left: 0; width: 100%; height: 100%; z-index: 1; }
    canvas { display: block; width: 100%; height: 100%; }
    /* The HUD has a fixed height (HUD_STRIP in the script reserves the strip above the composition). */
    #hud {
      position: absolute; top: 12px; left: 12px; z-index: 10;
      height: 104px;
      width: 340px; max-width: calc(100vw - 24px);
      background: rgba(0, 0, 0, 0.45);
      border: 1px solid rgba(255, 255, 255, 0.12);
      border-radius: 8px;
      padding: 8px 14px;
      overflow: hidden;
      pointer-events: none;
      user-select: none;
    }
    #hud h1 { font-size: 15px; line-height: 20px; font-weight: 600; letter-spacing: 0.5px; margin-bottom: 6px; }
    #hud h1, #hud li { white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
    #hud ul { list-style: none; }
    #hud li { font-size: 13px; line-height: 20px; opacity: 0.9; }
    #hover {
      position: absolute; z-index: 20; display: none;
      background: rgba(0, 0, 0, 0.75);
      border: 1px solid rgba(255, 255, 255, 0.2);
      border-radius: 6px;
      padding: 8px 12px;
      pointer-events: none;
      font-size: 12px; line-height: 1.5;
      max-width: 320px; overflow-wrap: anywhere;
    }
"""

# Opening of the page script: scene, canvas, context and hover box.
JS_HEAD = """
(function () {
  'use strict';
  var stateText = document.getElementById('gitgeist-state').textContent;
  var scene = JSON.parse(stateText);
  var spec = scene.spec;
  var canvas = document.getElementById('gitgeist-canvas');
  var ctx = canvas.getContext('2d');
  var hoverBox = document.getElementById('hover');

"""

# Seed (32 bits) read from the raw JSON text, and the mulberry32 generator.
JS_SEED = """  /* The effective seed has up to 64 bits: read it from the raw text, not from the parsed double. */
  var seedMatch = /"effective_seed":\\s*(\\d+)/.exec(stateText);
  var seed32 = Number(BigInt(seedMatch[1]) & BigInt(4294967295));
  function mulberry32(a) {
    return function () {
      a = (a + 0x6D2B79F5) | 0;
      var t = Math.imul(a ^ (a >>> 15), 1 | a);
      t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
      return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
    };
  }
  var rand = mulberry32(seed32);

"""

# Scene shortcuts shared by both pages, and the hsla colour helper.
JS_SCENE_VARS = """  var masses = spec.masses;
  var saturation = Math.round(spec.palette.saturation * 100);
  var speed = spec.motion.speed_hz;
  var loopSeconds = spec.motion.loop_seconds;
  var pulse = spec.motion.pulse;

  function hsl(hue, sat, light, alpha) {
    var h = hue === null ? 0 : hue;
    var s = hue === null ? 0 : sat;
    return 'hsla(' + h.toFixed(1) + ',' + s + '%,' + light.toFixed(1) + '%,' + alpha + ')';
  }

"""

# Window size and device pixel ratio.
JS_RESIZE = """  var width = 0;
  var height = 0;
  var dpr = 1;
  function resize() {
    dpr = window.devicePixelRatio || 1;
    width = Math.max(1, window.innerWidth);
    height = Math.max(1, window.innerHeight);
    canvas.width = Math.round(width * dpr);
    canvas.height = Math.round(height * dpr);
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  }
  window.addEventListener('resize', resize);
  resize();

"""

# Replay of the monthly commit pulse over one loop (the last 90 days take the final 10%).
JS_PULSE = """  function pulseAmplitude(loopTime) {
    var n = pulse.length;
    if (n === 0) { return 0; }
    var u = loopTime / loopSeconds;
    var index;
    if (n <= RECENT_MONTHS) {
      index = Math.floor(u * n);
    } else if (u < 1 - RECENT_LOOP_SHARE) {
      index = Math.floor(u / (1 - RECENT_LOOP_SHARE) * (n - RECENT_MONTHS));
    } else {
      index = n - RECENT_MONTHS + Math.floor((u - (1 - RECENT_LOOP_SHARE)) / RECENT_LOOP_SHARE * RECENT_MONTHS);
    }
    return pulse[Math.max(0, Math.min(n - 1, index))];
  }

"""

# Animation clock and frame loop.
JS_FRAME = """  var startTime = null;
  function frame(timestamp) {
    if (startTime === null) { startTime = timestamp; }
    draw((timestamp - startTime) / 1000);
    requestAnimationFrame(frame);
  }
  requestAnimationFrame(frame);

"""

# Start of the mousemove handler; the style adds its own hit test next.
JS_HOVER_OPEN = """  if (hoverBox && scene.caption) {
    window.addEventListener('mousemove', function (event) {
"""

# Hover tooltip text for the hit mass, and the end of the script.
JS_HOVER_TAIL = """      var detail = null;
      scene.hover.forEach(function (item) { if (item.mass_index === hit) { detail = item; } });
      if (detail === null) { hoverBox.style.display = 'none'; return; }
      var lines = [detail.label, detail.file_count + ' files (' + detail.file_share_percent + '%)'];
      if (detail.top_hotspot !== null) { lines.push('hotspot: ' + detail.top_hotspot); }
      hoverBox.textContent = lines.join('\\n');
      hoverBox.style.whiteSpace = 'pre-line';
      hoverBox.style.display = 'block';
      hoverBox.style.left = Math.min(event.clientX + 14, Math.max(0, window.innerWidth - 340)) + 'px';
      hoverBox.style.top = (event.clientY + 14) + 'px';
    });
  }
})();
"""


def hud_markup(scene: OrbitsScene | CreatureScene) -> tuple[str, str]:
    """HUD and hover box markup of a scene; both are empty when the scene has no caption."""
    if not scene.caption:
        return "", ""
    repo_title = html.escape(scene.repository_name or "Repository")
    items = "\n".join(f"      <li>{html.escape(text)}</li>" for text in scene.conclusions)
    hud = f'  <div id="hud">\n    <h1>{repo_title}</h1>\n    <ul>\n{items}\n    </ul>\n  </div>\n'
    return hud, '  <div id="hover"></div>\n'


def page_html(scene: OrbitsScene | CreatureScene, representation_title: str, script: str) -> str:
    """Assemble the self-contained page around a style's script (``script`` starts with a newline)."""
    # "<\/" is a valid JSON escape: the payload cannot close its own script tag early.
    scene_json = scene.model_dump_json(indent=2).replace("</", "<\\/")
    repo_title = html.escape(scene.repository_name or "Repository")
    hud, hover = hud_markup(scene)
    return (
        "<!DOCTYPE html>\n"
        '<html lang="en">\n<head>\n'
        '  <meta charset="UTF-8">\n'
        '  <meta name="viewport" content="width=device-width, initial-scale=1.0">\n'
        f"  <title>Gitgeist Live Portrait - {repo_title} ({representation_title})</title>\n"
        f"  <style>{PAGE_CSS}  </style>\n"
        "</head>\n<body>\n"
        f"{hud}{hover}"
        '  <div id="canvas-container">\n    <canvas id="gitgeist-canvas"></canvas>\n  </div>\n\n'
        f'  <script id="gitgeist-state" type="application/json">\n{scene_json}\n  </script>\n\n'
        f"  <script>{script}  </script>\n"
        "</body>\n</html>\n"
    )
