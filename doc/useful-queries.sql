
-- cell line metadata
CREATE OR REPLACE VIEW public.cell_line_metadata AS
 SELECT cd.plate_design_id AS plate_id,
    cd.well_id,
    cd.target_name,
    cell_line.id AS cell_line_id
   FROM crispr_design cd
     JOIN plate_design pd ON pd.design_id::text = cd.plate_design_id::text
     JOIN plate_instance pi ON pd.design_id::text = pi.plate_design_id::text
     JOIN electroporation ep ON pi.id = ep.plate_instance_id
     JOIN electroporation_line epl ON ep.id = epl.electroporation_id AND cd.well_id = epl.well_id
     JOIN cell_line ON cell_line.id = epl.cell_line_id
  ORDER BY (ROW(cd.plate_design_id, cd.well_id));

ALTER TABLE public.cell_line_metadata
    OWNER TO postgres;


-- exposure settings for microscopy FOVs with basic cell line metadata
select plate_id, well_id, target_name, fov.cell_line_id, pml_id, fov_id,
  data::json ->> 'exposure_time_488' as exposure_time_488,
  data::json ->> 'laser_power_488_488' as laser_power_488,
  raw_filename
from cell_line_metadata clm
  join microscopy_fov fov on clm.cell_line_id = fov.cell_line_id
  join microscopy_fov_result fov_result on fov.id = fov_result.fov_id
where fov_result.kind = 'raw-tiff-metadata'
order by (plate_id, well_id, pml_id);


-- filter by existence of a json key (where `data` is a JSON-typed column)
select * from microscopy_fov_result
where data::jsonb ? 'num_nuclei';

-- groupby a json value
select data::json ->> 'num_nuclei' as n, count(*) as c from microscopy_fov_result
group by n order by c desc;

-- groupby the 2nd element of an array in a json object
select count(fov_id) as n, (props::json ->> 'position')::json ->> 2 as p from microscopy_fov_roi
group by p order by n desc;

-- count kinds of fov results
select kind, count(kind) from microscopy_fov_result
left join microscopy_fov on microscopy_fov.id = microscopy_fov_result.fov_id
group by kind;


-- drop all rows from all microscopy-related tables
TRUNCATE microscopy_dataset CASCADE;

-- rename a column
ALTER TABLE table_name RENAME COLUMN column_name TO new_column_name;

-- add a column to an existing table
ALTER TABLE table_name ADD COLUMN column_name data_type;

-- remove a column from an existing table
ALTER TABLE table_name DROP COLUMN column_name [CASCADE];

-- replace a string in a column
UPDATE microscopy_fov_result
SET column = REPLACE (column, 'old-string', 'new-string');

-- add on delete cascade to microscopy_fov_result foreign key
ALTER TABLE microscopy_fov_result
DROP CONSTRAINT fk_microscopy_fov_result_fov_id_microscopy_fov,
ADD CONSTRAINT fk_microscopy_fov_result_fov_id_microscopy_fov FOREIGN KEY (fov_id)
   REFERENCES public.microscopy_fov (id) MATCH SIMPLE
   ON UPDATE NO ACTION
   ON DELETE CASCADE;


-- delete FOVs and descendents from particular datasets
delete from microscopy_fov_result
where fov_id in (
	select id from microscopy_fov
	where pml_id in ('PML0227', 'PML0233', 'PML0234')
);
delete from microscopy_fov
where pml_id in ('PML0227', 'PML0233', 'PML0234');


-- delete all results for raw-pipeline-microscopy datasets
delete from microscopy_fov_result
where fov_id in (
	select id from microscopy_fov where pml_id in (
		select pml_id from microscopy_dataset where root_directory like 'raw_%'
	)
);


-- select (or delete) all but the most recent result of a particular kind for each FOV
select * from microscopy_fov_result
where kind = 'fov-features'
and (fov_id, timestamp) not in (
	select fov_id, max(timestamp) from microscopy_fov_result
	where kind = 'fov-features'
	group by fov_id
);
