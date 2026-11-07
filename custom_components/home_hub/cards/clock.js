[[[
  const d = new Date();
  const day = d.toLocaleDateString([], {weekday:'long'}).toUpperCase();
  const time = d.toLocaleTimeString([], {hour:'2-digit', minute:'2-digit'});
  const date = d.toLocaleDateString([], {day:'numeric', month:'long', year:'numeric'});
  return `<div style="display:flex;flex-direction:column;gap:8px;text-align:left">
    <div style="font-size:13px;letter-spacing:4px;color:#F5A524;font-weight:600">${day}</div>
    <div style="font-size:54px;font-weight:700;line-height:1;letter-spacing:-2px">${time}</div>
    <div style="font-size:16px;opacity:.65">${date}</div></div>`;
]]]
