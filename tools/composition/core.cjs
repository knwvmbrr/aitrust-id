/* Offline composition observation/1.0.0. No text, identity or provenance verdict. */
(function (root) {
  'use strict';
  const VERSION = 'composition-observation/1.0.0';
  const MAX_EVENTS = 10000, MAX_LENGTH = 20000, MAX_MS = 1800000;
  const round = x => Math.round(x * 100) / 100;
  const cv = values => {
    if (values.length < 3) return null;
    const mean = values.reduce((a, b) => a + b, 0) / values.length;
    if (!mean) return null;
    return Math.round(Math.sqrt(values.reduce((a, b) => a + (b - mean) ** 2, 0) / values.length) / mean * 10) / 10;
  };
  function create() {
    let s;
    function reset() {
      s = { running: false, started: null, last: null, stopped: null, events: 0,
        suppressed: true, reason: 'input_mode_not_physical', keys: new Map(),
        dwell: [], flight: [], lastUp: null, lastKey: null, lastActivity: null, lastEdit: null,
        focusedEdits: 0, longEditGaps: 0, deleted: 0, rewritten: 0,
        length: 0, caret: 0, nonadjacent: 0, bins: Array(8).fill(0), pastes: 0,
        focused: false, visible: true, focusedMs: 0, hiddenMs: 0, intervals: 0 };
    }
    function suppress(reason) {
      s.suppressed = true; s.reason = reason;
      s.keys.clear(); s.dwell = []; s.flight = []; s.lastUp = null; s.lastKey = null;
    }
    function advance(at) {
      if (!Number.isFinite(at) || at < 0 || (s.last !== null && at < s.last)) throw Error('Invalid monotonic clock');
      if (s.last !== null && s.running) {
        const delta = at - s.last;
        if (s.focused && s.visible) s.focusedMs += delta;
        if (!s.visible) s.hiddenMs += delta;
      }
      s.last = at;
    }
    function stop(at, reason = 'paused') {
      if (!s.running) return;
      const boundary = Math.min(at, s.started + MAX_MS);
      advance(Math.max(s.last, boundary)); s.running = false; s.stopped = reason;
      s.keys.clear(); s.lastUp = null; s.lastKey = null;
    }
    function start(at, mode = 'unknown') {
      if (!['unknown', 'assistive', 'physical'].includes(mode)) throw Error('Unknown input mode');
      if (s.started !== null) throw Error('Reset before starting a new session');
      advance(at); s.started = at; s.running = true;
      s.suppressed = mode !== 'physical'; s.reason = s.suppressed ? 'input_mode_not_physical' : null;
    }
    function event(e) {
      if (!s.running) return false;
      if (!e || typeof e !== 'object' || !['keyDown','keyUp','edit','caret','focus','visibility','composition','assistive'].includes(e.kind)) throw Error('Unknown event');
      if (!Number.isFinite(e.at) || e.at < s.last) throw Error('Invalid monotonic clock');
      if (e.at - s.started >= MAX_MS || s.events >= MAX_EVENTS) { stop(e.at, 'limit_reached'); return false; }
      // Validate before any mutation; malformed data cannot create a partial observation.
      if (['keyDown','keyUp'].includes(e.kind) && (typeof e.code !== 'string' || !/^[A-Za-z0-9]{1,32}$/.test(e.code) || typeof e.trusted !== 'boolean')) throw Error('Invalid key event');
      if (e.kind === 'caret' && (!Number.isSafeInteger(e.position) || e.position < 0 || e.position > s.length)) throw Error('Invalid caret');
      if (e.kind === 'edit' && (![e.before,e.after,e.position,e.removed,e.added].every(v => Number.isSafeInteger(v) && v >= 0 && v <= MAX_LENGTH) || e.before !== s.length || e.position + e.removed > e.before || e.after !== e.before - e.removed + e.added || !['keyboard','paste','composition','replacement','unknown'].includes(e.input))) throw Error('Invalid edit');
      if (['focus','visibility'].includes(e.kind) && typeof e.value !== 'boolean') throw Error('Invalid visibility event');
      advance(e.at); s.events++;
      if (e.kind === 'keyDown' && e.trusted) s.lastActivity = e.at;
      if (e.kind === 'caret') {
        s.bins[Math.min(7, Math.floor(e.position / Math.max(1,s.length) * 8))]++;
      }
      if (e.kind === 'assistive' || e.kind === 'composition') suppress('assistive_or_composition_input');
      if (e.kind === 'focus') { s.focused = e.value; s.intervals++; if (!e.value) { s.keys.clear(); s.lastUp = null; } }
      if (e.kind === 'visibility') { s.visible = e.value; if (!e.value) { s.keys.clear(); s.lastUp = null; } }
      if (e.kind === 'keyDown' && !s.suppressed) {
        if (!e.trusted || s.keys.size >= 32) suppress('untrusted_or_unsupported_key_input');
        else if (!e.repeat && !s.keys.has(e.code)) {
          s.keys.set(e.code, e.at); s.lastKey = e.at;
          if (s.lastUp !== null) s.flight.push(e.at - s.lastUp);
        }
      }
      if (e.kind === 'keyUp' && !s.suppressed) {
        if (!e.trusted || !s.keys.has(e.code)) suppress('unmatched_or_untrusted_key_input');
        else { s.dwell.push(e.at - s.keys.get(e.code)); s.keys.delete(e.code); s.lastUp = e.at; }
      }
      if (e.kind === 'edit') {
        if (e.input !== 'keyboard' && e.input !== 'paste') suppress('assistive_or_unknown_edit_input');
        if (e.input === 'keyboard' && s.lastKey === null) suppress('edit_without_observed_keyboard');
        s.deleted += e.removed; s.rewritten += Math.min(e.removed, e.added);
        if (Math.abs(e.position - s.caret) > 1) s.nonadjacent++;
        s.bins[Math.min(7, Math.floor(e.position / Math.max(1, e.before) * 8))]++;
        if (e.input === 'paste' && e.added >= 64 && (s.lastActivity === null || e.at - s.lastActivity >= 2000)) s.pastes++;
        if (s.focused && s.visible) s.focusedEdits++;
        if (s.lastEdit !== null && e.at - s.lastEdit >= 2000) s.longEditGaps++;
        s.lastEdit = e.at;
        s.length = e.after; s.caret = e.position + e.added;
      }
      return true;
    }
    function snapshot() {
      const count = s.bins.reduce((a,b) => a+b,0);
      const entropy = count ? -s.bins.reduce((a,n) => n ? a + n/count*Math.log2(n/count) : a,0) : null;
      return { schema_version: 1, record_type: 'composition_observation', method: VERSION,
        status: s.started === null ? 'not_started' : s.running ? 'observing' : s.stopped,
        tags: [], authorship_inference: false, independent_accuracy_evidence: false,
        units: 'UTF-16 code units; monotonic milliseconds; eight caret bins',
        event_count: s.events, final_length: s.length,
        timing: { signal: 'sig.keystroke_liveness.v1', status: s.suppressed ? 'suppressed' : 'observed', reason: s.reason,
          dwell_cv: s.suppressed ? null : cv(s.dwell), flight_cv: s.suppressed ? null : cv(s.flight), samples: s.suppressed ? 0 : s.dwell.length },
        revision: { signal: 'sig.revision_churn.v1', deleted: s.deleted, rewritten: s.rewritten,
          churn: s.length ? round((s.deleted + s.rewritten) / s.length) : null, nonadjacent_edits: s.nonadjacent },
        caret: { signal: 'sig.compose_monotonicity.v1', entropy_bits: entropy === null ? null : round(entropy) },
        focus: { signal: 'sig.attention_shape.v1', visible_focused_ms: round(s.focusedMs), hidden_ms: round(s.hiddenMs), changes: s.intervals, visible_focused_edits: s.focusedEdits, edit_gaps_at_least_2000_ms: s.longEditGaps, reading_inferred: false },
        insertion: { signal: 'sig.paste_burst.v1', bursts: s.pastes, minimum_units: 64, preceding_key_window_ms: 2000, origin_inferred: false },
        safety: { signal: 'sig.assistive_input.v1', timing_suppressed: s.suppressed, detection_complete: false },
        limits: { maximum_events: MAX_EVENTS, maximum_length: MAX_LENGTH, maximum_ms: MAX_MS },
        warning: 'Local observations can be forged and may link sessions. No identity, authorship, attention or content-truth verdict.' };
    }
    reset(); return Object.freeze({start, event, pause: stop, reset, snapshot});
  }
  const api = Object.freeze({create, VERSION});
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
  else root.AITrustComposition = api;
})(globalThis);
