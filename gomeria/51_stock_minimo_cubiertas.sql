-- =====================================================================
-- STOCK MÍNIMO DE CUBIERTAS
-- ---------------------------------------------------------------------
-- Un aviso cuando quedan pocas gomas de un tipo en el depósito: «menos
-- de 10 de 295 BF Goodrich», «menos de 5 de 295 de dirección nuevas».
--
-- Dos cosas nuevas:
--
--   1. La cubierta dice para qué eje está hecha: dirección, tracción o
--      mixta. Hasta acá eso salía de dónde estaba montada, y una goma en
--      el depósito no está montada en ningún lado.
--   2. Las reglas: medida, y opcionalmente marca, tipo y si es nueva o
--      recapada, con la cantidad mínima. Se editan desde Parámetros →
--      Gomería y avisan en Alertas.
--
-- Lo que cuenta es lo que está en el depósito: estado 'stock' y sin un
-- montaje abierto. Lo que está en el recapador no se puede poner hoy.
--
-- Se pega entero en Supabase → SQL Editor → Run. Se puede correr las
-- veces que haga falta.
--
-- ANTES tienen que estar corridos 01_esquema.sql, 20_alertas.sql y
-- 31_marcas_medidas.sql.
-- =====================================================================

-- ---------------------------------------------------------------------
-- 1. PARA QUÉ EJE ES LA CUBIERTA
-- ---------------------------------------------------------------------
alter table cubiertas
  add column if not exists tipo text
  check (tipo is null or tipo in ('direccion', 'traccion', 'mixta'));

comment on column cubiertas.tipo is
  'Para qué eje está hecha: direccion, traccion o mixta. Nulo = sin definir.';


-- ---------------------------------------------------------------------
-- 2. LAS REGLAS
-- ---------------------------------------------------------------------
-- 'medida' es el número que identifica (295, 275, 1000), igual que en
-- cubiertas_medidas.corta. Marca, tipo y condición en nulo = cualquiera.
create table if not exists cubiertas_stock_minimo (
  id         bigint generated always as identity primary key,
  medida     text not null,
  marca      text,
  tipo       text check (tipo is null or tipo in ('direccion', 'traccion', 'mixta')),
  condicion  text check (condicion is null or condicion in ('nueva', 'recapada')),
  minimo     int  not null check (minimo > 0),
  activa     boolean not null default true,
  nota       text,
  creado     timestamptz not null default now()
);

alter table cubiertas_stock_minimo enable row level security;

comment on table cubiertas_stock_minimo is
  'Cuántas cubiertas de cada medida, marca, tipo y condición tiene que haber '
  'como mínimo en el depósito. Se editan desde /parametros.';


-- ---------------------------------------------------------------------
-- 3. SILENCIAR UNA ALERTA DE STOCK
-- ---------------------------------------------------------------------
-- La lista de fuentes que se pueden silenciar quedó corta: no tenía los
-- fluidos ni los prefiltros. Se rehace con todas.
alter table alertas_silenciadas
  drop constraint if exists alertas_silenciadas_fuente_check;
alter table alertas_silenciadas
  add constraint alertas_silenciadas_fuente_check
  check (fuente in ('vencimiento', 'service', 'prefiltro', 'combustible',
                    'cubierta', 'fluido', 'stock'));
