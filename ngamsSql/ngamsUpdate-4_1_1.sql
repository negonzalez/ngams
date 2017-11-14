-- make sure we have an "iteration" column on the bookkeeping table
-- some installations have already been tweaked by hand

declare
  cnt number;
begin
  select count(table_name) into cnt from user_tab_columns where table_name='NGAS_MIRRORING_BOOKKEEPING' and COLUMN_NAME='ITERATION';
  if cnt = 0 then
    execute immediate 'alter table ngas_mirroring_bookkeeping add iteration number(22) null';
  end if;
end;
/

-- some installations have the column, but it is nullable. We want to put a stop to that.
update ngas_mirroring_bookkeeping set iteration = 0 if iteration is null;
alter table ngas_mirroring_bookkeeping modify iteration number(22) default 0 not null;

alter table ngas_mirroring_bookkeeping modify status char(8) not null;

create index nmb_iter_status_idx on ngas_mirroring_bookkeeping(iteration, status);

alter table ngas_mirroring_bookkeeping modify source_host varchar2(64) not null;

create index nmb_thost_status_shost_idx on ngas_mirroring_bookkeeping(target_cluster, target_host, status, source_host);

-- the core of the mirroring algorithm checks the ngas_files table, which can get pretty big. It now
-- narrows this selection using the ingestion date
create index ngas_files_indate_idx on ngas_files(substr(ingestion_date, 1, 10));


