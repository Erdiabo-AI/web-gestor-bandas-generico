-- =============================================================================
--  gestorbandasgenerico · Esquema completo (PostgreSQL)
--  = material_base/mordheim.sql + db/migracion_2026-10-18_base.sql
--  Para una BBDD nueva basta con este fichero.
--
--  Códigos de estado:
--    campanas.campana_estado      INSCRIPCION · ABIERTA · CERRADA
--    bandas.banda_estado          1 Activa · 2 Destruida
--    bandas_lin.banda_lin_estado  0 Activo · 1 Lesionado · 2 Despedido · 3 Muerto
--    batallas.batalla_estado      0 Borrador · 1 Confirmada
--    usuarios.usuario_rol         STD · ADM  (COM es un modo de sesión, no un rol)
-- =============================================================================

CREATE TABLE public.reglas (
	regla_id uuid DEFAULT gen_random_uuid() NOT NULL,
	regla_anyo int4 NOT NULL,
	regla_descripcion varchar(150) NOT NULL,
	regla_version varchar(50) NOT NULL,
	regla_observaciones varchar(255) NULL,
	regla_stats_especificos jsonb,      -- {"m": 4, "ha": 4, ...}: claves = stats, valores = por defecto
	regla_info jsonb,
	CONSTRAINT reglas_pkey PRIMARY KEY (regla_id)
);

CREATE TABLE public.usuarios (
	usuario_id uuid DEFAULT gen_random_uuid() NOT NULL,
	usuario_nombre varchar(100) NOT NULL,
	usuario_email varchar(150) NOT NULL,
	usuario_password_hash varchar(255) NOT NULL,
	usuario_rol varchar(20) DEFAULT 'STD'::character varying NULL,
	reset_token_hash varchar(64) NULL,
	reset_expira timestamp NULL,
	reset_solicitado timestamp NULL,
	CONSTRAINT usuarios_pkey PRIMARY KEY (usuario_id),
	CONSTRAINT usuarios_usuario_email_key UNIQUE (usuario_email)
);

CREATE TABLE public.campanas (
	campana_id uuid DEFAULT gen_random_uuid() NOT NULL,
	regla_id uuid NOT NULL,
	campana_nombre varchar(150) NOT NULL,
	campana_temporada varchar(15) NOT NULL,
	campana_formato varchar(20) DEFAULT 'LIBRE' NOT NULL,
	campana_estado varchar(20) DEFAULT 'INSCRIPCION'::character varying NOT NULL,
	campana_logo_path varchar(200) NULL,
	usuarios_gestor_id uuid NOT NULL,
	usuarios_gestor_suplente_id uuid NULL,
	campana_ia_clave text NULL,
	campana_ia_activa bool DEFAULT true NOT NULL,
	campana_adicional jsonb NULL,
	campana_tesoreria_inicial int4 DEFAULT 0 NOT NULL,
	CONSTRAINT campanas_pkey PRIMARY KEY (campana_id),
	CONSTRAINT fk_campana_regla FOREIGN KEY (regla_id) REFERENCES public.reglas(regla_id),
	CONSTRAINT fk_campana_gestor FOREIGN KEY (usuarios_gestor_id) REFERENCES public.usuarios(usuario_id),
	CONSTRAINT campanas_usuarios_gestor_suplente_id_fkey FOREIGN KEY (usuarios_gestor_suplente_id) REFERENCES public.usuarios(usuario_id) ON DELETE SET NULL
);

CREATE TABLE public.campanas_usuarios (
	campana_usuario_id uuid DEFAULT gen_random_uuid() NOT NULL,
	campana_id uuid NOT NULL,
	usuario_id uuid NOT NULL,
	fecha_inscripcion date NOT NULL,
	usuario_estado int4 DEFAULT 1 NULL,
	CONSTRAINT campanas_usuarios_campana_id_usuario_id_key UNIQUE (campana_id, usuario_id),
	CONSTRAINT campanas_usuarios_pkey PRIMARY KEY (campana_usuario_id),
	CONSTRAINT fk_lu_campana FOREIGN KEY (campana_id) REFERENCES public.campanas(campana_id) ON DELETE CASCADE,
	CONSTRAINT fk_lu_usuario FOREIGN KEY (usuario_id) REFERENCES public.usuarios(usuario_id) ON DELETE CASCADE
);

CREATE TABLE public.notificaciones (
	notificacion_id uuid DEFAULT gen_random_uuid() NOT NULL,
	notificacion_tipo varchar(15) DEFAULT 'CONTACTO'::character varying NOT NULL,
	remitente_nombre varchar(100) NULL,
	remitente_email varchar(150) NULL,
	usuario_id uuid NULL,
	mensaje text NOT NULL,
	fecha timestamp DEFAULT now() NULL,
	leida bool DEFAULT false NULL,
	campana_id uuid NULL,               -- con valor: mensaje al comisario de esa campaña
	CONSTRAINT notificaciones_pkey PRIMARY KEY (notificacion_id),
	CONSTRAINT notificaciones_usuario_id_fkey FOREIGN KEY (usuario_id) REFERENCES public.usuarios(usuario_id) ON DELETE SET NULL,
	CONSTRAINT fk_notif_campana FOREIGN KEY (campana_id) REFERENCES public.campanas(campana_id) ON DELETE CASCADE
);

CREATE TABLE public.bandas (
	banda_id uuid DEFAULT gen_random_uuid() NOT NULL,
	campana_id uuid NOT NULL,
	campana_usuario_id uuid NOT NULL,
	banda_nombre varchar(150) NOT NULL,
	banda_tipo varchar(150) NOT NULL,
	banda_valor_banda int4 DEFAULT 0 NULL,
	banda_tesoreria int4 DEFAULT 0 NULL,
	banda_estado int4 DEFAULT 1 NOT NULL,
	banda_observaciones text NULL,
	banda_info jsonb,
	banda_logo_path varchar(200) NULL,
	banda_audit text NULL,              -- historial: una línea por acción
	CONSTRAINT bandas_campana_id_banda_nombre_key UNIQUE (campana_id, banda_nombre),
	CONSTRAINT bandas_pkey PRIMARY KEY (banda_id),
	CONSTRAINT fk_eq_campana FOREIGN KEY (campana_id) REFERENCES public.campanas(campana_id) ON DELETE CASCADE,
	CONSTRAINT fk_eq_lu FOREIGN KEY (campana_usuario_id) REFERENCES public.campanas_usuarios(campana_usuario_id) ON DELETE CASCADE
);
CREATE UNIQUE INDEX bandas_una_activa_por_usuario ON public.bandas (campana_usuario_id) WHERE banda_estado = 1;

CREATE TABLE public.bandas_lin (
	banda_lin_id uuid DEFAULT gen_random_uuid() NOT NULL,
	banda_id uuid NOT NULL,
	banda_lin_orden int4 NOT NULL,
	banda_lin_nombre varchar(150) NOT NULL,
	banda_lin_subtipo varchar(150) NOT NULL,
	banda_lin_cantidad int4 NOT NULL,
	banda_lin_coste int4 NOT NULL,      -- coste unitario total = precio base + armamento
	banda_lin_experiencia int4 DEFAULT 0 NULL,
	banda_lin_nivel int4 DEFAULT 1 NULL,
	banda_lin_estado int2 DEFAULT 0 NULL,
	banda_lin_observaciones text NULL,
	banda_lin_stats jsonb,
	banda_lin_armamento jsonb,          -- [{"nombre": "Hacha", "precio": 5}, ...]
	banda_lin_notas text NULL,
	banda_lin_audit text NULL,
	CONSTRAINT bandas_lin_pkey PRIMARY KEY (banda_lin_id),
	CONSTRAINT fk_banda_lin FOREIGN KEY (banda_id) REFERENCES public.bandas(banda_id) ON DELETE CASCADE
);

CREATE TABLE public.batallas (
	batalla_id uuid DEFAULT gen_random_uuid() NOT NULL,
	campana_id uuid NOT NULL,
	batalla_orden int4 NOT NULL,
	batalla_escenario varchar(50) NOT NULL,
	batalla_observaciones text NULL,
	batalla_ganador varchar(200),
	batalla_info jsonb,
	batalla_fecha date NOT NULL,
	batalla_estado int2 DEFAULT 0 NOT NULL,
	CONSTRAINT batalla_pkey PRIMARY KEY (batalla_id),
	CONSTRAINT batallas_campana_orden_key UNIQUE (campana_id, batalla_orden),
	CONSTRAINT fk_batalla_campana FOREIGN KEY (campana_id) REFERENCES public.campanas(campana_id) ON DELETE CASCADE
);

CREATE TABLE public.batallas_bandas (
	batalla_banda_id uuid DEFAULT gen_random_uuid() NOT NULL,
	batalla_id uuid NOT NULL,
	banda_id uuid NOT NULL,
	batalla_banda_ganancias int4 DEFAULT 0 NOT NULL,
	batalla_banda_ganador bool DEFAULT false NOT NULL,
	batalla_banda_info jsonb NULL,      -- {"bajas": "miembros muertos o lisiados"}
	CONSTRAINT batallas_bandas_pkey PRIMARY KEY (batalla_banda_id),
	CONSTRAINT batallas_bandas_batalla_banda_key UNIQUE (batalla_id, banda_id),
	CONSTRAINT fk_bb_batalla FOREIGN KEY (batalla_id) REFERENCES public.batallas(batalla_id) ON DELETE CASCADE,
	CONSTRAINT fk_bb_banda FOREIGN KEY (banda_id) REFERENCES public.bandas(banda_id) ON DELETE CASCADE
);

CREATE INDEX idx_campanas_regla ON public.campanas (regla_id);
CREATE INDEX idx_bandas_campana ON public.bandas (campana_id);
CREATE INDEX idx_bandas_lin_banda ON public.bandas_lin (banda_id);
CREATE INDEX idx_batallas_campana ON public.batallas (campana_id);
CREATE INDEX idx_batallas_bandas_banda ON public.batallas_bandas (banda_id);
CREATE INDEX idx_notif_campana ON public.notificaciones (campana_id);
