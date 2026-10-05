-- RF8 — Consultas SQL relacionales clásicas sobre las tablas proyectadas desde las clases.
-- Se ejecutan en el shell SQL de IRIS (bash scripts/consultas_sql.sh). Una sentencia por línea.
-- Cada clase persistente es una tabla; las referencias se navegan con -> (join implícito).

-- 1. Tablas del esquema Fixture (una por clase persistente)
SELECT TABLE_NAME FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_SCHEMA = 'Fixture' ORDER BY TABLE_NAME

-- 2. Herencia: Persona contiene a jugadores, árbitros y técnicos (extent compartido)
SELECT x__classname AS Clase, COUNT(*) AS Cantidad FROM Fixture.Persona GROUP BY x__classname

-- 3. Partidos con sus referencias resueltas por join implícito
SELECT p.Codigo, p.Estado, p.Fase, p.FechaHora, p.Sede->Estadio AS Sede, p.EquipoLocal->Nombre AS EqLocal, p.EquipoVisitante->Nombre AS EqVisitante FROM Fixture.Partido p ORDER BY p.Codigo

-- 4. Eventos (tabla hija): el ID compuesto partido||childsub refleja la relación padre-hijo
SELECT e.ID, e.Partido->Codigo AS Partido, e.Minuto, e.Tipo, e.Jugador->Codigo AS Jugador, e.Equipo->Codigo AS Equipo FROM Fixture.Evento e ORDER BY e.Partido, e.Minuto

-- 5. Marcador por SQL (mismo resultado que Partido.Marcador() navegando objetos)
SELECT e.Partido->Codigo AS Partido, e.Equipo->Codigo AS Equipo, COUNT(*) AS Goles FROM Fixture.Evento e WHERE e.Tipo = 'GOL' GROUP BY e.Partido, e.Equipo

-- 6. JOIN explícito clásico entre tablas proyectadas
SELECT j.Codigo, j.Dorsal, %EXTERNAL(j.Posicion) AS Posicion, eq.Nombre AS Equipo, eq.Confederacion FROM Fixture.Jugador j JOIN Fixture.Equipo eq ON j.Equipo = eq.ID WHERE eq.Codigo = 'E002' AND j.Dorsal <= 5 ORDER BY j.Dorsal

-- 7. Tarjetas por equipo
SELECT e.Equipo->Codigo AS Equipo, e.Tipo, COUNT(*) AS Cantidad FROM Fixture.Evento e WHERE e.Tipo %STARTSWITH 'TARJETA' GROUP BY e.Equipo, e.Tipo

-- 8. Plantel por equipo (lado "muchos" de la relación, resuelto por EquipoIdx)
SELECT eq.Codigo, eq.Nombre, COUNT(j.ID) AS Jugadores, eq.Tecnico->Apellido AS Tecnico FROM Fixture.Equipo eq LEFT JOIN Fixture.Jugador j ON j.Equipo = eq.ID GROUP BY eq.ID ORDER BY eq.Codigo
