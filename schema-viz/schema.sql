--
-- draft of pipeline database schema
--
--
-- Usage
-- -----
-- psql -f schema.sql -v dbname="dbname"
--
-- Keith Cheveralls
-- June 2019
--

---------------------------------------------------------------------------------------------------
--
-- disallow new connections
UPDATE pg_database SET datallowconn = 'false' 
WHERE datname = :'dbname';

-- force drop any existing connections
SELECT pg_terminate_backend(pid) FROM pg_stat_activity 
WHERE datname = :'dbname';

-- drop the database
DROP DATABASE IF EXISTS :dbname;
--
---------------------------------------------------------------------------------------------------


CREATE DATABASE :dbname WITH 
    OWNER = postgres
    ENCODING = 'UTF8' 
    LC_COLLATE = 'en_US.UTF-8' 
    LC_CTYPE = 'en_US.UTF-8';

\connect :dbname

-- TODO: what are these doing?
SET search_path = public, pg_catalog;
SET default_tablespace = '';


CREATE TYPE WELL_ID AS ENUM (
    'A01', 'A02', 'A03', 'A04', 'A05', 'A06', 'A07', 'A08', 'A09', 'A10', 'A11', 'A12', 
    'B01', 'B02', 'B03', 'B04', 'B05', 'B06', 'B07', 'B08', 'B09', 'B10', 'B11', 'B12', 
    'C01', 'C02', 'C03', 'C04', 'C05', 'C06', 'C07', 'C08', 'C09', 'C10', 'C11', 'C12',
    'D01', 'D02', 'D03', 'D04', 'D05', 'D06', 'D07', 'D08', 'D09', 'D10', 'D11', 'D12', 
    'E01', 'E02', 'E03', 'E04', 'E05', 'E06', 'E07', 'E08', 'E09', 'E10', 'E11', 'E12', 
    'F01', 'F02', 'F03', 'F04', 'F05', 'F06', 'F07', 'F08', 'F09', 'F10', 'F11', 'F12',
    'G01', 'G02', 'G03', 'G04', 'G05', 'G06', 'G07', 'G08', 'G09', 'G10', 'G11', 'G12', 
    'H01', 'H02', 'H03', 'H04', 'H05', 'H06', 'H07', 'H08', 'H09', 'H10', 'H11', 'H12'
);



-- master table of cell lines (includes progenitor, polyclonal, and monoclonal lines)
CREATE TABLE cell_line (
    -- surrogate primary key
    id                    serial PRIMARY KEY,
    parent_id             integer,
    nickname              varchar UNIQUE,
    notes                 varchar,
    FOREIGN KEY (parental_id) REFERENCES cell_line (id)
);


CREATE TABLE plate_design (
    -- primary key design_id is the human-assigned plate number (1, 2, 3, ..., 19)
    -- think about the best form for this (e.g., 'P0019' instead of 19)
    design_id           integer PRIMARY KEY,
    design_date         date,
    design_notes        varchar
);


CREATE TABLE crispr_design (
    -- surrogate primary key, but (well_id, plate_design_id) should be unique

    id                     serial PRIMARY KEY,
    well_id               WELL_ID,
    plate_design_id       integer,

    -- human-readable gene name
    target_name             varchar,
    -- ensemble transcript id (ENSTxxxx)
    transcript_id           varchar,
    -- N or C terminus
    target_terminus         varchar,
    -- repair template (ultramer) sequence (usually 200bp)
    template_sequence       varchar,
    -- guide sequence (20bp)
    protospacer_sequence    varchar,
    -- arbitrary design notes scraped from google sheets
    design_notes            varchar,

    UNIQUE (plate_design_id, well_id),
    FOREIGN KEY (plate_design_id) REFERENCES plate_design (design_id)
);


CREATE TABLE plate_instance (
    -- primary key plate_id is human-assigned 
    -- and is of the form '{design_id}-{batch_number}' (for example: 'P0019-01')
    plate_instance_id     varchar PRIMARY KEY,
    plate_design_id       integer,
    instance_date         date,
    instance_notes        varchar,
    FOREIGN KEY (plate_design_id) REFERENCES plate_design (design_id)
);


CREATE TABLE electroporation (
    -- surrogate primary key
    -- (cell_line_id, plate_instance_id, ep_date) should be unique
    id                       serial PRIMARY KEY,
    cell_line_id             integer,
    plate_instance_id        varchar,
    ep_date                  date,

    -- UNIQUE (plate_instance_id, ep_date, parental_cell_line_id),
    FOREIGN KEY (plate_instance_id) REFERENCES plate_instance (plate_instance_id),
    FOREIGN KEY (cell_line_id) REFERENCES cell_line (id)
);


CREATE TABLE facs_dataset (
    -- composite primary key (electroporation_id, well_id)
    -- note: no foreign key to the cell_line table, because FACS precedes cell line existence
    electroporation_id       integer,
    well_id                  WELL_ID,
    quality_grade            varchar, -- A, B, C, or D
    figure_filepath          varchar,
    sort_data_filepath       varchar,
    profile_data_filepath    varchar,
    PRIMARY KEY (electroporation_id, well_id),
    FOREIGN KEY (electroporation_id) REFERENCES electroporation (id)
);


-- table to map electroporations and well_ids to cell_line_id
CREATE TABLE electroporation_line (
    -- composite primary key is (electroporation_id, well_id)
    line_id               integer,
    well_id               WELL_ID,
    electroporation_id    integer,
    PRIMARY KEY (electroporation_id, well_id),
    FOREIGN KEY (electroporation_id) REFERENCES electroporation (id),
    FOREIGN KEY (line_id) REFERENCES cell_line (id)
);


CREATE TABLE imaging_experiment (
    -- surrogate primary key
    -- exp_name should also be unique and corresponds to a microscopy experiment id, like 'ML0037'
    id                    serial PRIMARY KEY,
    exp_name              varchar,
    exp_date              date,
    exp_notes             varchar
);


CREATE TABLE imaging_dataset (
    -- composite primary key (experiment_id, well_id, fov_id)
    -- dataset_serial enables 1-to-1 mapping to the dataset table of imagingDB
    id                    serial PRIMARY KEY,
    cell_line_id          integer,
    experiment_id         integer,
    well_id               WELL_ID,
    fov_id                integer,
    filepath              varchar,
    dataset_serial        varchar,
    UNIQUE (experiment_id, well_id, fov_id),
    FOREIGN KEY (cell_line_id) REFERENCES cell_line (id),
    FOREIGN KEY (experiment_id) REFERENCES imaging_experiment (id)
);


CREATE TABLE localization_annotation (
    -- serial primary key
    id     serial PRIMARY KEY,
    cell_line_id      integer,
    username          varchar,
    localization      varchar,
    FOREIGN KEY (cell_line_id) REFERENCES cell_line (id)
);


-- imaging quality annotations
CREATE TABLE imaging_dataset_annotation (
    -- serial primary key
    id                    serial PRIMARY KEY,
    imaging_dataset_id    integer,
    username              varchar,
    is_overexposed        boolean,
    is_heterogeneous      boolean,
    is_confluent          boolean,
    FOREIGN KEY (imaging_dataset_id) REFERENCES imaging_dataset (id)
);


CREATE TABLE comment (
    -- serial primary key
    id     serial PRIMARY KEY,
    cell_line_id      integer,
    username          varchar,
    comment_date      date,
    comment_content   varchar,
    FOREIGN KEY (cell_line_id) REFERENCES cell_line (id)
);


GRANT ALL ON SCHEMA public TO postgres;
GRANT ALL ON SCHEMA public TO PUBLIC;
