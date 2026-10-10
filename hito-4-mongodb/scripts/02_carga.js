// RF4, RF5, RF8 — Carga idempotente desde los CSV del Hito 5 (mismos ids en ambos módulos).
// updateOne + upsert por _id: repetir la carga no genera duplicados ni modifica documentos sin cambios
// (updatedAt solo se fija al insertar).
const fs = require("fs");
const db = db.getSiblingDB("fixture2030");

function leerCsv(ruta) {
  const [encabezado, ...lineas] = fs.readFileSync(ruta, "utf8").trim().split(/\r?\n/);  // los CSV del Hito 5 usan CRLF
  const campos = encabezado.split(",");
  return lineas.map(l => Object.fromEntries(l.split(",").map((v, i) => [campos[i], v])));
}

const ahora = new Date();
const equipos = leerCsv("/data/import/equipos.csv").map(e => ({
  updateOne: {
    filter: { _id: e.id },
    update: { $set: { nombre: e.nombre, pais: e.pais, confederacion: e.confederacion, grupo: e.grupo },
              $setOnInsert: { updatedAt: ahora } },
    upsert: true
  }
}));
const jugadores = leerCsv("/data/import/jugadores.csv").map(j => ({
  updateOne: {
    filter: { _id: j.id },
    update: { $set: { equipoId: j.equipo_id, nombre: j.nombre, apellido: j.apellido,
                      fechaNacimiento: new Date(j.fecha_nacimiento + "T00:00:00Z"), nacionalidad: j.nacionalidad,
                      posicion: j.posicion, dorsal: NumberInt(j.dorsal) },
              $setOnInsert: { updatedAt: ahora } },
    upsert: true
  }
}));

const re = db.equipos.bulkWrite(equipos, { ordered: false });
print(`equipos   -> insertados: ${re.upsertedCount}, actualizados: ${re.modifiedCount}, sin cambios: ${re.matchedCount - re.modifiedCount}`);
const rj = db.jugadores.bulkWrite(jugadores, { ordered: false });
print(`jugadores -> insertados: ${rj.upsertedCount}, actualizados: ${rj.modifiedCount}, sin cambios: ${rj.matchedCount - rj.modifiedCount}`);
print(`Total: ${db.equipos.countDocuments()} equipos, ${db.jugadores.countDocuments()} jugadores`);
