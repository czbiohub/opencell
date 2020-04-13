-- force drop all connections
SELECT pg_terminate_backend(pid)
FROM pg_stat_activity
WHERE datname = 'opencelldb';


-- cell line metadata
CREATE OR REPLACE VIEW public.cell_line_metadata AS
 SELECT cd.plate_design_id AS plate_id,
    cd.well_id,
    cd.target_name,
    cell_line.id AS cell_line_id
   FROM crispr_design cd
     INNER JOIN plate_design pd ON pd.design_id::text = cd.plate_design_id::text
     INNER JOIN plate_instance pi ON pd.design_id::text = pi.plate_design_id::text
     INNER JOIN electroporation ep ON pi.id = ep.plate_instance_id
     INNER JOIN electroporation_line epl ON ep.id = epl.electroporation_id AND cd.well_id = epl.well_id
     INNER JOIN cell_line ON cell_line.id = epl.cell_line_id
  ORDER BY (ROW(cd.plate_design_id, cd.well_id));


-- exposure settings for microscopy FOVs with basic cell line metadata
select plate_id, well_id, target_name, fov.cell_line_id, pml_id, fov_id,
  data::json ->> 'exposure_time_488' as exposure_time_488,
  data::json ->> 'laser_power_488_488' as laser_power_488,
  raw_filename
from cell_line_metadata clm
  inner join microscopy_fov fov on clm.cell_line_id = fov.cell_line_id
  inner join microscopy_fov_result fov_result on fov.id = fov_result.fov_id
where fov_result.kind = 'raw-tiff-metadata'
order by (plate_id, well_id, pml_id);


-- the top-scoring FOV and its score for each cell line
select * from (
	select fov.cell_line_id, fov.id as fov_id, (data::json ->> 'score')::float as score,
		row_number() over (
			partition by fov.cell_line_id
			order by coalesce((data::json ->> 'score')::float, -1) desc
		) as rank
	from microscopy_fov fov
	  left join microscopy_fov_result result on fov.id = result.fov_id
	where result.kind = 'fov-features'
) ranked_fovs
where rank = 1
order by score desc;


-- filter by existence of a json key (where `data` is a JSON-typed column)
select * from microscopy_fov_result where data::jsonb ? 'num_nuclei';

-- groupby a json value
select data::json ->> 'num_nuclei' as n, count(*) as c from microscopy_fov_result
group by n order by c desc;

-- groupby the 2nd element of an array in a json object
select count(fov_id) as n, (props::json ->> 'position')::json ->> 2 as p from microscopy_fov_roi
group by p order by n desc;

-- the number of cell line annotations with a particular category
select * from(
	select *, array(select json_array_elements_text(categories::json)) as cats
	from cell_line_annotation) ants
where 're_sort' = any(cats);



-- drop all rows from all microscopy-related tables
TRUNCATE microscopy_dataset CASCADE;

-- rename a table
ALTER TABLE table_name RENAME TO new_table_name;

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


-- count FOVs per dataset
select d.pml_id as pml_id, d.date, count(fov.id) from microscopy_dataset d
left join microscopy_fov fov on d.pml_id = fov.pml_id
group by d.pml_id, d.date
order by d.pml_id desc;

-- count FOVs (or pulldowns) per cell line
select * from cell_line_metadata
left join (
	select cell_line_id, count(*) as n from microscopy_fov
	group by cell_line_id
	order by n desc
) pd using (cell_line_id);

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
		select pml_id from microscopy_dataset where root_directory = 'raw_pipeline_microscopy'
	)
);

-- select (or delete) all but the most recent MicroscopyFOVResult of a particular kind for each FOV
select * from microscopy_fov_result
where kind = 'fov-features'
and (fov_id, date_created) not in (
	select fov_id, max(date_created) from microscopy_fov_result
	where kind = 'fov-features'
	group by fov_id
);

-- FOVs that cannot be 'cleaned' (that is, cropped in z)
select * from microscopy_fov_result
where kind = 'clean-tiff-metadata'
and data ->> 'error' is not null
order by date_created desc;

-- all targets that are *not* annotated 'no_gfp' and that do not have any annotated FOVs
select * from (
	select *, array(select json_array_elements_text(categories::json)) as cats
	from cell_line_annotation
) cla
left join cell_line_metadata clm on cla.cell_line_id = clm.cell_line_id
where clm.cell_line_id not in (
	select cell_line_id from microscopy_fov_annotation ant
	left join microscopy_fov fov on fov.id = ant.fov_id
)
and not ('no_gfp' = any(cats))
order by (plate_id, well_id);

-- group results by day
select count(*), to_char(date_created, 'YYYY-MM-DD') as d from microscopy_fov_result
group by d;
