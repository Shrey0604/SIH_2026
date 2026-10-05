alter table wells
    add column if not exists well_scope varchar(32) not null default 'LOCAL_OFFSET';

create index if not exists idx_wells_scope on wells(well_scope);
