[[[
const card = this;
const CAL = __CALENDAR__, BINS = __BIN_CALENDAR__, COLOURS = __COLOURS__, CAP = __CAP__;
const C = window.__homeHubCal || (window.__homeHubCal = {t: 0, ev: null, bins: null, busy: false});
if (!C.busy && Date.now() - C.t > 300000) {
  C.busy = true;
  const s = new Date(); s.setHours(0,0,0,0);
  const iso = d => d.toISOString();
  const q = d => '?start=' + iso(s) + '&end=' + iso(new Date(s.getTime() + d*864e5));
  Promise.all([
    hass.callApi('GET', 'calendars/' + CAL + q(3)),
    BINS ? hass.callApi('GET', 'calendars/' + BINS + q(21)) : Promise.resolve([])
  ]).then(([ev, bins]) => { C.ev = ev; C.bins = bins; C.t = Date.now(); try { card.requestUpdate('preview'); } catch (e) {} })
    .catch(() => { C.t = Date.now() - 240000; })
    .finally(() => { C.busy = false; });
}
const head = '<div style="display:flex;justify-content:space-between;align-items:baseline;gap:12px;margin-bottom:4px"><div style="display:flex;align-items:center;gap:8px;font-size:17px;font-weight:600"><ha-icon icon="mdi:calendar-heart" style="--mdc-icon-size:20px;color:#F5A524"></ha-icon>Coming up</div><div style="font-size:13px;opacity:.7;white-space:nowrap">Next 3 days</div></div>';
if (!C.ev) return '<div style="text-align:left">' + head + '<div style="opacity:.5;padding:12px 0">Loading…</div></div>';

const now = new Date();
const startOf = d => { const x = new Date(d); x.setHours(0,0,0,0); return x; };
const parse = e => {
  const allDay = !!e.start.date;
  const st = allDay ? new Date(e.start.date + 'T00:00:00') : new Date(e.start.dateTime);
  const en = allDay ? new Date(e.end.date + 'T00:00:00') : new Date(e.end.dateTime);
  return {allDay, st, en, title: (e.summary || '').trim()};
};
const who = t => { const l = t.toLowerCase();
  for (const [name, colour] of COLOURS) { if (name && l.includes(name)) return colour; }
  return '#F5A524'; };
const hm = d => d.toLocaleTimeString([], {hour:'2-digit', minute:'2-digit', hour12:false});
const evs = C.ev.map(parse).filter(e => e.en > now).sort((a,b) => (a.st - b.st) || (b.allDay - a.allDay));
const today = startOf(now);
const days = [0,1,2].map(i => new Date(today.getTime() + i*864e5));
const label = (d, i) => i === 0 ? 'Today' : i === 1 ? 'Tomorrow' : d.toLocaleDateString([], {weekday:'long'});
let out = ''; let shown = 0; let hidden = 0;
days.forEach((d, i) => {
  const next = new Date(d.getTime() + 864e5);
  const all = evs.filter(e => e.st < next && e.en > d); const list = all.slice(0, Math.max(0, CAP - shown)); hidden += all.length - list.length; shown += list.length; if (!list.length && all.length) return;
  out += '<div style="margin-top:' + (i ? 14 : 8) + 'px">'
    + '<div style="display:flex;align-items:baseline;gap:8px;margin-bottom:6px">'
    + '<span style="font-size:13px;font-weight:700;letter-spacing:1.5px;text-transform:uppercase;color:' + (i === 0 ? '#F5A524' : 'var(--primary-text-color)') + '">' + label(d, i) + '</span>'
    + '<span style="font-size:12px;opacity:.45">' + d.toLocaleDateString([], {day:'numeric', month:'short'}) + '</span></div>';
  if (!list.length) out += '<div style="font-size:14px;opacity:.4;padding:2px 0 2px 2px">Nothing planned</div>';
  list.forEach(e => {
    const c = who(e.title);
    const time = e.allDay || e.st < d ? '<span style="font-size:11px;font-weight:600;opacity:.7">ALL DAY</span>'
      : '<span style="font-size:14px;font-weight:600">' + hm(e.st) + '</span><span style="font-size:11px;opacity:.45">' + hm(e.en) + '</span>';
    out += '<div style="display:flex;align-items:center;gap:12px;padding:8px 10px;margin-bottom:5px;border-radius:12px;background:rgba(255,255,255,0.04)">'
      + '<div style="width:44px;display:flex;flex-direction:column;align-items:flex-start;flex-shrink:0;line-height:1.25">' + time + '</div>'
      + '<div style="width:3px;align-self:stretch;border-radius:2px;background:' + c + ';flex-shrink:0"></div>'
      + '<div style="font-size:14.5px;line-height:1.3;white-space:normal;overflow:hidden">' + e.title.replace(/</g,'&lt;') + '</div></div>';
  });
  out += '</div>';
});
if (hidden) out += '<div style="font-size:13px;opacity:.55;margin-top:6px;padding-left:2px">+' + hidden + ' more · tap to see the week</div>';
const bin = (C.bins || []).map(parse).filter(e => e.en > now).sort((a,b) => a.st - b.st)[0];
if (bin) {
  const dd = Math.round((startOf(bin.st) - today) / 864e5);
  const when = dd === 0 ? 'today' : dd === 1 ? 'tomorrow' : bin.st.toLocaleDateString([], {weekday:'long', day:'numeric', month:'short'});
  out += '<div style="display:flex;align-items:center;gap:8px;margin-top:12px;padding-top:10px;border-top:1px solid rgba(255,255,255,0.08);font-size:13px;opacity:.8">'
    + '<ha-icon icon="mdi:trash-can-outline" style="--mdc-icon-size:18px;color:#68D391"></ha-icon>'
    + '<span>' + bin.title.replace(/</g,'&lt;') + ' · <b>' + when + '</b></span></div>';
}
return '<div style="text-align:left">' + head + out + '</div>';
]]]
