-- =====================================================================
-- CIERRE DE LA API PÚBLICA DE SUPABASE
-- ---------------------------------------------------------------------
-- La app entra a la base directo por PostgreSQL con el usuario dueño
-- (SUPABASE_DB_URL). No usa la API REST de Supabase ni la clave anon.
--
-- Las tablas tienen RLS prendido, pero las vistas (v_*) se creaban como
-- SECURITY DEFINER: corrían con los permisos del dueño y salteaban RLS.
-- Con la URL del proyecto y la clave anon se podían leer por la API.
-- El panel las marca «UNRESTRICTED».
--
--   1. Todas las vistas pasan a security_invoker: corren con los
--      permisos de quien consulta. El dueño sigue viendo todo; anon y
--      authenticated chocan con RLS.
--   2. anon y authenticated pierden todo permiso sobre tablas, vistas,
--      secuencias y funciones del esquema public, también sobre lo que
--      se cree de acá en adelante.
--   3. Las funciones quedan con search_path fijo.
--
-- Se pega entero en Supabase → SQL Editor → Run. Se puede correr las
-- veces que haga falta. Conviene volver a correrlo después de cualquier
-- script que cree o reemplace vistas.
-- =====================================================================

do $$
declare
    r record;
begin
    -- 1. Vistas con los permisos de quien consulta
    for r in
        select c.relname
          from pg_class c
          join pg_namespace n on n.oid = c.relnamespace
         where n.nspname = 'public' and c.relkind = 'v'
    loop
        execute format('alter view public.%I set (security_invoker = true)', r.relname);
    end loop;

    -- 3. search_path fijo en las funciones propias
    for r in
        select p.oid::regprocedure as firma
          from pg_proc p
          join pg_namespace n on n.oid = p.pronamespace
         where n.nspname = 'public'
           and p.prokind = 'f'
           and not exists (select 1 from pg_depend d
                            where d.objid = p.oid and d.deptype = 'e')
    loop
        execute format('alter function %s set search_path = public, pg_temp', r.firma);
    end loop;
end $$;

-- 2. Sin acceso por la API
revoke all on all tables    in schema public from anon, authenticated;
revoke all on all sequences in schema public from anon, authenticated;
revoke all on all functions in schema public from anon, authenticated;

alter default privileges for role postgres in schema public
    revoke all on tables    from anon, authenticated;
alter default privileges for role postgres in schema public
    revoke all on sequences from anon, authenticated;
alter default privileges for role postgres in schema public
    revoke all on functions from anon, authenticated;
