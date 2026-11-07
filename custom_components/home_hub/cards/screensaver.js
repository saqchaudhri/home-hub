[[[
  const PRAYERS = __PRAYERS__, DOOR = __DOOR__, OWNER = __OWNER__;
  const d = new Date();
  const t = d.toLocaleTimeString([], {hour:'2-digit', minute:'2-digit'});
  const ds = d.toLocaleDateString([], {weekday:'long', day:'numeric', month:'long'});
  let p = '';
  for (const [n, e] of PRAYERS) {
    const s = states[e]; const pt = s && !isNaN(new Date(s.state)) ? new Date(s.state) : null;
    if (pt && pt > d) { p = n + ' at ' + pt.toLocaleTimeString([], {hour:'2-digit', minute:'2-digit'}); break; }
  }
  const onAir = DOOR && (states[DOOR] || {}).state === 'off';
  return '<div style="text-align:left;display:flex;flex-direction:column;gap:4px">'
    + '<div style="font-size:64px;font-weight:700;line-height:1;letter-spacing:-2px;text-shadow:0 2px 12px rgba(0,0,0,.4)">' + t + '</div>'
    + '<div style="font-size:18px;opacity:.85">' + ds + '</div>'
    + (p ? '<div style="display:block;font-size:16px;color:#F5A524;margin-top:4px"><ha-icon icon="mdi:mosque" style="--mdc-icon-size:18px;vertical-align:-3px;margin-right:6px"></ha-icon>Next: ' + p + '</div>' : '')
    + (onAir
        ? '<div class="onair">'
          + '<span class="onair-word"><span class="onair-dot"></span>ON AIR</span>'
          + '<span class="onair-sep"></span>'
          + '<span class="onair-msg">' + (OWNER ? OWNER + ' is' : 'Someone is') + ' on a work call<br><span style="opacity:.8;font-size:14px">Please keep the noise down</span></span>'
          + '</div>'
        : '')
    + '</div>';
]]]
