[[[
  const PRAYERS = __PRAYERS__;
  const d = new Date();
  const t = d.toLocaleTimeString([], {hour:'2-digit', minute:'2-digit', hour12:false});
  const ds = d.toLocaleDateString([], {weekday:'long', day:'numeric', month:'long'});
  let p = '';
  for (const [n, e] of PRAYERS) {
    const s = states[e]; const pt = s && !isNaN(new Date(s.state)) ? new Date(s.state) : null;
    if (pt && pt > d) { p = n + ' at ' + pt.toLocaleTimeString([], {hour:'2-digit', minute:'2-digit', hour12:false}); break; }
  }
  return '<div style="text-align:center;display:flex;flex-direction:column;align-items:center;gap:10px">'
    + '<div style="font-size:150px;font-weight:200;line-height:1;letter-spacing:-4px;color:rgba(255,255,255,0.30)">' + t + '</div>'
    + '<div style="font-size:20px;letter-spacing:2px;color:rgba(255,255,255,0.18)">' + ds + '</div>'
    + (p ? '<div style="display:block;font-size:17px;margin-top:6px;color:rgba(245,165,36,0.32)"><ha-icon icon="mdi:mosque" style="--mdc-icon-size:18px;vertical-align:-3px;margin-right:6px"></ha-icon>Next: ' + p + '</div>' : '')
    + '</div>';
]]]
