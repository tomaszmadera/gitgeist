"""Standalone HTML5/Canvas template generator for live preview."""

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
from gitgeist.schemas.live_state import CreatureScene, OrbitsScene


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

# ---------------------------------------------------------------------------------------------
# The character ``creature`` page (spec docs/features/live-renderer-v2/character-spec.md).
# It draws only from the embedded CreatureScene. Every frame is a pure function of the scene and
# the animation time; all randomness comes from one mulberry32 generator seeded with the effective
# seed modulo 2^32. The seeded parts are drawn in a fixed order: torso, limbs, cracks, motes, tendrils.
# ---------------------------------------------------------------------------------------------

_CREATURE_CONSTANTS = r"""  var body = scene.body;
  var TAU = Math.PI * 2;
  var GROUND = '#121218';
  var TORSO_LIGHTNESS = 45;
  var SEGMENT_LIGHTNESS = 38;
  var RING_WIDTH_MIN = 0.5;
  var RING_WIDTH_SPAN = 3.5;
  var TENDRIL_LENGTH = 0.12;
  var TENDRIL_SPAN = 0.18;
  var TENDRIL_BEND_DEG = 60;
  var TENDRIL_WAVE = 0.25;
  var JOINT_SWAY_SHIFT = 0.6;
  var BREATHING = 0.04;
  var CRACK_LENGTH = 0.15;
  var FLICKER_MIN_HZ = 0.5;
  var FLICKER_SPAN_HZ = 2.5;
  var RECENT_LOOP_SHARE = 0.1;
  var RECENT_MONTHS = 3;
  var OUTLINE_POINTS = 36;
  var HUD_STRIP = 120;

"""

_CREATURE_PARTS = r"""  /* Seeded, frame-stable parts of the drawing. */
  function noiseRing() {
    var ring = [];
    for (var k = 0; k < OUTLINE_POINTS; k++) { ring.push(rand() * 2 - 1); }
    return ring;
  }
  var torsoPart = { noise: noiseRing(), hatchAngle: rand() * Math.PI, breathPhase: rand() * TAU };
  var limbParts = body.limbs.map(function (limb) {
    return { limb: limb, noise: noiseRing(), hatchAngle: rand() * Math.PI, breathPhase: rand() * TAU, joints: [] };
  });
  var cracks = spec.cracks.marks.map(function (mark) {
    var offsets = [];
    for (var k = 0; k < 4; k++) { offsets.push(rand() * 2 - 1); }
    return { mark: mark, offsets: offsets };
  });
  var totalShare = masses.reduce(function (sum, mass) { return sum + mass.file_share; }, 0);
  var motes = [];
  for (var d = 0; d < spec.footprint.element_count; d++) {
    var pick = rand() * totalShare;
    var owner = -1;
    for (var m = 0; m < masses.length && owner < 0; m++) {
      pick -= masses[m].file_share;
      if (pick <= 0) { owner = m; }
    }
    if (owner < 0 && masses.length > 0) { owner = masses.length - 1; }
    motes.push({
      owner: owner, angle: rand() * TAU, dist: Math.sqrt(rand()) * 0.85, along: rand(),
      side: rand() * 2 - 1, phase: rand() * TAU, reach: 0.01 + rand() * 0.02
    });
  }
  var tendrils = spec.strands.paths.map(function (path) { return { path: path }; });

"""

_CREATURE_DRAW = r"""  function ellipseOutline(x, y, rx, ry, rot, noise) {
    var jitter = spec.edge.jitter;
    var cos = Math.cos(rot);
    var sin = Math.sin(rot);
    var pts = [];
    for (var k = 0; k < OUTLINE_POINTS; k++) {
      var a = k / OUTLINE_POINTS * TAU;
      var f = 1 + jitter * noise[k];
      var lx = rx * f * Math.cos(a);
      var ly = ry * f * Math.sin(a);
      pts.push([x + lx * cos - ly * sin, y + lx * sin + ly * cos]);
    }
    ctx.beginPath();
    var last = pts[pts.length - 1];
    ctx.moveTo((last[0] + pts[0][0]) / 2, (last[1] + pts[0][1]) / 2);
    for (var i = 0; i < pts.length; i++) {
      var next = pts[(i + 1) % pts.length];
      ctx.quadraticCurveTo(pts[i][0], pts[i][1], (pts[i][0] + next[0]) / 2, (pts[i][1] + next[1]) / 2);
    }
    ctx.closePath();
  }

  function ellipseRadius(rx, ry, psi) {
    return rx * ry / Math.max(1e-9, Math.hypot(ry * Math.cos(psi), rx * Math.sin(psi)));
  }

  function hatch(x, y, r, angle, hue) {
    var coverage = spec.hatching.coverage;
    if (coverage <= 0.005 || r <= 2) { return; }
    var spacing = 1 / coverage;
    var dx = Math.cos(angle);
    var dy = Math.sin(angle);
    ctx.strokeStyle = hsl(hue, saturation, 80, 0.55);
    ctx.lineWidth = 1;
    ctx.beginPath();
    for (var o = -r; o <= r; o += spacing) {
      var ox = x - dy * o;
      var oy = y + dx * o;
      ctx.moveTo(ox - dx * r, oy - dy * r);
      ctx.lineTo(ox + dx * r, oy + dy * r);
    }
    ctx.stroke();
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
    var torso = body.torso;

    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    ctx.shadowBlur = 0;
    ctx.fillStyle = GROUND;
    ctx.fillRect(0, 0, width, height);
    layout = [];

    /* tendrils (strands): thin lines growing out of the torso outline, each waving on its own phase */
    var tendrilRoots = [];
    if (torso !== null) {
      var torsoHue = masses[torso.mass_index].hue;
      var rot = torso.rotation_deg * Math.PI / 180;
      tendrils.forEach(function (tendril) {
        var path = tendril.path;
        var psi = path.phase * TAU;
        var r = ellipseRadius(torso.rx, torso.ry, psi);
        var px = r * Math.cos(psi);
        var py = r * Math.sin(psi);
        var rx0 = cx + (torso.x + px * Math.cos(rot) - py * Math.sin(rot)) * R;
        var ry0 = cy + (torso.y + px * Math.sin(rot) + py * Math.cos(rot)) * R;
        var dir = rot + psi;
        var len = (TENDRIL_LENGTH + TENDRIL_SPAN * Math.abs(path.curvature)) * R;
        var bend = path.curvature * TENDRIL_BEND_DEG * Math.PI / 180;
        var wave = Math.sin(TAU * 0.5 * speed * t + path.phase * TAU) * TENDRIL_WAVE * len;
        var mx = rx0 + Math.cos(dir) * len * 0.5 - Math.sin(dir) * wave;
        var my = ry0 + Math.sin(dir) * len * 0.5 + Math.cos(dir) * wave;
        var tx = rx0 + Math.cos(dir + bend) * len;
        var ty = ry0 + Math.sin(dir + bend) * len;
        ctx.strokeStyle = hsl(torsoHue, saturation, 68, 0.8);
        ctx.lineWidth = 1.5;
        ctx.beginPath();
        ctx.moveTo(rx0, ry0);
        ctx.quadraticCurveTo(mx, my, tx, ty);
        ctx.stroke();
        ctx.fillStyle = hsl(torsoHue, saturation, 85, 0.9);
        ctx.beginPath();
        ctx.arc(tx, ty, 1.8, 0, TAU);
        ctx.fill();
      });
    }

    /* limb segments: forward kinematics from the root, root to tip, limb by limb */
    limbParts.forEach(function (part) {
      var limb = part.limb;
      var mass = masses[limb.mass_index];
      var breathe = 1 + BREATHING * amp * Math.sin(TAU * speed * t + part.breathPhase);
      var x = cx + limb.root_x * R;
      var y = cy + limb.root_y * R;
      var heading = limb.root_angle_deg;
      part.joints = [[x, y, limb.segments[0].half_width * R * breathe]];
      limb.segments.forEach(function (segment, j) {
        heading += segment.bend_deg
          + limb.sway_amplitude_deg * Math.sin(TAU * speed * t + limb.sway_phase * TAU + JOINT_SWAY_SHIFT * j);
        var nx = x + segment.length * R * Math.cos(heading * Math.PI / 180);
        var ny = y + segment.length * R * Math.sin(heading * Math.PI / 180);
        var w0 = part.joints[j][2];
        var w1 = segment.half_width * R * breathe;
        var dx = nx - x;
        var dy = ny - y;
        var d = Math.max(1e-9, Math.hypot(dx, dy));
        var qx = -dy / d;
        var qy = dx / d;
        var fill = hsl(mass.hue, saturation, SEGMENT_LIGHTNESS, 1);
        ctx.shadowColor = fill;
        ctx.shadowBlur = spec.edge.blur_px * dpr;
        ctx.fillStyle = fill;
        ctx.beginPath();
        ctx.moveTo(x + qx * w0, y + qy * w0);
        ctx.lineTo(nx + qx * w1, ny + qy * w1);
        ctx.lineTo(nx - qx * w1, ny - qy * w1);
        ctx.lineTo(x - qx * w0, y - qy * w0);
        ctx.closePath();
        ctx.fill();
        ctx.beginPath();
        ctx.arc(nx, ny, w1, 0, TAU);
        ctx.fill();
        ctx.shadowBlur = 0;
        ctx.strokeStyle = hsl(mass.hue, saturation, SEGMENT_LIGHTNESS + 14, 0.9);
        ctx.lineWidth = 1;
        ctx.beginPath();
        ctx.moveTo(x + qx * w0, y + qy * w0);
        ctx.lineTo(nx + qx * w1, ny + qy * w1);
        ctx.moveTo(x - qx * w0, y - qy * w0);
        ctx.lineTo(nx - qx * w1, ny - qy * w1);
        ctx.stroke();
        ctx.save();
        ctx.beginPath();
        ctx.moveTo(x + qx * w0, y + qy * w0);
        ctx.lineTo(nx + qx * w1, ny + qy * w1);
        ctx.lineTo(nx - qx * w1, ny - qy * w1);
        ctx.lineTo(x - qx * w0, y - qy * w0);
        ctx.closePath();
        ctx.clip();
        hatch((x + nx) / 2, (y + ny) / 2, Math.max(w0, w1) + d / 2, part.hatchAngle, mass.hue);
        ctx.restore();
        x = nx;
        y = ny;
        part.joints.push([x, y, w1]);
      });
      part.pad = { x: x, y: y, r: limb.pad_radius * R * breathe };
    });

    /* torso, with its growth rings (oldest innermost) and hatching */
    if (torso !== null) {
      var tm = masses[torso.mass_index];
      var tb = 1 + BREATHING * amp * Math.sin(TAU * speed * t + torsoPart.breathPhase);
      var tx0 = cx + torso.x * R;
      var ty0 = cy + torso.y * R;
      var trx = torso.rx * R * tb;
      var tryy = torso.ry * R * tb;
      var trot = torso.rotation_deg * Math.PI / 180;
      var tfill = hsl(tm.hue, saturation, TORSO_LIGHTNESS, 1);
      ctx.shadowColor = tfill;
      ctx.shadowBlur = spec.edge.blur_px * dpr;
      ctx.fillStyle = tfill;
      ellipseOutline(tx0, ty0, trx, tryy, trot, torsoPart.noise);
      ctx.fill();
      ctx.shadowBlur = 0;
      ctx.strokeStyle = hsl(tm.hue, saturation, TORSO_LIGHTNESS + 18, 1);
      ctx.lineWidth = 1.2;
      ctx.stroke();
      var rings = spec.rings.thickness;
      var maxWidth = tryy / (rings.length + 1);
      for (var q = 0; q < rings.length; q++) {
        var lw = Math.min(RING_WIDTH_MIN + RING_WIDTH_SPAN * rings[q], maxWidth);
        if (lw <= 0) { continue; }
        ctx.strokeStyle = hsl(tm.hue, saturation, 72, 0.85);
        ctx.lineWidth = lw;
        ctx.beginPath();
        ctx.ellipse(tx0, ty0, trx * (q + 1) / (rings.length + 1), tryy * (q + 1) / (rings.length + 1), trot, 0, TAU);
        ctx.stroke();
      }
      ctx.save();
      ellipseOutline(tx0, ty0, trx, tryy, trot, torsoPart.noise);
      ctx.clip();
      hatch(tx0, ty0, Math.max(trx, tryy), torsoPart.hatchAngle, tm.hue);
      ctx.restore();
      layout[torso.mass_index] = { torso: true, x: tx0, y: ty0, r: tryy, rx: trx, ry: tryy, rot: trot };
    }

    /* pads: the round end of every limb, the body of its mass */
    limbParts.forEach(function (part) {
      var mass = masses[part.limb.mass_index];
      var pad = part.pad;
      var fill = hsl(mass.hue, saturation, TORSO_LIGHTNESS, 1);
      ctx.shadowColor = fill;
      ctx.shadowBlur = spec.edge.blur_px * dpr;
      ctx.fillStyle = fill;
      ellipseOutline(pad.x, pad.y, pad.r, pad.r, 0, part.noise);
      ctx.fill();
      ctx.shadowBlur = 0;
      ctx.strokeStyle = hsl(mass.hue, saturation, TORSO_LIGHTNESS + 18, 1);
      ctx.lineWidth = 1.2;
      ctx.stroke();
      ctx.save();
      ellipseOutline(pad.x, pad.y, pad.r, pad.r, 0, part.noise);
      ctx.clip();
      hatch(pad.x, pad.y, pad.r, part.hatchAngle, mass.hue);
      ctx.restore();
      layout[part.limb.mass_index] = { limb: part, x: pad.x, y: pad.y, r: pad.r, rx: pad.r, ry: pad.r, rot: 0 };
    });

    /* cracks: short jagged lines at a polar position on their part */
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

    /* focal knot: a bright disc on the part that owns the hotspot (a limb's pad, or the torso) */
    var knot = spec.knot;
    if (knot !== null && layout[knot.mass_index]) {
      var host = layout[knot.mass_index];
      var hostMass = masses[knot.mass_index];
      var unit = hostMass.radius > 0 ? host.r / hostMass.radius : 0;
      var hz = FLICKER_MIN_HZ + FLICKER_SPAN_HZ * knot.flicker;
      var glow = 0.55 + 0.45 * (0.5 + 0.5 * Math.sin(TAU * hz * t));
      ctx.shadowColor = hsl(hostMass.hue, saturation, 85, 1);
      ctx.shadowBlur = 10 * dpr;
      ctx.fillStyle = hsl(hostMass.hue, saturation, 88, glow);
      ctx.beginPath();
      ctx.arc(host.x + knot.offset_x * unit, host.y + knot.offset_y * unit, Math.max(0.5, knot.radius * host.r), 0, TAU);
      ctx.fill();
      ctx.shadowBlur = 0;
    }

    /* motes: small points drifting over the parts in proportion to their file share */
    motes.forEach(function (p) {
      var host = p.owner >= 0 ? layout[p.owner] : null;
      var hue = p.owner >= 0 ? masses[p.owner].hue : null;
      var drift = p.phase + TAU * speed * 0.3 * t;
      var px;
      var py;
      if (host === null || host === undefined) {
        px = cx + Math.cos(p.angle) * p.dist * R * 0.3;
        py = cy + Math.sin(p.angle) * p.dist * R * 0.3;
      } else if (host.torso) {
        var lx = host.rx * p.dist * Math.cos(p.angle);
        var ly = host.ry * p.dist * Math.sin(p.angle);
        px = host.x + lx * Math.cos(host.rot) - ly * Math.sin(host.rot);
        py = host.y + lx * Math.sin(host.rot) + ly * Math.cos(host.rot);
      } else {
        var joints = host.limb.joints;
        var segs = joints.length - 1;
        var pos = p.along * (segs + 1);
        if (pos >= segs) {
          px = host.x + Math.cos(p.angle) * p.dist * host.r;
          py = host.y + Math.sin(p.angle) * p.dist * host.r;
        } else {
          var i = Math.floor(pos);
          var f = pos - i;
          var a = joints[i];
          var b = joints[i + 1];
          var w = (a[2] + (b[2] - a[2]) * f) * 0.8 * p.side;
          var dx = b[0] - a[0];
          var dy = b[1] - a[1];
          var dd = Math.max(1e-9, Math.hypot(dx, dy));
          px = a[0] + dx * f - dy / dd * w;
          py = a[1] + dy * f + dx / dd * w;
        }
      }
      px += Math.cos(drift) * p.reach * R;
      py += Math.sin(drift) * p.reach * R;
      ctx.fillStyle = hsl(hue, saturation, 78, 0.7);
      ctx.fillRect(px - 0.75, py - 0.75, 1.5, 1.5);
    });
  }

"""

_CREATURE_HIT = r"""      var hit = -1;
      var mx = event.clientX;
      var my = event.clientY;
      /* limbs first (they are drawn over the torso), then the torso */
      layout.forEach(function (place, index) {
        if (hit >= 0 || !place || !place.limb) { return; }
        if (Math.hypot(mx - place.x, my - place.y) <= place.r) { hit = index; return; }
        var joints = place.limb.joints;
        for (var i = 0; i + 1 < joints.length; i++) {
          var ax = joints[i][0];
          var ay = joints[i][1];
          var dx = joints[i + 1][0] - ax;
          var dy = joints[i + 1][1] - ay;
          var len2 = Math.max(1e-9, dx * dx + dy * dy);
          var u = Math.max(0, Math.min(1, ((mx - ax) * dx + (my - ay) * dy) / len2));
          var w = joints[i][2] + (joints[i + 1][2] - joints[i][2]) * u;
          if (Math.hypot(mx - (ax + dx * u), my - (ay + dy * u)) <= w) { hit = index; return; }
        }
      });
      if (hit < 0) {
        layout.forEach(function (place, index) {
          if (hit >= 0 || !place || !place.torso) { return; }
          var lx = (mx - place.x) * Math.cos(place.rot) + (my - place.y) * Math.sin(place.rot);
          var ly = -(mx - place.x) * Math.sin(place.rot) + (my - place.y) * Math.cos(place.rot);
          if ((lx / place.rx) * (lx / place.rx) + (ly / place.ry) * (ly / place.ry) <= 1) { hit = index; }
        });
      }
"""

_CREATURE_JS = (
    JS_HEAD + _CREATURE_CONSTANTS + JS_SEED + JS_SCENE_VARS + _CREATURE_PARTS + JS_RESIZE + JS_PULSE
    + _CREATURE_DRAW + JS_FRAME + JS_HOVER_OPEN + _CREATURE_HIT + JS_HOVER_TAIL
)


def generate_creature_html(scene: CreatureScene) -> str:
    """Generate the self-contained HTML5 page of the character ``creature`` portrait.

    The page embeds the scene JSON and draws only from it; with ``scene.caption`` false it has
    no HUD and no hover box.

    Raises:
        TypeError: If scene is not a CreatureScene.
    """
    if not isinstance(scene, CreatureScene):
        raise TypeError(f"Expected CreatureScene, got {type(scene).__name__}")
    return page_html(scene, "Character", _CREATURE_JS)
