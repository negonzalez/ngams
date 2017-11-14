

drop table ngas.ngas_mirroring_bookkeeping;
commit;

Create table ngas.ngas_mirroring_bookkeeping (
       file_id            varchar2(64)    not null, 
       file_version       number(22)      not null, 
       file_size          number(20)          null,
       disk_id            varchar2(128)       null,
       host_id            varchar2(32)        null,
       format             varchar2(32)        null,
       status             char(8)         not null,
       target_cluster     varchar2(64)        null,
       target_host        varchar2(64)        null, 
       archive_command    varchar2(118)       null,
       source_host        varchar2(64)    not null,
       retrieve_command   varchar2(118)       null,
       ingestion_date     varchar2(23)        null,
       ingestion_time     float(126)          null,
       iteration          number(22)      not null, 
       checksum 		  varchar2(64) 	  not null,
       staging_file       varchar2(256)       null,
       attempt            number(4)           null,
       downloaded_bytes   number(22)          null,
       constraint ngas_mirroring_bookkeeping_idx primary key(file_id, file_version, iteration)
);

grant insert, update, delete, select on ngas.ngas_mirroring_bookkeeping to ngas;
grant select on ngas.ngas_mirroring_bookkeeping to public;
commit;

create index nmb_iter_status_idx on ngas_mirroring_bookkeeping(iteration, status);

create index nmb_thost_status_shost_idx on ngas_mirroring_bookkeeping(target_cluster, target_host, status, source_host);


