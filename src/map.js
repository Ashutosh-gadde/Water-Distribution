import L from 'leaflet';

export function initializeLaturWaterMap(mapContainerId) {
    // Initialize map centered on Latur, Maharashtra, India
    const map = L.map(mapContainerId).setView([18.4088, 76.5604], 13);

    // Add OpenStreetMap Basemap
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        maxZoom: 19,
        attribution: '© Latur Municipal Corporation GIS Cell'
    }).addTo(map);

    // Layer Groups for Municipal Assets
    const layers = {
        wards: L.layerGroup().addTo(map),
        pipelines: L.layerGroup().addTo(map),
        valves: L.layerGroup().addTo(map),
        tanks: L.layerGroup().addTo(map),
        faults: L.layerGroup().addTo(map)
    };

    // Layer Control Toggle
    L.control.layers(null, {
        "Ward Boundaries": layers.wards,
        "Distribution Pipelines": layers.pipelines,
        "Control Valves": layers.valves,
        "Storage Reservoirs": layers.tanks,
        "Reported Faults & Leaks": layers.faults
    }).addTo(map);

    return { map, layers };
}
