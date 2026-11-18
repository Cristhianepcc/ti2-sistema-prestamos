-- Fusiona el rol DIRECCION_ESCUELA en ADMINISTRADOR_SISTEMA.
-- Ejecutar una sola vez sobre una BD existente:
--   docker compose exec -T db psql -U <usuario> -d <bd> < backend/migrations/001_fusionar_direccion_en_administrador.sql
BEGIN;

-- 1. Quien tenía DIRECCION_ESCUELA pasa a ADMINISTRADOR_SISTEMA (sin duplicar).
INSERT INTO usuario_rol (usuario_id, rol)
SELECT usuario_id, 'ADMINISTRADOR_SISTEMA'::rol
FROM usuario_rol
WHERE rol = 'DIRECCION_ESCUELA'::rol
ON CONFLICT DO NOTHING;

DELETE FROM usuario_rol WHERE rol = 'DIRECCION_ESCUELA'::rol;

-- 2. Recrear el enum sin DIRECCION_ESCUELA (Postgres no permite quitar valores).
ALTER TYPE rol RENAME TO rol_old;
CREATE TYPE rol AS ENUM (
  'ESTUDIANTE', 'DOCENTE', 'CUSTODIO_CE', 'CUSTODIO_INFRA', 'ADMINISTRADOR_SISTEMA'
);
ALTER TABLE usuario_rol ALTER COLUMN rol TYPE rol USING rol::text::rol;
DROP TYPE rol_old;

COMMIT;
