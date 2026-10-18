-- =============================================================================
--  gestorbandasgenerico · Migración 2026-10-18 (2)
--  Nuevo campo de categoría del miembro de banda (p. ej. «Héroe», «Secuaz»).
-- =============================================================================
BEGIN;

ALTER TABLE public.bandas_lin ADD COLUMN banda_lin_categoria varchar(50) NULL;

COMMIT;
