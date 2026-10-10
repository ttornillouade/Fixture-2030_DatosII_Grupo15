// RF11 — Composición de planteles por confederación: jugadores por posición.
const db = db.getSiblingDB("fixture2030");
printjson(db.jugadores.aggregate([
  { $lookup: { from: "equipos", localField: "equipoId", foreignField: "_id", as: "equipo" } },
  { $unwind: "$equipo" },
  { $group: { _id: { confederacion: "$equipo.confederacion", posicion: "$posicion" }, jugadores: { $sum: 1 } } },
  { $group: { _id: "$_id.confederacion", porPosicion: { $push: { k: "$_id.posicion", v: "$jugadores" } }, total: { $sum: "$jugadores" } } },
  { $project: { _id: 0, confederacion: "$_id", total: 1, porPosicion: { $arrayToObject: "$porPosicion" } } },
  { $sort: { confederacion: 1 } }
]).toArray());
