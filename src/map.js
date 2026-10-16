import { LMC_DEFAULT_CENTER, LMC_DEFAULT_ZOOM } from './config.js';
import { loadMapFeatures } from './backend.js';

let map;
const layerByType = new Map();
const colors = { ward:'#64748b', zone:'#16a34a', pipeline:'#2563eb', valve:'#ea580c', tank:'#7c3aed', pump:'#0f766e', hydrant:'#dc2626', other:'#475569', water_meter:'#0891b2' };

export async function initNetworkMap(containerId = 'network-map') {
  if (map) { map.remove(); map = null; layerByType.clear(); }
  map = L.map(containerId, { preferCanvas: true }).setView(LMC_DEFAULT_CENTER, LMC_DEFAULT_ZOOM);
  // Public OpenStreetMap tiles. For a government production deployment, confirm tile-provider terms,
  // usage limits, attribution and procurement requirements before relying on this service.
  L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    maxZoom: 19, attribution: '&copy; OpenStreetMap contributors'
  }).addTo(map);
  const geojson = await loadMapFeatures();
  const bounds = [];
  const grouped = {};
  for (const feature of (geojson.features || [])) {
    const type = feature.properties?.type || 'other';
    (grouped[type] ||= []).push(feature);
  }
  for (const [type, features] of Object.entries(grouped)) {
    const layer = L.geoJSON({ type:'FeatureCollection', features }, {
      style: () => ({ color: colors[type] || colors.other, weight: type === 'pipeline' ? 3 : 1.5, fillOpacity: type === 'zone' || type === 'ward' ? 0.12 : 0.25 }),
      pointToLayer: (feature, latlng) => L.circleMarker(latlng, { radius: type === 'valve' ? 5 : 6, color: colors[type] || colors.other, fillOpacity: 0.9 }),
      onEachFeature: (feature, leafletLayer) => {
        const p = feature.properties || {};
        const safe = value => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
        leafletLayer.bindPopup(`<strong>${safe(p.name || p.id)}</strong><br>${safe(p.type)}<br>ID: ${safe(p.id)}<br>Verification: ${safe(p.verified)}`);
      }
    }).addTo(map);
    layerByType.set(type, layer);
    const b = layer.getBounds?.(); if (b?.isValid()) bounds.push(b);
  }
  if (bounds.length) {
    const combined = bounds.reduce((acc, b) => acc.extend(b), L.latLngBounds(bounds[0]));
    map.fitBounds(combined.pad(0.08), { maxZoom: 16 });
  }
  return map;
}

export function setLayerVisible(type, visible) {
  if (!map || !layerByType.has(type)) return;
  const layer = layerByType.get(type);
  if (visible) layer.addTo(map); else map.removeLayer(layer);
}
