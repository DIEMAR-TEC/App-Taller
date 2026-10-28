-- =====================================================================
-- ESTADOS DE LA CUBIERTA Y DEPÓSITOS
-- ---------------------------------------------------------------------
-- «Stock» no es un estado: dice dónde está la goma, no cómo está. Una
-- cubierta en el depósito puede ser nueva, usada, recapada o estar
-- esperando ir al recapador, y el listado mostraba «stock» para todas.
--
--   1. cubiertas.condicion: cómo está la goma.
--
--          nueva       0 km, nunca montada
--          usada       se montó y se desmontó
--          a_recapar   separada para mandar al recapador
--          recapada    volvió del recapador y todavía no se montó
--
--      El estado sigue diciendo dónde está (stock = en un depósito,
--      montada, recapado = en lo del recapador, reparacion, baja). La
--      pantalla muestra la condición cuando la goma está en un depósito.
--
--   2. «En recapador» es solo lo que salió con un remito de envío. Lo
--      que se desmonta «para recapado» queda en el depósito como
--      «a recapar» hasta que se arme el envío.
--
--   3. depositos: dónde se guarda. Uno por lugar físico (Buenos Aires,
--      otra provincia), con para qué se usa: cubiertas, repuestos o los
--      dos. Se editan desde Parámetros → Gomería.
--
-- Se pega entero en Supabase → SQL Editor → Run. Se puede correr las
-- veces que haga falta.
--
-- ANTES tienen que estar corridos 01_esquema.sql, 18_desgaste.sql y
-- 43_recapado.sql.
-- =====================================================================

begin;

-- ---------------------------------------------------------------------
-- 1. DEPÓSITOS
-- ---------------------------------------------------------------------
create table if not exists depositos (
  id         bigint generated always as identity primary key,
  nombre     text not null unique,
  uso        text not null default 'ambos'
             check (uso in ('cubiertas', 'repuestos', 'ambos')),
  direccion  text,
  activo     boolean not null default true,
  orden      int not null default 50,
  creado     timestamptz not null default now()
);

alter table depositos enable row level security;

comment on table depositos is
  'Los depósitos físicos. uso dice si guarda cubiertas, repuestos o los dos.';

insert into depositos (nombre, uso, orden)
values ('Buenos Aires', 'ambos', 10)
on conflict (nombre) do nothing;

alter table cubiertas
  add column if not exists deposito_id bigint references depositos(id);

comment on column cubiertas.deposito_id is
  'En qué depósito está cuando no está montada ni en el recapador.';

update cubiertas
   set deposito_id = (select id from depositos where nombre = 'Buenos Aires')
 where deposito_id is null;


-- ---------------------------------------------------------------------
-- 2. LA CONDICIÓN
-- ---------------------------------------------------------------------
alter table cubiertas
  add column if not exists condicion text not null default 'nueva'
  check (condicion in ('nueva', 'usada', 'a_recapar', 'recapada'));

comment on column cubiertas.condicion is
  'Cómo está la goma: nueva, usada, a_recapar o recapada. La pantalla la '
  'muestra como estado cuando la cubierta está en un depósito.';

-- El historial anota los cambios de condición con su propio tipo.
alter table movimientos drop constraint if exists movimientos_tipo_check;
alter table movimientos add constraint movimientos_tipo_check
  check (tipo in ('alta', 'montaje', 'desmontaje', 'rotacion', 'recapado',
                  'reparacion', 'medicion', 'baja', 'estado'));


-- ---------------------------------------------------------------------
-- 3. LO QUE YA ESTÁ CARGADO
-- ---------------------------------------------------------------------
-- Una sola vez: solo se tocan las que todavía tienen el valor por
-- defecto y nunca se marcaron a mano.
--
--   · En «recapado» sin un envío abierto: no está en lo del recapador,
--     está esperando ir. Vuelve al depósito como «a recapar».
--   · Código S16-P / STK-P sin recapar: el conteo las separó para recapar.
--   · Recapada y sin montar desde que volvió: recapada.
--   · Montada alguna vez desde su última vida, o código S16-U: usada.
--   · El resto: nueva.
update cubiertas c
   set estado = 'stock', condicion = 'a_recapar'
 where c.estado = 'recapado'
   and not exists (select 1 from recapado_renglones r
                   join recapado_envios e on e.id = r.envio_id
                   where r.cubierta_id = c.id and r.estado = 'enviada'
                     and e.estado = 'abierto');

update cubiertas c
   set condicion = case
     when c.codigo ~ '^(S16|STK)-P' and coalesce(c.recapados, 0) = 0
       then 'a_recapar'
     when exists (select 1 from montajes m
                  where m.cubierta_id = c.id
                    and (m.hasta is not null or c.estado <> 'montada')
                    and m.desde::date >= coalesce(
                          (select max(v.desde) from vidas_cubierta v
                           where v.cubierta_id = c.id), '-infinity'::date))
       then 'usada'
     when c.codigo ~ '^(S16|STK)-U' then 'usada'
     when coalesce(c.recapados, 0) > 0 then 'recapada'
     else 'nueva' end
 where c.condicion = 'nueva'
   and not exists (select 1 from movimientos mv
                   where mv.cubierta_id = c.id and mv.tipo = 'estado');


-- ---------------------------------------------------------------------
-- 4. LA CONDICIÓN SE MUEVE SOLA
-- ---------------------------------------------------------------------
-- Va en la base y no en el programa porque hay muchos caminos que mueven
-- una goma (la mesa, el parte, la handheld, deshacer) y tienen que
-- decir lo mismo:
--
--   · Pasa a «recapado» sin un envío abierto → queda en el depósito
--     como «a recapar».
--   · Se le suma un recapado → recapada.
--   · Se desmonta una nueva o una recapada → usada.
--   · Entra sin depósito → el primero que guarda cubiertas.
create or replace function cubiertas_condicion() returns trigger
language plpgsql as $$
begin
  if new.estado = 'recapado'
     and (tg_op = 'INSERT' or old.estado is distinct from 'recapado')
     and not exists (select 1 from recapado_renglones r
                     join recapado_envios e on e.id = r.envio_id
                     where r.cubierta_id = new.id and r.estado = 'enviada'
                       and e.estado = 'abierto') then
    new.estado := 'stock';
    new.condicion := 'a_recapar';
  end if;

  if tg_op = 'UPDATE' then
    if coalesce(new.recapados, 0) > coalesce(old.recapados, 0) then
      new.condicion := 'recapada';
    elsif old.estado = 'montada' and new.estado <> 'montada'
          and new.condicion in ('nueva', 'recapada') then
      new.condicion := 'usada';
    end if;
  end if;

  if new.deposito_id is null then
    new.deposito_id := (select id from depositos
                        where activo and uso in ('cubiertas', 'ambos')
                        order by orden, id limit 1);
  end if;
  return new;
end $$;

drop trigger if exists tg_cubiertas_condicion on cubiertas;
create trigger tg_cubiertas_condicion
  before insert or update of estado, recapados, deposito_id on cubiertas
  for each row execute function cubiertas_condicion();

commit;

-- Cómo quedó.
select condicion, estado, count(*) from cubiertas
 where estado <> 'baja' group by 1, 2 order by 2, 1;
