DROP USER "NGAS" CASCADE;

CREATE USER "NGAS" PROFILE "DEFAULT" 
IDENTIFIED BY "ngas$dba" DEFAULT 
TABLESPACE "NGAS" TEMPORARY TABLESPACE "TEMP" ACCOUNT UNLOCK;

GRANT CONNECT TO "NGAS";
GRANT DBA TO "NGAS";
GRANT MGMT_USER TO "NGAS" WITH ADMIN OPTION;

GRANT DELETE ANY TABLE TO "NGAS";
GRANT IMPORT FULL DATABASE TO "NGAS";
GRANT INSERT ANY TABLE TO "NGAS";
GRANT SELECT ANY DICTIONARY TO "NGAS";
GRANT SELECT ANY TABLE TO "NGAS";
GRANT UPDATE ANY TABLE TO "NGAS";

commit;
disconnect;
quit
