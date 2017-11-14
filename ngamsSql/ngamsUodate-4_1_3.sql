alter table ngas.ngas_mirroring_bookkeeping  modify file_size number(20) not null;

create index nmb_file_size_idx on ngas.ngas_mirroring_bookkeeping(file_size);
