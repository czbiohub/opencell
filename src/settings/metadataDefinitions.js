
import facsGrades from '../data/facs_grades.json';


// column defs for the datatable; also used by header.jsx
// the single argument of the accessor methods is assumed to be
// a JSON object of cell line metadata returned by the '/lines' endpoint
const cellLineMetadataDefinitions = [
    {   
        id: 'protein_name',
        accessor: row => row.uniprot_metadata?.protein_name,
        Header: 'Gene description',
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
        Header: 'Tag terminus',
    },{
        id: 'protospacer_sequence',
        accessor: row => row.metadata?.protospacer_sequence,
        Header: 'CRISPR guide RNA sequence',
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
        accessor: row => row.facs?.intensity?.toFixed(2),
        Header: 'FACS intensity (log a.u.)',
        units: 'log a.u.',
    },{
        id: 'facs_area',
        accessor: row => Math.round(row.facs?.area*100),
        Header: 'FACS area (%)',
        units: '%',
    },{
        id: 'hdr_all',
        accessor: row => Math.round(100*row.sequencing?.hdr),
        Header: 'HDR/all',
        units: '%',
    },{
        id: 'other_all',
        accessor: row => Math.round(100*(row.sequencing?.nhej + row.sequencing?.mixed)),
        Header: 'other/all',
        units: '%',
    },{
        id: 'wt_all',
        accessor: row => Math.round(100*row.sequencing?.unmodified),
        Header: 'wt/all',
        units: '%',
    },{
        id: 'facs_grade',
        accessor: row => facsGrades[`${row.metadata?.plate_id}-${row.metadata?.well_id}`],
        Header: 'FACS grade',
    },{
        id: 'publication_ready',
        accessor: row => row.annotation.categories?.includes('publication_ready'),
        Header: 'Pub ready',
    },{
        id: 'has_pulldown',
        accessor: row => !!row.best_pulldown?.id,
        Header: 'Has pulldown',
    },{
        id: 'has_saved_network',
        accessor: row => !!row.best_pulldown?.has_saved_network,
        Header: 'Has saved network',
    },{
        id: 're_image',
        accessor: row => row.annotation.categories?.includes('re_image'),
        Header: 'Re-image',
    },{
        id: 'no_gfp',
        accessor: row => row.annotation.categories?.includes('no_gfp'),
        Header: 'No GFP',
    },{
        id: 'low_gfp',
        accessor: row => row.annotation.categories?.includes('low_gfp'),
        Header: 'Low GFP',
    },{
        id: 're_sort',
        accessor: row => row.annotation.categories?.includes('salvageable_re_sort'),
        Header: 'Salvageable re-sort',
    },{
        id: 'num_fovs',
        accessor: row => row.fov_counts?.num_fovs,
        Header: 'Num FOVs',
    },{
        id: 'num_annoted_fovs',
        accessor: row => row.fov_counts?.num_annotated_fovs,
        Header: 'Num annotated FOVs',
    },{
        id: 'only_old_annotated_fovs',
        accessor: row => row.fov_counts?.num_annotated_fovs > 0 && !row.fov_counts.num_annotated_fovs_da,
        Header: 'Annotated FOVs all old',
    },{
        id: 'graded_annotations',
        accessor: row => row.annotation.has_graded_annotations,
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


const sanitizeValue = value => {
    if (isNaN(value)) return String(value);
    if (typeof(value)==='boolean') return String(value);
    return value;
}

// wrap accessors to coerce all values to strings
cellLineMetadataDefinitions.forEach(def => {
    const accessor = def.accessor;
    def.accessor = row => sanitizeValue(accessor(row));
});

fovMetadataDefinitions.forEach(def => {
    const accessor = def.accessor;
    def.accessor = row => sanitizeValue(accessor(row));
});

export {
    cellLineMetadataDefinitions,
    fovMetadataDefinitions,
};