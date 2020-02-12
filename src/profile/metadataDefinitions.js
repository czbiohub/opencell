import manualMetadata from '../demo/data/manual_metadata.json';
import uniprotMetadata from '../demo/data/uniprot_metadata.json';
import facsGrades from '../demo/data/facs_grades.json';


// column defs for the datatable; also used by header.jsx
// the single argument of the accessor methods is assumed to be
// a JSON object of cell line metadata returned by the '/lines' endpoint
const metadataDefinitions = [
    {   
        id: 'protein_name',
        accessor: row => {
            const maxLength = 20; // previously was 35
            let name = (
                manualMetadata[row.target_name]?.protein_name ||
                manualMetadata[row.target_name]?.description ||
                uniprotMetadata[row.target_name]?.protein_name
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
            let value = row.target_family || 'null';
            return value ? value.charAt(0).toUpperCase() + value.slice(1) : null;
        },
        Header: 'Family',
        units: '',
    },{
        id: 'target_terminus',
        accessor: row => row.target_terminus,
        Header: 'Term',
        units: null,
    },{
        id: 'uniprot_id',
        accessor: row => uniprotMetadata[row.target_name]?.uniprot_id,
        Header: 'Uniprot ID'
    },{
        id: 'plate_id',
        accessor: row => parseInt(row.plate_id?.slice(1)),
        Header: 'Plate',
        units: null,
    },{
        id: 'well_id',
        accessor: row => row.well_id,
        Header: 'Well',
        units: null,
    },{
        id: 'hek_tpm',
        accessor: row => Math.round(row.scalars?.hek_tpm),
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
        accessor: row => facsGrades[`${row.plate_id}-${row.well_id}`],
        Header: 'FACS',
        units: '',
    }
];


export default metadataDefinitions;