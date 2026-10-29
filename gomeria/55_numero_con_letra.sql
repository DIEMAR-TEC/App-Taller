-- =====================================================================
-- CUBIERTAS CARGADAS CON LA LETRA DE LA POSICIÓN EN EL NÚMERO
-- ---------------------------------------------------------------------
-- Se pega entero en Supabase → SQL Editor → New query → Run. Se puede
-- correr las veces que haga falta.
--
-- En el parte, «287I» es la 287 puesta adentro del dual. El sistema la
-- tomaba como una cubierta nueva «287I»: la montaba y la 287 seguía
-- figurando en stock. Esto lo corrige:
--   - Si existe la cubierta sin la letra, el montaje y los movimientos
--     pasan a ella (queda montada y usada) y la duplicada se elimina.
--   - Si no existe, a la cubierta se le quita la letra del código.
-- =====================================================================
do $$
declare r record; base_id bigint;
begin
  for r in select id, codigo from cubiertas where codigo ~ '^[0-9]+[IE]$' loop
    base_id := null;
    select b.id into base_id from cubiertas b
     where b.id <> r.id
       and ltrim(b.codigo, '0') = ltrim(regexp_replace(r.codigo, '[IE]$', ''), '0')
     order by (b.estado <> 'baja') desc, b.id
     limit 1;
    if base_id is null then
      update cubiertas set codigo = regexp_replace(r.codigo, '[IE]$', ''), condicion = 'usada'
       where id = r.id;
    else
      delete from movimientos where cubierta_id = r.id and tipo = 'alta';
      update movimientos        set cubierta_id = base_id where cubierta_id = r.id;
      update montajes           set cubierta_id = base_id where cubierta_id = r.id;
      update mediciones         set cubierta_id = base_id where cubierta_id = r.id;
      update recapado_renglones set cubierta_id = base_id where cubierta_id = r.id;
      delete from vidas_cubierta where cubierta_id = r.id;
      update cubiertas set estado = 'montada', condicion = 'usada',
                           fecha_baja = null, motivo_baja = null
       where id = base_id;
      delete from cubiertas where id = r.id;
    end if;
  end loop;
end $$;

-- Cómo quedó: no tiene que aparecer ningún código con letra.
select c.codigo, c.estado, c.condicion, u.patente, p.codigo as posicion
from cubiertas c
left join montajes m on m.cubierta_id = c.id and m.hasta is null
left join unidades u on u.id = m.unidad_id
left join configuracion_posiciones p on p.id = m.posicion_id
where c.codigo ~ '^[0-9]+[IE]$'
   or c.codigo in ('020','021','125','130','165','287','427','445','446','447','448','473')
order by c.codigo;
