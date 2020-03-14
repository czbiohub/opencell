import manualMetadata from '../demo/data/manual_metadata.json';
import uniprotMetadata from '../demo/data/uniprot_metadata.json';
import facsGrades from '../demo/data/facs_grades.json';


// column defs for the datatable; also used by header.jsx
// the single argument of the accessor methods is assumed to be
// a JSON object of cell line metadata returned by the '/lines' endpoint
const cellLineMetadataDefinitions = [
    {   
        id: 'protein_name',
        accessor: row => {
            const maxLength = 20;
            const targetName = row.metadata?.target_name;
            if (!targetName) return null;
            let name = (
                manualMetadata[targetName]?.protein_name ||
                manualMetadata[targetName]?.description ||
                uniprotMetadata[targetName]?.protein_name
            );
            name = name ? name : '';
            name = name.split('(')[0].split(',')[0].trim();
            name = name.length > maxLength ? `${name.slice(0, maxLength)}...` : name;
            return name
        },
        Header: 'Protein name',
        units: null,
    },{
        id: 'target_family',
        accessor: row => {
            let value = row.metadata?.target_family || 'null';
            return value ? value.charAt(0).toUpperCase() + value.slice(1) : null;
        },
        Header: 'Family',
        units: '',
    },{
        id: 'target_terminus',
        accessor: row => row.metadata?.target_terminus,
        Header: 'Term',
        units: null,
    },{
        id: 'uniprot_id',
        accessor: row => row.metadata ? uniprotMetadata[row.metadata.target_name]?.uniprot_id : null,
        Header: 'Uniprot ID'
    },{
        id: 'plate_id',
        accessor: row => parseInt(row.metadata?.plate_id?.slice(1)),
        Header: 'Plate',
        units: null,
    },{
        id: 'well_id',
        accessor: row => row.metadata?.well_id,
        Header: 'Well',
        units: null,
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
        units: '',
    }
];


const fovMetadataDefinitions = [
    {
        id: 'laser_power',
        Header: 'Laser power',
        accessor: fov => fov.laser_power_488?.toFixed(1),
        units: '%',
    },{
        id: 'exposure_time',
        Header: 'Exposure time',
        accessor: fov => fov.exposure_time_488?.toFixed(),
        units: 'ms',
    },{
        id: 'max_intensity',
        Header: 'Max intensity',
        accessor: fov => fov.max_intensity_488,
        units: '',
    },{
        id: 'score',
        Header: 'Score',
        accessor: fov => fov.score?.toFixed(2) || 'NA',
        units: '',
    },{
        id: 'step_size',
        Header: 'Step size',
        accessor: fov => fov.z_step_size?.toFixed(1),
        units: 'um',
    },{
        id: 'pml_id',
        Header: 'Dataset ID',
        accessor: fov => fov.pml_id,
        units: '',
    },{
        id: 'fov_id',
        Header: 'FOV ID',
        accessor: fov => fov.id,
        units: '',
    }
];


export {
    cellLineMetadataDefinitions,
    fovMetadataDefinitions,
};