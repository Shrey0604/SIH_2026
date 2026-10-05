begin;

-- Vectors from different models or dimensions must never share a similarity space.
-- Clear the former OpenAI/demo vectors before resizing the pgvector column.
update document_chunks
set embedding = null;

alter table document_chunks
    alter column embedding type vector(768)
    using null::vector(768);

alter table document_chunks
    add column if not exists embedding_provider varchar(32),
    add column if not exists embedding_model varchar(96),
    add column if not exists embedding_dimension integer;

update document_chunks
set embedding_provider = null,
    embedding_model = null,
    embedding_dimension = null;

commit;
