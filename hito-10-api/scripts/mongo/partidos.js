// Partidos con sus eventos embebidos (funcionalidad del Hito 9).
// Embeber es la relación padre-hijo documental: un evento no existe sin su partido, se guarda
// con él y se borra con él. Las transiciones de estado las hace la API con updates condicionales.
// Fuente: los CSV del Hito 5 (mismos ids que Neo4j). Carga idempotente por _id.
const fs = require("fs");
const db = db.getSiblingDB("fixture2030");

function leerCsv(ruta) {
  const [encabezado, ...lineas] = fs.readFileSync(ruta, "utf8").trim().split(/\r?\n/);
  const campos = encabezado.split(",");
  return lineas.map(l => Object.fromEntries(l.split(",").map((v, i) => [campos[i], v])));
}

const esquema = {
  bsonType: "object",
  required: ["_id", "fechaHora", "fase", "sede", "equipoLocalId", "equipoVisitanteId", "estado", "eventos", "updatedAt"],
  additionalProperties: false,
  properties: {
    _id: { bsonType: "string", pattern: "^P[0-9]{3}$" },
    fechaHora: { bsonType: "date" },
    fase: { bsonType: "string" },
    sede: {
      bsonType: "object", required: ["id", "nombre", "ciudad"], additionalProperties: false,
      properties: { id: { bsonType: "string" }, nombre: { bsonType: "string" }, ciudad: { bsonType: "string" } }
    },
    equipoLocalId: { bsonType: "string", pattern: "^E[0-9]{3}$" },
    equipoVisitanteId: { bsonType: "string", pattern: "^E[0-9]{3}$" },
    estado: { enum: ["PROGRAMADO", "EN_JUEGO", "FINALIZADO"] },
    eventos: {
      bsonType: "array",
      items: {
        bsonType: "object", required: ["tipo", "minuto", "jugadorId"], additionalProperties: false,
        properties: {
          tipo: { enum: ["Gol", "TarjetaAmarilla", "TarjetaRoja", "Cambio"] },
          minuto: { bsonType: "int", minimum: 1, maximum: 130 },
          jugadorId: { bsonType: "string", pattern: "^E[0-9]{3}-J[0-9]{2}$" }
        }
      }
    },
    updatedAt: { bsonType: "date" }
  }
};
if (db.getCollectionNames().includes("partidos")) {
  db.runCommand({ collMod: "partidos", validator: { $jsonSchema: esquema }, validationLevel: "strict" });
} else {
  db.createCollection("partidos", { validator: { $jsonSchema: esquema }, validationLevel: "strict" });
}

const sedes = Object.fromEntries(leerCsv("/tmp/fixture10/sedes.csv").map(s => [s.id, { id: s.id, nombre: s.nombre, ciudad: s.ciudad }]));
const eventos = {};
for (const e of leerCsv("/tmp/fixture10/eventos.csv")) {
  (eventos[e.partido_id] ||= []).push({ tipo: e.tipo, minuto: NumberInt(e.minuto), jugadorId: e.jugador_id });
}
const ahora = new Date();
const operaciones = leerCsv("/tmp/fixture10/partidos.csv").map(p => ({
  updateOne: {
    filter: { _id: p.id },
    // Los CSV traen solo la fecha: se asume el inicio a las 16:00 UTC.
    update: { $set: { fechaHora: new Date(p.fecha + "T16:00:00Z"), fase: p.fase, sede: sedes[p.sede_id],
                      equipoLocalId: p.local_id, equipoVisitanteId: p.visitante_id,
                      estado: p.estado.trim() === "Finalizado" ? "FINALIZADO" : "PROGRAMADO",
                      eventos: (eventos[p.id] || []).sort((a, b) => a.minuto - b.minuto) },
              $setOnInsert: { updatedAt: ahora } },
    upsert: true
  }
}));
const r = db.partidos.bulkWrite(operaciones, { ordered: false });
print(`partidos -> insertados: ${r.upsertedCount}, actualizados: ${r.modifiedCount}, sin cambios: ${r.matchedCount - r.modifiedCount}`);
print(`Total: ${db.partidos.countDocuments()} partidos, ${db.partidos.aggregate([{ $group: { _id: null, n: { $sum: { $size: "$eventos" } } } }]).toArray()[0].n} eventos embebidos`);
