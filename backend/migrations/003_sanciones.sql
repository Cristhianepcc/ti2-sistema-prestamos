-- Compatibilidad del esquema existente con el módulo de sanciones.
-- create_all crea primero tablas y tipos faltantes; esta migración completa el esquema previo.
ALTER TYPE estado_recurso ADD VALUE IF NOT EXISTS 'BAJA';
ALTER TABLE prestamo ADD COLUMN IF NOT EXISTS danado BOOLEAN NOT NULL DEFAULT FALSE;
ALTER TABLE prestamo ADD COLUMN IF NOT EXISTS perdido BOOLEAN NOT NULL DEFAULT FALSE;
