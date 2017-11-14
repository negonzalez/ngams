alter table ngas.ngas_mirroring_bookkeeping  modify file_size number(20) not null;

create index nmb_file_size_idx on ngas.ngas_mirroring_bookkeeping(file_size);

-- make absolutely sure that the PK is correct - some older installations used a different PK
alter table ngas_mirroring_bookkeeping drop primary key;
alter table ngas_mirroring_bookkeeping add constraint ngas_mirroring_bookkeeping_idx primary key(file_id, file_version, iteration)

quit
/

