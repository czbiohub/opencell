
import facsGrades from '../demo/data/facs_grades.json';


// column defs for the datatable; also used by header.jsx
// the single argument of the accessor methods is assumed to be
// a JSON object of cell line metadata returned by the '/lines' endpoint
const cellLineMetadataDefinitions = [
    {   
        id: 'protein_name',
        accessor: row => row.uniprot_metadata?.protein_name,
        Header: 'Protein name',
    },{
        id: 'target_family',
        accessor: row => {
            let value = row.metadata?.target_family || 'NA';
            return value ? value.charAt(0).toUpperCase() + value.slice(1) : null;
        },
        Header: 'Family',
    },{
        id: 'target_terminus',
        accessor: row => row.metadata?.target_terminus,
        Header: 'Terminus',
    },{
        id: 'uniprot_id',
        accessor: row => row.uniprot_metadata?.uniprot_id,
        Header: 'Uniprot ID'
    },{
        id: 'ensg_id',
        accessor: row => row.metadata?.ensg_id,
        Header: 'ENSG ID'
    },{
        id: 'plate_id',
        accessor: row => parseInt(row.metadata?.plate_id?.slice(1)),
        Header: 'Plate',
    },{
        id: 'well_id',
        accessor: row => row.metadata?.well_id,
        Header: 'Well',
    },{
        id: 'sort_count',
        accessor: row => row.metadata?.sort_count,
        Header: 'Sort count',
    },{
        id: 'hek_tpm',
        accessor: row => Math.round(row.metadata?.hek_tpm),
        Header: 'Expression (tpm)',
        units: 'tpm',
    },{
        id: 'facs_intensity',
        accessor: row => row.scalars?.facs_intensity?.toFixed(2),
        Header: 'FACS intensity (log a.u.)',
        units: 'log a.u.',
    },{
        id: 'facs_area',
        accessor: row => Math.round(row.scalars?.facs_area*100),
        Header: 'FACS area (%)',
        units: '%',
    },{
        id: 'hdr_all',
        accessor: row => Math.round(100*row.scalars?.hdr_all),
        Header: 'HDR/all',
        units: '%',
    },{
        id: 'hdr_modified',
        accessor: row => Math.round(100*row.scalars?.hdr_modified),
        Header: 'HDR/mod',
        units: '%',
    },{
        id: 'facs_grade',
        accessor: row => facsGrades[`${row.metadata?.plate_id}-${row.metadata?.well_id}`],
        Header: 'FACS',
    },{
        id: 'publication_ready',
        accessor: row => String(row.annotation.categories?.includes('publication_ready')),
        Header: 'Pub ready',
    },{
        id: 're_image',
        accessor: row => String(row.annotation.categories?.includes('re_image')),
        Header: 'Re-image',
    },{
        id: 'no_gfp',
        accessor: row => String(row.annotation.categories?.includes('no_gfp')),
        Header: 'No GFP',
    },{
        id: 'low_gfp',
        accessor: row => String(row.annotation.categories?.includes('low_gfp')),
        Header: 'Low GFP',
    },{
        id: 're_sort',
        accessor: row => String(row.annotation.categories?.includes('salvageable_re_sort')),
        Header: 'Salvageable re-sort',
    },{
        id: 'num_fovs',
        accessor: row => row.counts.num_fovs,
        Header: 'Num FOVs',
    },{
        id: 'num_annoted_fovs',
        accessor: row => row.counts.num_annotated_fovs,
        Header: 'Num annotated FOVs',
    },{
        id: 'graded_annotations',
        accessor: row => String(row.annotation.has_graded_annotations),
        Header: 'Graded annotations',
    }
];


const fovMetadataDefinitions = [
    {
        id: 'laser_power',
        Header: 'Laser power',
        accessor: fov => fov.metadata?.laser_power_488?.toFixed(1),
        units: '%',
    },{
        id: 'exposure_time',
        Header: 'Exposure time',
        accessor: fov => fov.metadata?.exposure_time_488?.toFixed(),
        units: 'ms',
    },{
        id: 'max_intensity',
        Header: 'Max intensity',
        accessor: fov => fov.metadata?.max_intensity_488,
    },{
        id: 'score',
        Header: 'Score',
        accessor: fov => fov.metadata?.score?.toFixed(2) || 'NA',
    },{
        id: 'step_size',
        Header: 'Step size',
        accessor: fov => fov.metadata?.z_step_size?.toFixed(1),
        units: 'um',
    },{
        id: 'cell_layer_center',
        Header: 'Cell layer center',
        accessor: fov => fov.metadata?.cell_layer_center?.toFixed(2),
        units: 'um',
    },{
        id: 'pml_id',
        Header: 'Dataset ID',
        accessor: fov => fov.metadata?.pml_id,
    },{
        id: 'fov_id',
        Header: 'FOV ID',
        accessor: fov => fov.metadata?.id,
    }
];


export {
    cellLineMetadataDefinitions,
    fovMetadataDefinitions,
};