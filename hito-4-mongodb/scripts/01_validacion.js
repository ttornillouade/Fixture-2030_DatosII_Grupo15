// RF7 — Colecciones con validación $jsonSchema. Solo atributos propios de cada entidad:
// las métricas deportivas (goles, atajadas, etc.) pertenecen a su módulo, no a este.
const db = db.getSiblingDB("fixture2030");

const esquemaEquipo = {
  bsonType: "object",
  required: ["_id", "nombre", "pais", "confederacion", "grupo", "updatedAt"],
  additionalProperties: false,
  properties: {
    _id: { bsonType: "string", pattern: "^E[0-9]{3}$" },
    nombre: { bsonType: "string", minLength: 1 },
    pais: { bsonType: "string", minLength: 1 },
    confederacion: { enum: ["AFC", "CAF", "CONCACAF", "CONMEBOL", "OFC", "UEFA"] },
    grupo: { bsonType: "string", pattern: "^[A-P]$" },
    updatedAt: { bsonType: "date" }
  }
};

const esquemaJugador = {
  bsonType: "object",
  required: ["_id", "equipoId", "nombre", "apellido", "fechaNacimiento", "nacionalidad", "posicion", "dorsal", "updatedAt"],
  additionalProperties: false,
  properties: {
    _id: { bsonType: "string", pattern: "^E[0-9]{3}-J[0-9]{2}$" },
    equipoId: { bsonType: "string", pattern: "^E[0-9]{3}$" },
    nombre: { bsonType: "string", minLength: 1 },
    apellido: { bsonType: "string", minLength: 1 },
    fechaNacimiento: { bsonType: "date" },
    nacionalidad: { bsonType: "string", minLength: 1 },
    posicion: { enum: ["Arquero", "Defensor", "Mediocampista", "Delantero"] },
    dorsal: { bsonType: "int", minimum: 1, maximum: 99 },
    updatedAt: { bsonType: "date" }
  }
};

for (const [nombre, esquema] of [["equipos", esquemaEquipo], ["jugadores", esquemaJugador]]) {
  if (db.getCollectionNames().includes(nombre)) {
    db.runCommand({ collMod: nombre, validator: { $jsonSchema: esquema }, validationLevel: "strict" });
  } else {
    db.createCollection(nombre, { validator: { $jsonSchema: esquema }, validationLevel: "strict" });
  }
  print(`Validación $jsonSchema aplicada a ${nombre}`);
}

// Un dorsal no se repite dentro de un equipo.
db.jugadores.createIndex({ equipoId: 1, dorsal: 1 }, { unique: true, name: "equipo_dorsal_unico" });
print("Índice único equipo_dorsal_unico creado");
