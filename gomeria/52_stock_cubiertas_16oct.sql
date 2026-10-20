-- =====================================================================
-- STOCK DE CUBIERTAS AL 16/10/2026
-- ---------------------------------------------------------------------
-- Reemplaza lo que había en el depósito por el conteo del 16/10/2026:
-- 97 cubiertas.
--
--   1. Todo lo que figuraba en el depósito (estado 'stock' y sin montaje
--      abierto) se da de baja con motivo «Ajuste de inventario 16/10/2026».
--      No se borra: la ficha, su vida y sus movimientos quedan como
--      historia. Lo montado y lo que está en el recapador no se toca.
--   2. Se dan de alta las 97 del conteo, con código provisorio por grupo:
--
--          S16-N###   nuevas 0 km          S16-P###   para recapar
--          S16-R###   recapadas nuevas     S16-M###   macizas
--          S16-U###   usadas para rodar    S16-C###   con cámara
--
--      Cuando se sepa el número de fuego de una, se le cambia el código:
--
--          update cubiertas set codigo = '4521' where codigo = 'S16-R007';
--
-- Se pega entero en Supabase → SQL Editor → Run. Se puede correr las
-- veces que haga falta: si el conteo ya está cargado no hace nada.
-- =====================================================================

begin;

-- Las medidas que no estaban en el catálogo.
insert into cubiertas_medidas (medida, corta, clase, orden) values
  ('7.50×16',      '750', 'otro', 50),
  ('215/75 R17.5', '215', 'otro', 50),
  ('205/70 R15',   '205', 'otro', 50)
on conflict (medida) do nothing;

insert into cubiertas_marcas (nombre, slug) values
  ('Compasal', 'compasal'),
  ('Formula',  'formula')
on conflict do nothing;

create temp table conteo (codigo text, marca text, modelo text, medida text,
                          recapados int, obs text) on commit drop;
insert into conteo values
  ('S16-N001', 'Goodrich', null, '295', 0, 'Nueva 0 km'),
  ('S16-N002', 'Goodrich', null, '295', 0, 'Nueva 0 km'),
  ('S16-N003', 'Compasal', null, '295', 0, 'Nueva 0 km'),
  ('S16-N004', 'Compasal', null, '295', 0, 'Nueva 0 km'),
  ('S16-N005', 'Compasal', null, '295', 0, 'Nueva 0 km'),
  ('S16-N006', 'Compasal', null, '295', 0, 'Nueva 0 km'),
  ('S16-N007', 'Compasal', null, '295', 0, 'Nueva 0 km'),
  ('S16-N008', 'Compasal', null, '295', 0, 'Nueva 0 km'),
  ('S16-N009', 'Michelin', null, '295', 0, 'Nueva 0 km'),
  ('S16-N010', null, null, '1000×20', 0, 'Nueva 0 km'),
  ('S16-N011', null, null, '1000×20', 0, 'Nueva 0 km'),
  ('S16-N012', 'Fate', 'Avantia', '205/70 R15', 0, 'Nueva 0 km · utilitario'),
  ('S16-R001', 'Fate', null, '295', 1, 'Recapada nueva'),
  ('S16-R002', 'Fate', null, '295', 1, 'Recapada nueva'),
  ('S16-R003', 'Fate', null, '295', 1, 'Recapada nueva'),
  ('S16-R004', 'Fate', null, '295', 1, 'Recapada nueva'),
  ('S16-R005', 'Fate', null, '295', 1, 'Recapada nueva'),
  ('S16-R006', 'Fate', null, '295', 1, 'Recapada nueva'),
  ('S16-R007', 'Fate', null, '295', 1, 'Recapada nueva'),
  ('S16-R008', 'Fate', null, '295', 1, 'Recapada nueva'),
  ('S16-R009', 'Fate', null, '295', 1, 'Recapada nueva'),
  ('S16-R010', 'Fate', null, '295', 1, 'Recapada nueva'),
  ('S16-R011', 'Fate', null, '295', 1, 'Recapada nueva'),
  ('S16-R012', 'Fate', null, '295', 1, 'Recapada nueva'),
  ('S16-R013', 'Fate', null, '295', 1, 'Recapada nueva'),
  ('S16-R014', 'Fate', null, '295', 1, 'Recapada nueva'),
  ('S16-R015', 'Fate', null, '295', 1, 'Recapada nueva'),
  ('S16-R016', 'Fate', null, '295', 1, 'Recapada nueva'),
  ('S16-R017', 'Goodrich', null, '295', 1, 'Recapada nueva'),
  ('S16-R018', 'Goodrich', null, '295', 1, 'Recapada nueva'),
  ('S16-R019', 'Goodrich', null, '295', 1, 'Recapada nueva'),
  ('S16-R020', 'Goodrich', null, '295', 1, 'Recapada nueva'),
  ('S16-R021', 'Goodrich', null, '295', 1, 'Recapada nueva'),
  ('S16-R022', 'Goodrich', null, '295', 1, 'Recapada nueva'),
  ('S16-R023', 'Goodrich', null, '295', 1, 'Recapada nueva'),
  ('S16-R024', 'Goodrich', null, '295', 1, 'Recapada nueva'),
  ('S16-R025', 'Goodrich', null, '295', 1, 'Recapada nueva'),
  ('S16-R026', 'Goodrich', null, '295', 1, 'Recapada nueva'),
  ('S16-R027', 'Dunlop', null, '295', 1, 'Recapada nueva'),
  ('S16-R028', 'Dunlop', null, '295', 1, 'Recapada nueva'),
  ('S16-R029', 'Dunlop', null, '295', 1, 'Recapada nueva'),
  ('S16-R030', 'Dunlop', null, '295', 1, 'Recapada nueva'),
  ('S16-R031', 'Michelin', null, '295', 1, 'Recapada nueva'),
  ('S16-R032', 'Michelin', null, '295', 1, 'Recapada nueva'),
  ('S16-R033', 'Michelin', null, '295', 1, 'Recapada nueva'),
  ('S16-R034', 'Firestone', null, '295', 1, 'Recapada nueva'),
  ('S16-R035', 'Fate', null, '275', 1, 'Recapada nueva'),
  ('S16-R036', 'Fate', null, '275', 1, 'Recapada nueva'),
  ('S16-R037', 'Fate', null, '275', 1, 'Recapada nueva'),
  ('S16-R038', 'Fate', null, '275', 1, 'Recapada nueva'),
  ('S16-R039', 'Fate', null, '275', 1, 'Recapada nueva'),
  ('S16-R040', 'Michelin', null, '275', 1, 'Recapada nueva'),
  ('S16-R041', 'Michelin', null, '275', 1, 'Recapada nueva'),
  ('S16-R042', 'Michelin', null, '275', 1, 'Recapada nueva'),
  ('S16-R043', 'Michelin', null, '275', 1, 'Recapada nueva'),
  ('S16-R044', null, null, '1000×20', 1, 'Recapada nueva'),
  ('S16-R045', null, null, '1000×20', 1, 'Recapada nueva'),
  ('S16-R046', null, null, '1000×20', 1, 'Recapada nueva'),
  ('S16-R047', 'Fate', null, '215/75 R17.5', 1, 'Recapada nueva'),
  ('S16-R048', 'Fate', null, '215/75 R17.5', 1, 'Recapada nueva'),
  ('S16-R049', 'Fate', null, '215/75 R17.5', 1, 'Recapada nueva'),
  ('S16-R050', 'Formula', null, '215/75 R17.5', 1, 'Recapada nueva'),
  ('S16-U001', 'Fate', null, '295', 1, 'Usada para rodar'),
  ('S16-U002', 'Fate', null, '295', 1, 'Usada para rodar'),
  ('S16-U003', 'Goodrich', 'Taco', '295', 1, 'Usada para rodar'),
  ('S16-U004', 'Pirelli', 'Taco', '275', 0, 'Usada para rodar'),
  ('S16-U005', 'Pirelli', 'Taco', '275', 0, 'Usada para rodar'),
  ('S16-U006', 'Pirelli', 'Lineal', '275', 0, 'Usada para rodar'),
  ('S16-U007', null, null, '1000×20', 0, 'Usada para rodar'),
  ('S16-U008', null, null, '1000×20', 0, 'Usada para rodar'),
  ('S16-U009', null, null, '1000×20', 0, 'Usada para rodar'),
  ('S16-U010', null, null, '1000×20', 0, 'Usada para rodar'),
  ('S16-U011', null, null, '1000×20', 0, 'Usada para rodar'),
  ('S16-U012', null, null, '1000×20', 0, 'Usada para rodar'),
  ('S16-U013', 'Fate', null, '7.50×16', 0, 'Usada para rodar · estado no indicado'),
  ('S16-U014', 'Fate', null, '7.50×16', 0, 'Usada para rodar · estado no indicado'),
  ('S16-U015', 'Fate', null, '7.50×16', 0, 'Usada para rodar · estado no indicado'),
  ('S16-U016', 'Fate', null, '7.50×16', 0, 'Usada para rodar · estado no indicado'),
  ('S16-U017', 'Fate', null, '7.50×16', 0, 'Usada para rodar · estado no indicado'),
  ('S16-U018', 'Fate', null, '7.50×16', 0, 'Usada para rodar · estado no indicado'),
  ('S16-U019', 'Fate', null, '7.50×16', 0, 'Usada para rodar · estado no indicado'),
  ('S16-P001', 'Fate', null, '295', 0, 'Para recapar'),
  ('S16-P002', 'Fate', null, '295', 0, 'Para recapar'),
  ('S16-P003', 'Fate', null, '295', 0, 'Para recapar'),
  ('S16-P004', 'West Lake', null, '295', 0, 'Para recapar'),
  ('S16-P005', 'West Lake', null, '295', 0, 'Para recapar'),
  ('S16-P006', 'Fate', null, '275', 0, 'Para recapar'),
  ('S16-M001', null, null, '700×12', 0, 'Maciza · autoelevador'),
  ('S16-M002', null, null, '700×12', 0, 'Maciza · autoelevador'),
  ('S16-M003', null, null, '600×9', 0, 'Maciza · autoelevador'),
  ('S16-M004', null, null, '600×9', 0, 'Maciza · autoelevador'),
  ('S16-C001', null, null, '700×12', 0, 'Con cámara · autoelevador'),
  ('S16-C002', null, null, '700×12', 0, 'Con cámara · autoelevador'),
  ('S16-C003', null, null, '600×9', 0, 'Con cámara · autoelevador'),
  ('S16-C004', null, null, '600×9', 0, 'Con cámara · autoelevador'),
  ('S16-C005', null, null, '600×9', 0, 'Con cámara · autoelevador'),
  ('S16-C006', null, null, '600×9', 0, 'Con cámara · autoelevador');

-- 1. BAJA DE LO QUE HABÍA EN EL DEPÓSITO
create temp table a_baja on commit drop as
select c.id from cubiertas c
where c.estado = 'stock'
  and not exists (select 1 from montajes m where m.cubierta_id = c.id and m.hasta is null)
  and not exists (select 1 from cubiertas where codigo like 'S16-%');

update cubiertas c
   set estado = 'baja', fecha_baja = date '2026-10-16',
       motivo_baja = 'Ajuste de inventario 16/10/2026'
  from a_baja b where b.id = c.id;

update vidas_cubierta v
   set hasta = greatest(v.desde, date '2026-10-16'),
       motivo_fin = 'Ajuste de inventario 16/10/2026',
       remanente_fin_mm = c.remanente_mm
  from cubiertas c, a_baja b
 where c.id = v.cubierta_id and b.id = v.cubierta_id and v.hasta is null;

insert into movimientos (grupo_id, tipo, cubierta_id, usuario, nota)
select g.id, 'baja', b.id, 'sistema', 'Ajuste de inventario 16/10/2026'
from a_baja b, (select gen_random_uuid() as id) g;

-- 2. ALTA DEL CONTEO
insert into cubiertas (codigo, marca, modelo, medida, recapados,
                       observaciones, estado, fecha_alta)
select codigo, marca, modelo, medida, recapados,
       obs || ' · stock al 16/10/2026', 'stock', date '2026-10-16'
from conteo
on conflict (codigo) do nothing;

-- Las recién dadas de alta: las del conteo que todavía no tienen vida.
create temp table altas on commit drop as
select c.id, c.marca, c.modelo, c.recapados
from cubiertas c join conteo t using (codigo)
where not exists (select 1 from vidas_cubierta v where v.cubierta_id = c.id);

insert into vidas_cubierta (cubierta_id, numero, tipo, marca, banda, desde, nota)
select id, recapados,
       case when recapados > 0 then 'recapado' else 'original' end,
       marca, case when recapados = 0 then modelo end,
       date '2026-10-16', 'Alta por conteo de stock del 16/10/2026.'
from altas
on conflict do nothing;

insert into movimientos (grupo_id, tipo, cubierta_id, usuario, nota)
select g.id, 'alta', a.id, 'sistema', 'Conteo de stock del 16/10/2026'
from altas a, (select gen_random_uuid() as id) g;

commit;

-- Qué quedó en el depósito. Tiene que dar 97.
select coalesce(medida, '(sin medida)') as medida,
       split_part(observaciones, ' · ', 1) as que_son,
       coalesce(marca, '(sin marca)') as marca,
       count(*) as cuantas
from cubiertas c
where estado = 'stock'
  and not exists (select 1 from montajes m where m.cubierta_id = c.id and m.hasta is null)
group by 1, 2, 3
order by 1, 2, 3;
