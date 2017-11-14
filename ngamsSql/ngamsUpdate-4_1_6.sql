-- add columns for:
--   the checksum from the source database
--   the staging file name so that we can resume downloads
--   the number of attempts of downloads - for info only
--   bytes downloaded so far (not used in this release)

declare
  cnt number;
begin
  select count(table_name) into cnt from user_tab_columns where table_name='NGAS_MIRRORING_BOOKKEEPING' and COLUMN_NAME='CHECKSUM';
  if cnt = 0 then
    execute immediate 'alter table ngas_mirroring_bookkeeping add checksum varchar2(64) default ''?'' not null';
  end if;

  select count(table_name) into cnt from user_tab_columns where table_name='NGAS_MIRRORING_BOOKKEEPING' and COLUMN_NAME='STAGING_FILE';
  if cnt = 0 then
    execute immediate 'alter table ngas_mirroring_bookkeeping add staging_file varchar2(256) null';
  end if;

  select count(table_name) into cnt from user_tab_columns where table_name='NGAS_MIRRORING_BOOKKEEPING' and COLUMN_NAME='ATTEMPT';
  if cnt = 0 then
    execute immediate 'alter table ngas_mirroring_bookkeeping add attempt number(4) null';
  end if;

  select count(table_name) into cnt from user_tab_columns where table_name='NGAS_MIRRORING_BOOKKEEPING' and COLUMN_NAME='DOWNLOADED_BYTES';
  if cnt = 0 then
    execute immediate 'alter table ngas_mirroring_bookkeeping add downloaded_bytes number(22) null';
  end if;
end;
/
