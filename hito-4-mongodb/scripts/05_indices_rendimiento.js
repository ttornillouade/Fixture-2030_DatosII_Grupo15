// RF12, RF13 — Consulta principal: plantel de un equipo filtrado por posición y ordenado por dorsal
// (pantalla de convocatoria). Se mide con explain("executionStats") antes y después del índice.
const db = db.getSiblingDB("fixture2030");
const filtro = { equipoId: "E010", posicion: "Delantero" };
const resumen = (etapa, plan) => {
  const s = plan.executionStats;
  const texto = JSON.stringify(plan.queryPlanner.winningPlan);
  const etapas = texto.match(/"stage":"[A-Z_]+"/g).join(" > ");
  const indice = (texto.match(/"indexName":"([^"]+)"/) || [, "ninguno"])[1];
  print(`${etapa}: nReturned=${s.nReturned} totalDocsExamined=${s.totalDocsExamined} totalKeysExamined=${s.totalKeysExamined} executionTimeMillis=${s.executionTimeMillis}`);
  print(`  plan: ${etapas} | índice usado: ${indice}`);
};

// Antes: el único índice que sirve es equipo_dorsal_unico {equipoId, dorsal}: filtra por equipo pero
// tiene que leer todo el plantel para descartar las otras posiciones.
if (db.jugadores.getIndexes().some(i => i.name === "equipo_posicion_dorsal")) db.jugadores.dropIndex("equipo_posicion_dorsal");
resumen("Antes del índice", db.jugadores.find(filtro).sort({ dorsal: 1 }).explain("executionStats"));
db.jugadores.createIndex({ equipoId: 1, posicion: 1, dorsal: 1 }, { name: "equipo_posicion_dorsal" });
resumen("Después del índice", db.jugadores.find(filtro).sort({ dorsal: 1 }).explain("executionStats"));
print("\nÍndices de jugadores: " + db.jugadores.getIndexes().map(i => i.name).join(", "));
