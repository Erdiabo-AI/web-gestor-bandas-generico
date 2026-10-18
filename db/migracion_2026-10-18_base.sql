-- =============================================================================
--  gestorbandasgenerico · Migración 2026-10-18
--  Se aplica sobre la BBDD creada con material_base/mordheim.sql (sin FKs).
--  Decisiones: docs/PENDIENTES.md (C5, C6, C7, H2, H4, decisión 4).
-- =============================================================================
BEGIN;

-- 1. Claves foráneas (la BBDD se creó sin ninguna) ----------------------------
ALTER TABLE public.campanas
    ADD CONSTRAINT fk_campana_regla FOREIGN KEY (regla_id) REFERENCES public.reglas(regla_id),
    ADD CONSTRAINT fk_campana_gestor FOREIGN KEY (usuarios_gestor_id) REFERENCES public.usuarios(usuario_id),
    ADD CONSTRAINT campanas_usuarios_gestor_suplente_id_fkey FOREIGN KEY (usuarios_gestor_suplente_id)
        REFERENCES public.usuarios(usuario_id) ON DELETE SET NULL;

ALTER TABLE public.campanas_usuarios
    ADD CONSTRAINT fk_lu_campana FOREIGN KEY (campana_id) REFERENCES public.campanas(campana_id) ON DELETE CASCADE,
    ADD CONSTRAINT fk_lu_usuario FOREIGN KEY (usuario_id) REFERENCES public.usuarios(usuario_id) ON DELETE CASCADE;

ALTER TABLE public.notificaciones
    ADD CONSTRAINT notificaciones_usuario_id_fkey FOREIGN KEY (usuario_id)
        REFERENCES public.usuarios(usuario_id) ON DELETE SET NULL;

ALTER TABLE public.bandas
    ADD CONSTRAINT fk_eq_campana FOREIGN KEY (campana_id) REFERENCES public.campanas(campana_id) ON DELETE CASCADE,
    ADD CONSTRAINT fk_eq_lu FOREIGN KEY (campana_usuario_id)
        REFERENCES public.campanas_usuarios(campana_usuario_id) ON DELETE CASCADE;

ALTER TABLE public.bandas_lin
    ADD CONSTRAINT fk_banda_lin FOREIGN KEY (banda_id) REFERENCES public.bandas(banda_id) ON DELETE CASCADE;

ALTER TABLE public.batallas
    ADD CONSTRAINT fk_batalla_campana FOREIGN KEY (campana_id) REFERENCES public.campanas(campana_id) ON DELETE CASCADE;

-- 2. Bandas implicadas en cada batalla y sus ganancias (H2: informativo) ------
CREATE TABLE public.batallas_bandas (
    batalla_banda_id uuid DEFAULT gen_random_uuid() NOT NULL,
    batalla_id uuid NOT NULL,
    banda_id uuid NOT NULL,
    batalla_banda_ganancias int4 DEFAULT 0 NOT NULL,
    batalla_banda_ganador bool DEFAULT false NOT NULL,
    batalla_banda_info jsonb NULL,          -- {"bajas": "miembros muertos o lisiados"}
    CONSTRAINT batallas_bandas_pkey PRIMARY KEY (batalla_banda_id),
    CONSTRAINT batallas_bandas_batalla_banda_key UNIQUE (batalla_id, banda_id),
    CONSTRAINT fk_bb_batalla FOREIGN KEY (batalla_id) REFERENCES public.batallas(batalla_id) ON DELETE CASCADE,
    CONSTRAINT fk_bb_banda FOREIGN KEY (banda_id) REFERENCES public.bandas(banda_id) ON DELETE CASCADE
);

-- 3. Estado del acta: 0 borrador · 1 confirmada --------------------------------
ALTER TABLE public.batallas ADD COLUMN batalla_estado int2 DEFAULT 0 NOT NULL;
ALTER TABLE public.batallas ADD CONSTRAINT batallas_campana_orden_key UNIQUE (campana_id, batalla_orden);

-- 4. Tesorería inicial de la campaña y formato por defecto (C5, C6) -------------
ALTER TABLE public.campanas ADD COLUMN campana_tesoreria_inicial int4 DEFAULT 0 NOT NULL;
ALTER TABLE public.campanas ALTER COLUMN campana_formato SET DEFAULT 'LIBRE';

-- 5. Contacto con el comisario de una campaña (H4) ------------------------------
ALTER TABLE public.notificaciones ADD COLUMN campana_id uuid NULL;
ALTER TABLE public.notificaciones
    ADD CONSTRAINT fk_notif_campana FOREIGN KEY (campana_id) REFERENCES public.campanas(campana_id) ON DELETE CASCADE;

-- 6. Una banda ACTIVA por usuario y campaña (decisión 4) ------------------------
--    banda_estado: 1 Activa · 2 Destruida. Con la banda destruida puede crear otra.
ALTER TABLE public.bandas ALTER COLUMN banda_estado SET DEFAULT 1;
CREATE UNIQUE INDEX bandas_una_activa_por_usuario ON public.bandas (campana_usuario_id) WHERE banda_estado = 1;

-- 7. Índices de las claves foráneas más consultadas -----------------------------
CREATE INDEX idx_campanas_regla ON public.campanas (regla_id);
CREATE INDEX idx_bandas_campana ON public.bandas (campana_id);
CREATE INDEX idx_bandas_lin_banda ON public.bandas_lin (banda_id);
CREATE INDEX idx_batallas_campana ON public.batallas (campana_id);
CREATE INDEX idx_batallas_bandas_banda ON public.batallas_bandas (banda_id);
CREATE INDEX idx_notif_campana ON public.notificaciones (campana_id);

COMMIT;
