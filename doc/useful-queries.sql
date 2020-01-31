
-- all electroporations with their plate designs
select * from electroporation, plate_instance, plate_design
where electroporation.plate_instance_id = plate_instance.id
and plate_instance.plate_design_id = plate_design.design_id
order by plate_design_id
limit 100;


-- all polyclonal cell lines with well_id, target_name, and microscopy FOVs
-- for a particular plate
select cell_line.id as cell_line_id, cd.well_id, cd.plate_design_id, cd.target_name, fov.* from 
crispr_design cd inner join plate_design pd on pd.design_id = cd.plate_design_id
inner join plate_instance pi on pd.design_id = pi.plate_design_id
inner join electroporation ep on pi.id = ep.plate_instance_id
inner join electroporation_line epl on (ep.id, cd.well_id) = (epl.electroporation_id, epl.well_id)
inner join cell_line on cell_line.id = epl.cell_line_id
left join microscopy_fov fov on cell_line.id = fov.cell_line_id
where cd.plate_design_id = 'P0019';


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


-- delete FOVs and descendents from particular datasets
delete from microscopy_fov_result
where fov_id in (
	select id from microscopy_fov
	where pml_id in ('PML0227', 'PML0233', 'PML0234')
);
delete from microscopy_fov
where pml_id in ('PML0227', 'PML0233', 'PML0234');


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

-- delete all results for raw-pipeline-microscopy datasets
delete from microscopy_fov_result
where fov_id in (
	select id from microscopy_fov where pml_id in (
		select pml_id from microscopy_dataset where root_directory like 'raw_%'
	)
);