[[[
  const list = __PRAYERS__;
  const now = new Date(); let next = -1;
  const rows = list.map(([n,e],i) => { const s = states[e]; const t = s && !isNaN(new Date(s.state)) ? new Date(s.state) : null; if (next < 0 && t && t > now) next = i; return {n, t}; });
  const fmt = t => t ? t.toLocaleTimeString([], {hour:'2-digit', minute:'2-digit'}) : '--:--';
  let sub = list.length ? list[0][0] + ' tomorrow' : '';
  if (next >= 0) { const m = Math.round((rows[next].t - now)/60000); sub = rows[next].n + ' in ' + (m >= 60 ? Math.floor(m/60)+'h ' : '') + (m%60) + 'm'; }
  const body = rows.map((r,i) => { const isNext = i === next, past = next < 0 || i < next;
    return `<div style="display:flex;justify-content:space-between;align-items:center;__ROW_STYLE__;${isNext ? 'background:rgba(245,165,36,.16);color:#F5A524;font-weight:600;box-shadow:0 0 0 1px rgba(245,165,36,.35) inset' : past ? 'opacity:.4' : ''}"><span>${r.n}</span><span>${fmt(r.t)}</span></div>`; }).join('');
  return `<div style="text-align:left">
    <div style="display:flex;justify-content:space-between;align-items:baseline;margin-bottom:12px;gap:12px">
      <div style="display:flex;align-items:center;gap:8px;font-size:17px;font-weight:600"><ha-icon icon="mdi:mosque" style="--mdc-icon-size:20px;color:#F5A524"></ha-icon>Prayer times</div>
      <div style="font-size:13px;opacity:.7;white-space:nowrap">${sub}</div></div>
    <div style="display:flex;flex-direction:column;gap:4px">${body}</div></div>`;
]]]
