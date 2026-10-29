-- =====================================================================
-- LAS CUBIERTAS QUE SALIERON DE UNA UNIDAD Y FIGURAN NUEVAS
-- ---------------------------------------------------------------------
-- Se pega entero en Supabase → SQL Editor → New query → Run. Se puede
-- correr las veces que haga falta.
--
-- Una goma que sale de un camión vuelve al depósito usada, nunca nueva.
-- Las que el parte sacaba sin tenerlas cargadas en el mapa quedaban como
-- nuevas. Esto pasa a usada las que están en el depósito y lo último que
-- les pasó fue salir de una unidad.
-- =====================================================================
update cubiertas c
   set condicion = 'usada'
 where c.estado = 'stock'
   and c.condicion in ('nueva', 'recapada')
   and (select mv.tipo from movimientos mv
         where mv.cubierta_id = c.id and mv.deshecho is null
         order by mv.fecha desc, mv.id desc limit 1) = 'desmontaje';

-- Cómo quedó: no tiene que aparecer ninguna.
select c.codigo, c.condicion
from cubiertas c
where c.estado = 'stock'
  and c.condicion in ('nueva', 'recapada')
  and (select mv.tipo from movimientos mv
        where mv.cubierta_id = c.id and mv.deshecho is null
        order by mv.fecha desc, mv.id desc limit 1) = 'desmontaje';
