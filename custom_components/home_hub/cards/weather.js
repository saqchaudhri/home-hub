[[[
const card = this;
const W = window.__homeHubWx || (window.__homeHubWx = {fc: null, sub: null});
if (!W.sub && hass.connection) {
  W.sub = hass.connection.subscribeMessage(m => { W.fc = m.forecast || []; try { card.requestUpdate('preview'); } catch (e) {} },
    {type: 'weather/subscribe_forecast', forecast_type: 'daily', entity_id: __WEATHER__});
}
const ic = c => 'mdi:' + ({'clear-night':'weather-night','cloudy':'weather-cloudy','fog':'weather-fog','hail':'weather-hail','lightning':'weather-lightning','lightning-rainy':'weather-lightning-rainy','partlycloudy':'weather-partly-cloudy','pouring':'weather-pouring','rainy':'weather-rainy','snowy':'weather-snowy','snowy-rainy':'weather-snowy-rainy','sunny':'weather-sunny','windy':'weather-windy','windy-variant':'weather-windy-variant'}[c] || 'alert-circle-outline');
const label = c => ({'clear-night':'Clear','partlycloudy':'Some cloud','lightning-rainy':'Storms','snowy-rainy':'Sleet','windy-variant':'Windy'}[c] || (c ? c.charAt(0).toUpperCase() + c.slice(1) : ''));
const a = entity.attributes;
const r = n => Math.round(n);
const fc = W.fc || [];
const today = fc[0];
const hilo = today ? '<span style="opacity:.6">H</span> ' + r(today.temperature) + '° <span style="opacity:.6;margin-left:4px">L</span> ' + r(today.templow) + '°' : '';
const days = fc.slice(1, 4).map(d => {
  const dn = new Date(d.datetime).toLocaleDateString([], {weekday:'short'});
  return '<div style="display:flex;flex-direction:column;align-items:center;gap:2px;min-width:40px">'
    + '<span style="font-size:11px;opacity:.55;text-transform:uppercase;letter-spacing:.5px">' + dn + '</span>'
    + '<ha-icon icon="' + ic(d.condition) + '" style="--mdc-icon-size:20px;opacity:.85"></ha-icon>'
    + '<span style="font-size:13px;font-weight:600">' + r(d.temperature) + '°</span></div>';
}).join('');
return '<div style="display:flex;align-items:center;justify-content:space-between;gap:10px;width:100%">'
  + '<div style="display:flex;align-items:center;gap:10px;min-width:0">'
  +   '<ha-icon icon="' + ic(entity.state) + '" style="--mdc-icon-size:36px;color:#F5A524;flex-shrink:0"></ha-icon>'
  +   '<div style="font-size:30px;font-weight:700;line-height:1;letter-spacing:-1px">' + r(a.temperature) + '°</div>'
  +   '<div style="display:flex;flex-direction:column;gap:2px;text-align:left;min-width:0">'
  +     '<span style="font-size:14px;font-weight:600;white-space:nowrap;overflow:hidden;text-overflow:ellipsis">' + label(entity.state) + '</span>'
  +     '<span style="font-size:12px;white-space:nowrap">' + hilo + '</span></div></div>'
  + '<div style="display:flex;gap:4px;flex-shrink:0">' + days + '</div></div>';
]]]
