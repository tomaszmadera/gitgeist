"""Live page of the ``anatomy`` representation: HUD of raw counts, legend, canvas drawing, hover and breathing.

See ``docs/features/anatomy-representation/spec.md``, sections "What each visual property means" and "Page".
Every coordinate comes from the scene (``gitgeist.render.anatomy``); the script only scales the scene to the
viewport, draws it, and moves every body with the same slow breathing. Motion never encodes a fact. No
colour or mark expresses good or bad: every mark uses one neutral light colour on the dark ground, and hue
only tells the language. The page has no randomness: two renders of the same scene draw the same picture.
"""

from __future__ import annotations

import html
import json

from gitgeist.render.page_common import JS_FRAME, JS_HEAD, JS_HOVER_OPEN, JS_RESIZE, page_html
from gitgeist.schemas.live_state import AnatomyScene

# One neutral hue family per language, at a low saturation (no red or green, criterion 7).
LANGUAGE_HUES = {"php": 265, "typescript": 210, "javascript": 190, "python": 45}
LANGUAGE_NAMES = {"php": "PHP", "typescript": "TypeScript", "javascript": "JavaScript", "python": "Python"}
TISSUE_SATURATION = 28
SWATCH_LIGHTNESS = 50

# One line per row of the spec table "What each visual property means", in its order.
LEGEND_ROWS = (
    ("Cell area", "lines of the file"),
    ("Cell in an organ, organ outline (one merged skin)", "community in the dependency graph"),
    ("Tendon width", "number of edges between two organs"),
    ("Separate body", "separate connected component"),
    ("Dust speck", "file with no internal dependency, drawn at 0.18 of its cell radius, at least 0.6 px"),
    ("Grey cyst with dashed outline", "foreign files"),
    (
        "Concentric strata inside a cell",
        "lines per blame year, older years innermost and darker",
    ),
    ("Surface wear (grain density on the cell edge)", "changes, square-root scale"),
    ("White rim", "test file"),
    ("Thin outer membrane on a non-test cell", "number of test files with an edge to it"),
    ("Tissue hue", "language"),
    (
        "Tissue texture solid, hatched, dotted",
        "PHP namespace and strict_types both, one, none; TypeScript typed without, with loose marks, "
        "or untyped TS/JS; Python: annotated share of functions is the solid fraction of the cell "
        "(a file without functions is solid)",
    ),
    ("Light grey dots inside a cell", "superglobals + globals, one dot per occurrence"),
    ("Hollow dots inside a cell", "deprecated calls, one dot per occurrence"),
)

_ANATOMY_CSS = """    #hud { height: auto; }
    #legend {
      position: absolute; right: 12px; bottom: 12px; z-index: 10;
      width: 340px; max-width: calc(100vw - 24px);
      max-height: calc(100vh - 24px); overflow: auto;
      background: rgba(0, 0, 0, 0.45);
      border: 1px solid rgba(255, 255, 255, 0.12);
      border-radius: 8px;
      padding: 8px 12px;
      font-size: 11px; line-height: 15px;
      user-select: none;
    }
    #legend ul { list-style: none; }
    #legend li { margin-bottom: 3px; opacity: 0.9; }
    #legend b { font-weight: 600; }
    #legend .swatch {
      display: inline-block; width: 9px; height: 9px; border-radius: 50%;
      margin: 0 3px 0 6px; vertical-align: -1px;
    }
"""

_ANATOMY_CONSTANTS = """  var TAU = Math.PI * 2;
  var GOLDEN_ANGLE = Math.PI * (3 - Math.sqrt(5));
  var GROUND = '#121218';
  var MARK = 'rgba(232, 232, 238, ';
  var SKIN_FILL = '#24242e';
  var SKIN_EDGE = '#55556a';
  var CYST_FILL = 'rgba(96, 96, 110, 0.35)';
  var CYST_EDGE = 'rgba(150, 150, 164, 0.75)';
  var TEXTURE = 'rgba(18, 18, 24, 0.6)';
  var LANGUAGE_HUE = __LANGUAGE_HUE__;
  var TISSUE_SATURATION = __TISSUE_SATURATION__;
  var STRATA_LIGHT_FIRST = 22;
  var STRATA_LIGHT_LAST = 64;
  var UNBLAMED_LIGHT = 40;
  var SKIN_GROW = 1.35;
  var WEAR = 0.03;
  var TEXTURE_STEP = 3;
  var DOT_REACH = 0.72;
  var DUST_SCALE = 0.18;
  var DUST_MIN = 0.6;
  var FRAME_FILL = 0.92;
  var MARGIN = 12;
  var BREATH_PERIOD = 7;
  var BREATH_AMPLITUDE = 0.015;
  var hud = document.getElementById('hud');
  var legend = document.getElementById('legend');
  var years = scene.blame_years;

"""

_ANATOMY_DRAW = r"""  /* Frame: the bounding box of bodies and cysts (dust is placed in fractions of the frame side). */
  var boxes = scene.bodies.concat(scene.cysts);
  var minX = 0, maxX = 0, minY = 0, maxY = 0;
  if (boxes.length > 0) {
    minX = Infinity; maxX = -Infinity; minY = Infinity; maxY = -Infinity;
    boxes.forEach(function (b) {
      minX = Math.min(minX, b.x - b.r); maxX = Math.max(maxX, b.x + b.r);
      minY = Math.min(minY, b.y - b.r); maxY = Math.max(maxY, b.y + b.r);
    });
  }
  var sceneCx = (minX + maxX) / 2;
  var sceneCy = (minY + maxY) / 2;
  var sceneSpan = Math.max(maxX - minX, maxY - minY, 1);
  var view = { cx: 0, cy: 0, side: 1, s: 1 };

  /* The free area: below the HUD, and beside or above the legend, whichever leaves the larger square. */
  function fit() {
    var top = MARGIN;
    if (hud) { top = hud.offsetTop + hud.offsetHeight + MARGIN; }
    var left = MARGIN;
    var right = width - MARGIN;
    var bottom = height - MARGIN;
    var besideW = right - left - legend.offsetWidth - MARGIN;
    var aboveH = legend.offsetTop - MARGIN - top;
    var beside = Math.min(besideW, bottom - top);
    var above = Math.min(right - left, aboveH);
    var area;
    if (beside >= above) {
      area = [left, top, left + Math.max(1, besideW), bottom];
    } else {
      area = [left, top, right, top + Math.max(1, aboveH)];
    }
    view.side = Math.max(1, Math.min(area[2] - area[0], area[3] - area[1]));
    view.cx = (area[0] + area[2]) / 2;
    view.cy = (area[1] + area[3]) / 2;
    view.s = view.side * FRAME_FILL / sceneSpan;
  }
  function toScreen(x, y) { return [view.cx + (x - sceneCx) * view.s, view.cy + (y - sceneCy) * view.s]; }

  /* The only computed colour of the page: the language hue at the tissue saturation. */
  function tissue(facts, light, alpha) {
    return 'hsla(' + LANGUAGE_HUE[facts.language] + ',' + TISSUE_SATURATION + '%,' + light.toFixed(1) + '%,' + alpha + ')';
  }
  function yearLight(year) {
    if (years.last === years.first) { return (STRATA_LIGHT_FIRST + STRATA_LIGHT_LAST) / 2; }
    return STRATA_LIGHT_FIRST + (STRATA_LIGHT_LAST - STRATA_LIGHT_FIRST) * (year - years.first) / (years.last - years.first);
  }

  /* Share of the cell drawn solid, and the texture of the rest. */
  function texture(facts) {
    if (facts.language === 'php') {
      var marks = (facts.namespace ? 1 : 0) + (facts.strict_types ? 1 : 0);
      return marks === 2 ? { solid: 1, rest: null } : { solid: 0, rest: marks === 1 ? 'hatched' : 'dotted' };
    }
    if (facts.language === 'python') {
      if (facts.functions === 0) { return { solid: 1, rest: null }; }
      return { solid: facts.annotated_functions / facts.functions, rest: 'dotted' };
    }
    if (facts.typed) { return facts.loose_marks === 0 ? { solid: 1, rest: null } : { solid: 0, rest: 'hatched' }; }
    return { solid: 0, rest: 'dotted' };
  }

  function drawTexture(g, x, y, rr, kind, solid) {
    g.save();
    g.beginPath();
    if (solid > 0) {
      g.moveTo(x, y);
      g.arc(x, y, rr, -Math.PI / 2 + solid * TAU, -Math.PI / 2 + TAU);
      g.closePath();
    } else {
      g.arc(x, y, rr, 0, TAU);
    }
    g.clip();
    g.fillStyle = TEXTURE;
    g.strokeStyle = TEXTURE;
    g.lineWidth = 0.7;
    var step = TEXTURE_STEP;
    if (kind === 'hatched') {
      g.beginPath();
      for (var d = -2 * rr; d <= 2 * rr; d += step) {
        g.moveTo(x + d - rr, y + rr);
        g.lineTo(x + d + rr, y - rr);
      }
      g.stroke();
    } else {
      g.beginPath();
      for (var gx = x - rr; gx <= x + rr; gx += step) {
        for (var gy = y - rr; gy <= y + rr; gy += step) {
          g.moveTo(gx + 0.6, gy);
          g.arc(gx, gy, 0.6, 0, TAU);
        }
      }
      g.fill();
    }
    g.restore();
  }

  function drawCell(g, cell, x, y, rr) {
    var facts = cell.facts;
    var stamps = Object.keys(cell.line_years).map(Number).sort(function (a, b) { return a - b; });
    if (stamps.length === 0 || years === null) {
      g.beginPath();
      g.arc(x, y, rr, 0, TAU);
      g.fillStyle = tissue(facts, UNBLAMED_LIGHT, 1);
      g.fill();
    } else {
      /* Strata: area shares per year, the oldest innermost; drawn from the outside in. */
      var total = stamps.reduce(function (sum, year) { return sum + cell.line_years[year]; }, 0);
      var cumulative = total;
      for (var k = stamps.length - 1; k >= 0; k--) {
        g.beginPath();
        g.arc(x, y, rr * Math.sqrt(cumulative / total), 0, TAU);
        g.fillStyle = tissue(facts, yearLight(stamps[k]), 1);
        g.fill();
        cumulative -= cell.line_years[stamps[k]];
      }
    }
    var tex = texture(facts);
    if (tex.rest !== null && tex.solid < 1 && rr > TEXTURE_STEP) { drawTexture(g, x, y, rr, tex.rest, tex.solid); }

    /* Light grey dots (superglobals + globals) then hollow dots (deprecated calls) on one sunflower. */
    var filled = facts.language === 'php' ? facts.superglobals + facts.globals : 0;
    var hollow = facts.language === 'php' ? facts.deprecated_calls : 0;
    var dots = filled + hollow;
    if (dots > 0) {
      var reach = rr * DOT_REACH;
      var dot = Math.min(rr * 0.14, reach * 0.5 / Math.sqrt(dots));
      for (var i = 0; i < dots; i++) {
        var dist = reach * Math.sqrt((i + 0.5) / dots);
        var px = x + dist * Math.cos(i * GOLDEN_ANGLE);
        var py = y + dist * Math.sin(i * GOLDEN_ANGLE);
        g.beginPath();
        g.arc(px, py, dot, 0, TAU);
        if (i < filled) {
          g.fillStyle = MARK + '0.8)';
          g.fill();
        } else {
          g.strokeStyle = MARK + '0.9)';
          g.lineWidth = Math.max(0.4, dot * 0.35);
          g.stroke();
        }
      }
    }

    /* Surface wear: grains along the edge; grains per pixel of circumference grow with sqrt(changes). */
    var grains = Math.round(WEAR * Math.sqrt(cell.changes) * TAU * rr);
    if (grains > 0) {
      var grain = Math.max(0.35, rr * 0.025);
      g.fillStyle = MARK + '0.55)';
      g.beginPath();
      for (var n = 0; n < grains; n++) {
        var angle = n * GOLDEN_ANGLE;
        var depth = rr * (0.86 + 0.12 * ((n * 0.6180339887) % 1));
        var gx2 = x + depth * Math.cos(angle);
        var gy2 = y + depth * Math.sin(angle);
        g.moveTo(gx2 + grain, gy2);
        g.arc(gx2, gy2, grain, 0, TAU);
      }
      g.fill();
    }

    if (cell.test) {
      g.beginPath();
      g.arc(x, y, rr, 0, TAU);
      g.strokeStyle = MARK + '1)';
      g.lineWidth = Math.max(0.8, rr * 0.08);
      g.stroke();
    } else if (cell.test_edges > 0) {
      g.beginPath();
      g.arc(x, y, rr + Math.max(1.2, rr * 0.12), 0, TAU);
      g.strokeStyle = MARK + '0.6)';
      g.lineWidth = 0.5 * Math.sqrt(cell.test_edges);
      g.stroke();
    }
  }

  /* One merged skin per organ: the union of enlarged cell circles, an edge ring under a fill. */
  function drawSkin(g, organ, place) {
    [[SKIN_EDGE, 1.2], [SKIN_FILL, 0]].forEach(function (layer) {
      g.beginPath();
      organ.cells.forEach(function (cell) {
        var p = place(cell.x, cell.y);
        var rr = cell.r * view.s * SKIN_GROW + layer[1];
        g.moveTo(p[0] + rr, p[1]);
        g.arc(p[0], p[1], rr, 0, TAU);
      });
      g.fillStyle = layer[0];
      g.fill();
    });
  }

  function offscreen(w, h) {
    var c = document.createElement('canvas');
    c.width = Math.max(1, Math.ceil(w * dpr));
    c.height = Math.max(1, Math.ceil(h * dpr));
    var g = c.getContext('2d');
    g.setTransform(dpr, 0, 0, dpr, 0, 0);
    return { canvas: c, ctx: g, w: w, h: h };
  }

  /* Static layers, redrawn on resize: the ground (cysts), one layer per body, and the dust above the bodies. */
  var groundLayer = null;
  var bodyLayers = [];
  var dustLayer = null;
  function speckRadius(speck) { return Math.max(DUST_MIN, DUST_SCALE * speck.r * view.s); }
  function speckAt(speck) { return [view.cx + speck.x * view.side, view.cy + speck.y * view.side]; }

  function build() {
    fit();
    groundLayer = offscreen(width, height);
    var g = groundLayer.ctx;
    g.fillStyle = GROUND;
    g.fillRect(0, 0, width, height);
    scene.cysts.forEach(function (cyst) {
      var p = toScreen(cyst.x, cyst.y);
      g.beginPath();
      g.arc(p[0], p[1], cyst.r * view.s, 0, TAU);
      g.fillStyle = CYST_FILL;
      g.fill();
      g.setLineDash([3, 4]);
      g.strokeStyle = CYST_EDGE;
      g.lineWidth = 0.8;
      g.stroke();
      g.setLineDash([]);
    });
    bodyLayers = scene.bodies.map(function (body, index) {
      var half = body.r * view.s * 1.5 + 8;
      var layer = offscreen(2 * half, 2 * half);
      var b = layer.ctx;
      function place(x, y) { return [half + (x - body.x) * view.s, half + (y - body.y) * view.s]; }
      scene.tendons.forEach(function (tendon) {
        if (tendon.body !== index) { return; }
        var a = place(body.organs[tendon.source].x, body.organs[tendon.source].y);
        var c = place(body.organs[tendon.target].x, body.organs[tendon.target].y);
        var mx = (a[0] + c[0]) / 2 - (c[1] - a[1]) * 0.12;
        var my = (a[1] + c[1]) / 2 + (c[0] - a[0]) * 0.12;
        b.beginPath();
        b.moveTo(a[0], a[1]);
        b.quadraticCurveTo(mx, my, c[0], c[1]);
        b.strokeStyle = MARK + '0.25)';
        b.lineWidth = Math.max(0.5, tendon.width * view.s);
        b.lineCap = 'round';
        b.stroke();
      });
      body.organs.forEach(function (organ) { drawSkin(b, organ, place); });
      body.organs.forEach(function (organ) {
        organ.cells.forEach(function (cell) {
          var p = place(cell.x, cell.y);
          drawCell(b, cell, p[0], p[1], cell.r * view.s);
        });
      });
      var centre = toScreen(body.x, body.y);
      return { layer: layer, half: half, x: centre[0], y: centre[1] };
    });
    dustLayer = offscreen(width, height);
    scene.dust.forEach(function (speck) {
      var p = speckAt(speck);
      drawCell(dustLayer.ctx, speck, p[0], p[1], speckRadius(speck));
    });
  }
  window.addEventListener('resize', build);
  build();

  /* Every body breathes with the same period, amplitude and phase. */
  var breath = 1;
  function draw(seconds) {
    breath = 1 + BREATH_AMPLITUDE * Math.sin(TAU * seconds / BREATH_PERIOD);
    ctx.drawImage(groundLayer.canvas, 0, 0, width, height);
    bodyLayers.forEach(function (item) {
      var size = 2 * item.half * breath;
      ctx.drawImage(item.layer.canvas, item.x - item.half * breath, item.y - item.half * breath, size, size);
    });
    ctx.drawImage(dustLayer.canvas, 0, 0, width, height);
  }

  function factsText(facts) {
    if (facts.language === 'php') {
      return 'PHP: namespace ' + (facts.namespace ? 'yes' : 'no') + ', strict_types ' + (facts.strict_types ? 'yes' : 'no') +
        ', superglobals ' + facts.superglobals + ', globals ' + facts.globals +
        ', deprecated calls ' + facts.deprecated_calls + ', includes ' + facts.includes;
    }
    if (facts.language === 'python') {
      return 'Python: functions ' + facts.functions + ', annotated ' + facts.annotated_functions;
    }
    return (facts.language === 'typescript' ? 'TypeScript' : 'JavaScript') + ': typed ' + (facts.typed ? 'yes' : 'no') +
      ', loose marks ' + facts.loose_marks;
  }
  function cellText(cell) {
    var stamps = Object.keys(cell.line_years).map(Number).sort(function (a, b) { return a - b; });
    var yearsText = stamps.length === 0 ? 'none' : stamps.map(function (year) {
      return year + ': ' + cell.line_years[year];
    }).join(', ');
    return [cell.path, 'lines: ' + cell.lines, 'changes: ' + cell.changes, 'line years: ' + yearsText,
      factsText(cell.facts), 'internal edges: ' + cell.edges];
  }

"""

_ANATOMY_HOVER = r"""      var mx = event.clientX;
      var my = event.clientY;
      var lines = null;
      /* Dust is drawn above the bodies, so a speck over a body is hit first. */
      scene.dust.forEach(function (speck) {
        if (lines !== null) { return; }
        var p = speckAt(speck);
        if (Math.hypot(mx - p[0], my - p[1]) <= speckRadius(speck) + 2) { lines = cellText(speck); }
      });
      for (var b = scene.bodies.length - 1; b >= 0 && lines === null; b--) {
        var item = bodyLayers[b];
        var body = scene.bodies[b];
        /* Undo the breathing, then the frame scale: pointer in scene units. */
        var lx = body.x + (mx - item.x) / breath / view.s;
        var ly = body.y + (my - item.y) / breath / view.s;
        var skin = null;
        body.organs.forEach(function (organ) {
          organ.cells.forEach(function (cell) {
            var d = Math.hypot(lx - cell.x, ly - cell.y);
            if (lines === null && d <= cell.r) { lines = cellText(cell); }
            if (skin === null && d <= cell.r * SKIN_GROW) { skin = organ; }
          });
        });
        if (lines === null && skin !== null) {
          var organLines = skin.cells.reduce(function (sum, cell) { return sum + cell.lines; }, 0);
          lines = ['organ', 'files: ' + skin.cells.length + ', lines: ' + organLines];
        }
      }
      scene.cysts.forEach(function (cyst) {
        if (lines !== null) { return; }
        var p = toScreen(cyst.x, cyst.y);
        if (Math.hypot(mx - p[0], my - p[1]) <= cyst.r * view.s) {
          var cystLines = cyst.files.reduce(function (sum, file) { return sum + file.lines; }, 0);
          lines = ['foreign: ' + cyst.key, 'files: ' + cyst.files.length + ', lines: ' + cystLines];
        }
      });
      if (lines === null) { hoverBox.style.display = 'none'; return; }
      hoverBox.textContent = lines.join('\n');
      hoverBox.style.whiteSpace = 'pre-line';
      hoverBox.style.display = 'block';
      hoverBox.style.left = Math.min(event.clientX + 14, Math.max(0, window.innerWidth - 340)) + 'px';
      hoverBox.style.top = (event.clientY + 14) + 'px';
    });
  }
})();
"""

_ANATOMY_JS = (
    JS_HEAD
    + _ANATOMY_CONSTANTS.replace("__LANGUAGE_HUE__", json.dumps(LANGUAGE_HUES)).replace(
        "__TISSUE_SATURATION__", str(TISSUE_SATURATION)
    )
    + JS_RESIZE
    + _ANATOMY_DRAW
    + JS_FRAME
    + JS_HOVER_OPEN
    + _ANATOMY_HOVER
)


def hud_lines(scene: AnatomyScene) -> list[str]:
    """HUD lines: raw counts only, no adjective and no ranking."""
    counts = scene.counts
    if counts.lines:
        foreign = f"{100 * counts.foreign_lines / counts.lines:.1f}% ({counts.foreign_lines} of {counts.lines})"
    else:
        foreign = "0 of 0"
    years = f"{scene.blame_years.first}-{scene.blame_years.last}" if scene.blame_years is not None else "none"
    return [
        f"files scanned: {counts.files}",
        f"edges: {counts.edges}",
        f"bodies: {counts.bodies}",
        f"organs in the largest body: {counts.organs_in_largest_body}",
        f"dust files: {counts.dust}",
        f"foreign share of lines: {foreign}",
        f"blame years: {years}",
        f"unresolved references: {scene.unresolved_references}",
    ]


def legend_markup() -> str:
    """The legend: one line per visual property, the tissue hue line with one swatch per language."""
    items = []
    for name, meaning in LEGEND_ROWS:
        line = f"<b>{html.escape(name)}</b>: {html.escape(meaning)}"
        if name == "Tissue hue":
            line += "".join(
                f'<span class="swatch" style="background: hsl({LANGUAGE_HUES[key]}, {TISSUE_SATURATION}%, '
                f'{SWATCH_LIGHTNESS}%)"></span>{label}'
                for key, label in LANGUAGE_NAMES.items()
            )
        items.append(f"      <li>{line}</li>")
    return '  <div id="legend">\n    <ul>\n' + "\n".join(items) + "\n    </ul>\n  </div>\n"


def generate_anatomy_html(scene: AnatomyScene) -> str:
    """Generate the self-contained HTML5 page of the ``anatomy`` portrait.

    The page embeds the scene JSON and draws only from it. The legend is always shown; with
    ``scene.caption`` false the page has no HUD and no hover box.

    Raises:
        TypeError: If scene is not an AnatomyScene.
    """
    if not isinstance(scene, AnatomyScene):
        raise TypeError(f"Expected AnatomyScene, got {type(scene).__name__}")
    return page_html(
        scene,
        "Anatomy",
        _ANATOMY_JS,
        hud_lines=hud_lines(scene),
        extra_css=_ANATOMY_CSS,
        extra_markup=legend_markup(),
    )
