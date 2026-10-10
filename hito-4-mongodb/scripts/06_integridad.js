// RNF2, RNF3 — Volumen, relaciones válidas y campos críticos.
const db = db.getSiblingDB("fixture2030");
const huerfanos = db.jugadores.aggregate([
  { $lookup: { from: "equipos", localField: "equipoId", foreignField: "_id", as: "e" } },
  { $match: { e: { $size: 0 } } }, { $count: "n" }]).toArray();
const equiposSinPlantel = db.equipos.aggregate([
  { $lookup: { from: "jugadores", localField: "_id", foreignField: "equipoId", as: "j" } },
  { $match: { j: { $size: 0 } } }, { $count: "n" }]).toArray();
printjson({
  equipos: db.equipos.countDocuments(),
  jugadores: db.jugadores.countDocuments(),
  jugadoresSinEquipoValido: huerfanos.length ? huerfanos[0].n : 0,
  equiposSinJugadores: equiposSinPlantel.length ? equiposSinPlantel[0].n : 0,
  documentosQueNoCumplenValidacion: db.jugadores.countDocuments({ $nor: [db.getCollectionInfos({ name: "jugadores" })[0].options.validator] })
});
