-- La API ejecuta esta limpieza una sola vez mediante el registro de migraciones.
-- Conserva la solicitud activa más antigua y rechaza las duplicadas.

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
