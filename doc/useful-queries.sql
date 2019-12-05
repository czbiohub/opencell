
-- all electroporations with their plate designs
select * from electroporation, plate_instance, plate_design
where electroporation.plate_instance_id = plate_instance.id
and plate_instance.plate_design_id = plate_design.design_id
order by plate_design_id
limit 100;


-- all polyclonal cell lines with their crispr designs
select cell_line.id as cell_line_id, cd.* from 
crispr_design cd inner join plate_design pd on pd.design_id = cd.plate_design_id
inner join plate_instance pi on pd.design_id = pi.plate_design_id
inner join electroporation ep on pi.id = ep.plate_instance_id
inner join electroporation_line epl on (ep.id, cd.well_id) = (epl.electroporation_id, epl.well_id)
inner join cell_line on cell_line.id = epl.cell_line_id;

