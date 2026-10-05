begin;

create table if not exists wells (
    id varchar(64) primary key,
    name varchar(80) not null unique,
    is_active boolean not null default false,
    latitude double precision not null,
    longitude double precision not null,
    field_name varchar(120) not null,
    max_md_m double precision not null,
    status varchar(32) not null,
    source_kind varchar(32) not null,
    well_scope varchar(32) not null default 'LOCAL_OFFSET'
);

create table if not exists formations (
    id varchar(64) primary key,
    name varchar(80) not null unique,
    code varchar(32) not null unique
);

create table if not exists well_formation_intervals (
    id varchar(96) primary key,
    well_id varchar(64) not null references wells(id),
    formation_id varchar(64) not null references formations(id),
    top_md_m double precision not null,
    base_md_m double precision not null,
    top_tvd_m double precision,
    base_tvd_m double precision,
    unique (well_id, formation_id)
);

create table if not exists documents (
    id varchar(96) primary key,
    well_id varchar(64) references wells(id),
    title varchar(180) not null,
    document_type varchar(24) not null,
    filename varchar(180) not null,
    storage_path varchar(300) not null,
    page_count integer not null,
    sha256 varchar(64) not null unique,
    ingestion_status varchar(32) not null,
    source_kind varchar(32) not null,
    created_at timestamptz not null
);

create table if not exists document_chunks (
    id varchar(128) primary key,
    document_id varchar(96) not null references documents(id),
    page_number integer not null,
    chunk_index integer not null,
    text text not null,
    embedding vector(768),
    embedding_provider varchar(32),
    embedding_model varchar(96),
    embedding_dimension integer,
    unique (document_id, page_number, chunk_index)
);

create table if not exists events (
    id varchar(96) primary key,
    well_id varchar(64) not null references wells(id),
    formation_id varchar(64) references formations(id),
    hazard_type varchar(32) not null,
    start_md_m double precision not null,
    end_md_m double precision,
    severity varchar(16) not null,
    description text not null,
    historical_response text,
    extraction_confidence double precision not null,
    source varchar(32) not null,
    created_at timestamptz not null
);

create table if not exists event_evidence (
    id varchar(128) primary key,
    event_id varchar(96) not null references events(id),
    document_id varchar(96) not null references documents(id),
    page_number integer not null,
    evidence_text text not null,
    bbox_json text,
    unique (event_id, document_id, page_number)
);

create table if not exists telemetry_samples (
    id varchar(96) primary key,
    well_id varchar(64) not null references wells(id),
    seq integer not null,
    timestamp_offset_s integer not null,
    md_m double precision not null,
    tvd_m double precision,
    rop_mph double precision not null,
    wob_kn double precision not null,
    rpm double precision not null,
    torque_knm double precision not null,
    spp_bar double precision not null,
    flow_in_lpm double precision not null,
    flow_out_lpm double precision not null,
    pit_volume_m3 double precision not null,
    mud_weight_sg double precision not null,
    gas_units double precision not null,
    unique (well_id, seq)
);

create table if not exists alerts (
    id varchar(96) primary key,
    active_well_id varchar(64) not null references wells(id),
    hazard_type varchar(32) not null,
    status varchar(16) not null,
    current_md_m double precision not null,
    projected_hazard_md_m double precision not null,
    lookahead_m double precision not null,
    evidence_score double precision not null,
    analog_support double precision not null,
    recurrence_score double precision not null,
    telemetry_score double precision not null,
    explanation_json text not null,
    created_at timestamptz not null
);

create index if not exists idx_intervals_well on well_formation_intervals(well_id);
create index if not exists idx_intervals_formation on well_formation_intervals(formation_id);
create index if not exists idx_events_well on events(well_id);
create index if not exists idx_events_formation on events(formation_id);
create index if not exists idx_events_hazard on events(hazard_type);
create index if not exists idx_chunks_document on document_chunks(document_id);
create index if not exists idx_evidence_event on event_evidence(event_id);

commit;
