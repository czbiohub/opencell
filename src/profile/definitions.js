import manualMetadata from '../demo/data/manual_metadata.json';
import uniprotMetadata from '../demo/data/uniprot_metadata.json';


// column defs for the datatable; also used by header.jsx
// the single argument of the accessor methods is assumed to be
// a JSON object of cell line metadata returned by the '/lines' endpoint
export const metadataDefinitions = [
    {   
        id: 'protein_name',
        accessor: row => {
            let name = (
                manualMetadata[row.target_name]?.protein_name ||
                manualMetadata[row.target_name]?.description ||
                uniprotMetadata[row.target_name]?.protein_name
            );
            name = name ? name : '';
            name = name.split('(')[0].split(',')[0].trim();
            name = name.length > 35 ? `${name.slice(0, 35)}...` : name;
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
        id: 'uniprot_id',
        accessor: row => uniprotMetadata[row.target_name]?.uniprot_id,
        Header: 'Uniprot ID'
    },{
        id: 'plate_id',
        accessor: row => row.plate_design_id,
        Header: 'Plate ID',
        units: null,
    },{
        id: 'well_id',
        accessor: row => row.well_id,
        Header: 'Well ID',
        units: null,
    },{
        id: 'hek_tpm',
        accessor: row => Math.round(row.hek_tpm),
        Header: 'Expression (tpm)',
        units: 'tpm',
    },
    // {
    //     id: 'facs_intensity',
    //     accessor: row => row.facs_results.rel_median_log,
    //     Header: 'FACS intensity (log a.u.)',
    //     units: 'log a.u.',
    // },{
    //     id: 'facs_area',
    //     accessor: row => Math.round(row.facs_results.area*100),
    //     Header: 'FACS area (%)',
    //     units: '%',
    // },
];

