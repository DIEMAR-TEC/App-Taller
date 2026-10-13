-- Hermanado tractor–semi según la planilla UNIDADES_HERMANADAS (13/10/2026).
--
-- Los pares que ya coincidían quedan como estaban. Los que cambian cierran
-- el enganche anterior y abren el nuevo con fecha de hoy, igual que lo hace
-- la pantalla de enganches. Patentes de la planilla corregidas contra el
-- maestro: AF7798NT = AF788NT, AE456MQ = AE456MJ, AD900KU = AD900UK.
--
-- Fuera de este script: los tractores de fleteros (KNI281, LCC752) no están
-- en el maestro, y FCM530 tampoco.
do $$
declare
  hoy date := date '2026-10-13';
  par record;
  t_id bigint;
  s_id bigint;
begin
  for par in select * from (values
    ('AF533SB','AA114ZX'), ('AH522SI','AC538KW'), ('AD247MQ','AE456MJ'),
    ('AE588MW','AE456MK'), ('AF470UT','AF294QU'), ('AF218HY','AF455DQ'),
    ('AF796IX','AF677RJ'), ('AG286TR','AF788NT'), ('AH842GQ','AG888WA'),
    ('AH861UB','AH935PH'),
    ('AF577BD','AG055TX'), ('AG708DM','AB102VH'), ('AE423IV','OOD560'),
    ('AE423IW','AA472IP'), ('AG865QF','MJF259'),  ('AG983HW','AG123FA'),
    ('AI604LF','AH048RS'), ('AH938VO','AH787DF')
  ) as v(tractor, semi)
  loop
    select id into strict t_id from unidades where patente = par.tractor;
    select id into strict s_id from unidades where patente = par.semi;

    if exists (select 1 from enganches where tractor_id = t_id and semi_id = s_id
               and hasta is null) then
      continue;
    end if;

    -- Lo que tuvieran abierto el tractor o el semi se cierra hoy.
    update enganches
       set hasta = hoy,
           nota = nullif(concat_ws(' · ', nota,
                  'Se cerró al importar UNIDADES_HERMANADAS.'), '')
     where hasta is null and (tractor_id = t_id or semi_id = s_id);

    update unidades set es_semi = true where id = s_id and not es_semi;

    insert into enganches (tractor_id, semi_id, desde, usuario, nota)
    values (t_id, s_id, hoy, 'Importación',
            'Planilla UNIDADES_HERMANADAS.');
  end loop;

  -- El maestro dice el semi de hoy de cada tractor.
  update unidades u set semi = s.patente
    from enganches e join unidades s on s.id = e.semi_id
   where e.tractor_id = u.id and e.hasta is null
     and u.semi is distinct from s.patente;
end $$;
