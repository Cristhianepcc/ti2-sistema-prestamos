-- Deja viva la solicitud más antigua por (solicitante, recurso) y rechaza las demás.
-- Ejecutar una sola vez:
--   docker compose exec -T db psql -U prestamos -d prestamos < backend/migrations/002_rechazar_solicitudes_duplicadas.sql
BEGIN;

WITH ranqueadas AS (
  SELECT id,
         ROW_NUMBER() OVER (
           PARTITION BY solicitante_id, recurso_id
           ORDER BY created_at, id
         ) AS rn
  FROM solicitud
  WHERE estado IN ('SOLICITADA', 'AVALADA', 'AUTORIZADA')
)
UPDATE solicitud s
SET estado = 'RECHAZADA',
    motivo_rechazo = 'Solicitud duplicada rechazada automáticamente'
FROM ranqueadas r
WHERE s.id = r.id AND r.rn > 1;

COMMIT;