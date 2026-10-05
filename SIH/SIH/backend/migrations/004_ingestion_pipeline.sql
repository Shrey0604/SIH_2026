begin;

create table if not exists document_pages (
    id varchar(128) primary key,
    document_id varchar(96) not null references documents(id),
    page_number integer not null,
    raw_text text not null,
    recovered_text text,
    text_quality double precision not null,
    extraction_method varchar(24) not null,
    width_pt double precision not null,
    height_pt double precision not null,
    unique (document_id, page_number)
);

create table if not exists ingestion_jobs (
    id varchar(96) primary key,
    document_id varchar(96) not null unique references documents(id),
    status varchar(32) not null,
    stages_json text not null,
    error_message text,
    cached_verified_extraction boolean not null default false,
    created_at timestamptz not null,
    updated_at timestamptz not null
);

create index if not exists idx_document_pages_document on document_pages(document_id);
create index if not exists idx_ingestion_jobs_document on ingestion_jobs(document_id);

alter table document_pages enable row level security;
alter table ingestion_jobs enable row level security;

commit;
