

alter table ngas_mirroring_bookkeeping
    add source_ingestion_date date default sysdate not null;

alter table ngas_mirroring_bookkeeping
    drop column archive_command;

alter table ngas_mirroring_bookkeeping
    drop column retrieve_command;

create table alma_mirroring_exclusions (
  id integer not null,
  rule_type varchar2(8) not null,
  file_pattern varchar2(64) not null,
  ingestion_start timestamp not null,
  ingestion_end timestamp not null,
  arc varchar2(6)
);

-- it's a pain to look in the logfiles of all nodes in a cluster. The most important log messages should
-- be centrally logged to DB.
create table ngas_alerts (
  id integer not null,
  server_name varchar2(128) not null,
  raised_time timestamp not null,
  level varchar2(8) not null,
  message varchar2(512) not null
);

create sequence ngas_seq;

insert into alma_mirroring_exclusions (id, rule_type, file_pattern, ingestion_start, ingestion_end, arc) values (ngas_seq.nextval, 'EXCLUDE', 'ALMA%.tar', sysdate, to_timestamp('2222-01-01', 'YYYY-MM-DD'), 'HERE');
insert into alma_mirroring_exclusions (id, rule_type, file_pattern, ingestion_start, ingestion_end, arc) values (ngas_seq.nextval, 'EXCLUDE', 'backup%.tar', sysdate, to_timestamp('2222-01-01', 'YYYY-MM-DD'), 'HERE');
insert into alma_mirroring_exclusions (id, rule_type, file_pattern, ingestion_start, ingestion_end, arc) values (ngas_seq.nextval, 'EXCLUDE', 'TMC%.tar', sysdate, to_timestamp('2222-01-01', 'YYYY-MM-DD'), 'HERE');
insert into alma_mirroring_exclusions (id, rule_type, file_pattern, ingestion_start, ingestion_end, arc) values (ngas_seq.nextval, 'EXCLUDE', 'XMLLOG%.tar', sysdate, to_timestamp('2222-01-01', 'YYYY-MM-DD'), 'HERE');

insert into ngas_cfg_pars (cfg_group_id, cfg_par, cfg_val, cfg_comment) values ('alma_mirroring', 'masterNode', 'ngassco01:7771:', 'ngas_id of the mirroring master node. There is only expected to be one per database.');
insert into ngas_cfg_pars (cfg_group_id, cfg_par, cfg_val, cfg_comment) values ('alma_mirroring', 'archiveHandlingUnit', 'ngas04:7778', 'ngas_id of the AHU node.');
insert into ngas_cfg_pars (cfg_group_id, cfg_par, cfg_val, cfg_comment) values ('alma_mirroring', 'siteId', 'SCO', 'site identifier - must be one of EU, EA, NA, SCO or OSF');
insert into ngas_cfg_pars (cfg_group_id, cfg_par, cfg_val, cfg_comment) values ('alma_mirroring', 'sleepTime', '900', 'sleep time (in seconds) between the end of one mirroring iteration and the start of the next');
insert into ngas_cfg_pars (cfg_group_id, cfg_par, cfg_val, cfg_comment) values ('alma_mirroring', 'numParallelFetches', '15', 'number of threads per ngams server used for fetching files');
insert into ngas_cfg_pars (cfg_group_id, cfg_par, cfg_val, cfg_comment) values ('alma_mirroring', 'baselineDate', '1970-01-01', '(year-month-date): basline date for mirroring');
insert into ngas_cfg_pars (cfg_group_id, cfg_par, cfg_val, cfg_comment) values ('alma_mirroring', 'iterationFileLimit', 'None', 'maximum number of files to fetch in each iteration (None means no limit)');
