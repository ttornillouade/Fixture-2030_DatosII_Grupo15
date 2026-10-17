// RF9, RF10 — Inserción, actualización y consultas. Los documentos de demostración se eliminan al final.
const db = db.getSiblingDB("fixture2030");
const titulo = t => print(`\n--- ${t}`);

titulo("Inserción de un equipo y un jugador (validados por $jsonSchema)");
db.equipos.insertOne({ _id: "E900", nombre: "Seleccion Demo", pais: "Pais Demo", confederacion: "OFC", grupo: "P", updatedAt: new Date() });
db.jugadores.insertOne({ _id: "E900-J01", equipoId: "E900", nombre: "Demo", apellido: "Jugador", fechaNacimiento: new Date("2000-01-01"),
                         nacionalidad: "Pais Demo", posicion: "Delantero", dorsal: NumberInt(9), updatedAt: new Date() });
printjson(db.equipos.findOne({ _id: "E900" }));

titulo("Inserción inválida: jugador con dorsal 120 (rechazada por la validación: máximo 99)");
try {
  db.jugadores.insertOne({ _id: "E900-J02", equipoId: "E900", nombre: "X", apellido: "Y", fechaNacimiento: new Date(),
                           nacionalidad: "Z", posicion: "Delantero", dorsal: NumberInt(120), updatedAt: new Date() });
} catch (e) { print(`Rechazado: ${e.errorResponse ? e.errorResponse.errmsg : e.message}`); }

titulo("Actualización del equipo y del jugador");
printjson(db.equipos.updateOne({ _id: "E900" }, { $set: { nombre: "Seleccion Demo Actualizada", updatedAt: new Date() } }));
printjson(db.jugadores.updateOne({ _id: "E900-J01" }, { $set: { dorsal: NumberInt(10), updatedAt: new Date() } }));

titulo("Recuperación por identificador: equipo E010 y jugador E010-J09");
printjson(db.equipos.findOne({ _id: "E010" }));
printjson(db.jugadores.findOne({ _id: "E010-J09" }));

titulo("Filtrado: equipos de CONMEBOL del grupo A");
printjson(db.equipos.find({ confederacion: "CONMEBOL", grupo: "A" }, { nombre: 1, grupo: 1 }).toArray());

titulo("Proyección + orden + paginación: plantel de E010 por dorsal, página 2 de 5 jugadores");
printjson(db.jugadores.find({ equipoId: "E010" }, { _id: 1, apellido: 1, posicion: 1, dorsal: 1 })
  .sort({ dorsal: 1 }).skip(5).limit(5).toArray());

titulo("Limpieza de los documentos de demostración");
print(`jugadores eliminados: ${db.jugadores.deleteMany({ equipoId: "E900" }).deletedCount}`);
print(`equipos eliminados: ${db.equipos.deleteOne({ _id: "E900" }).deletedCount}`);
