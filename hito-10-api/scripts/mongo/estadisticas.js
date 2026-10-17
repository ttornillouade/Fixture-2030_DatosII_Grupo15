// Estadísticas temporales por equipo (funcionalidad del Hito 8).
// Colección time series: timeField = ts, metaField = {partidoId, equipoId} (las dimensiones),
// granularidad de segundos y retención automática de 14 días (expireAfterSeconds).
// Genera 1 punto por segundo y equipo para P001-P004 (95 minutos), de forma determinística.
// Es repetible: borra los puntos de esos partidos antes de volver a insertarlos.
const db = db.getSiblingDB("fixture2030");
const RETENCION_S = 14 * 24 * 3600;

if (!db.getCollectionNames().includes("estadisticas")) {
  db.createCollection("estadisticas", {
    timeseries: { timeField: "ts", metaField: "meta", granularity: "seconds" },
    expireAfterSeconds: RETENCION_S
  });
}

let semilla = 2030;
const azar = () => (semilla = (semilla * 1103515245 + 12345) % 2147483648) / 2147483648;

for (const p of db.partidos.find({ _id: { $in: ["P001", "P002", "P003", "P004"] } }).toArray()) {
  db.estadisticas.deleteMany({ "meta.partidoId": p._id });
  const equipos = [p.equipoLocalId, p.equipoVisitanteId];
  const pases = [0, 0], tiros = [0, 0];
  let posesionLocal = 50, lote = [];
  for (let s = 0; s < 95 * 60; s++) {
    posesionLocal = Math.min(80, Math.max(20, posesionLocal + (azar() - 0.5) * 2));
    for (let i = 0; i < 2; i++) {
      if (azar() < 0.08) pases[i]++;
      if (azar() < 0.002) tiros[i]++;
      lote.push({ ts: new Date(p.fechaHora.getTime() + s * 1000), meta: { partidoId: p._id, equipoId: equipos[i] },
                  posesionPct: Math.round((i === 0 ? posesionLocal : 100 - posesionLocal) * 100) / 100,
                  pasesCompletados: NumberInt(pases[i]), tiros: NumberInt(tiros[i]) });
    }
    if (lote.length >= 5000) { db.estadisticas.insertMany(lote, { ordered: false }); lote = []; }
  }
  if (lote.length) db.estadisticas.insertMany(lote, { ordered: false });
  print(`${p._id}: ${db.estadisticas.countDocuments({ "meta.partidoId": p._id })} puntos desde ${p.fechaHora.toISOString()}`);
}
print("Índices: " + db.estadisticas.getIndexes().map(i => JSON.stringify(i.key)).join(", "));

