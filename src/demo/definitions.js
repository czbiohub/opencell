
import pipelineMetadata from './data/20190816_pipeline-metadata.json';
import manualMetadata from './data/manual_metadata.json';
import uniprotMetadata from './data/uniprot_metadata.json';


// column defs for the datatable; also used by header.jsx
export const metadataDefinitions = [
    {   
        id: 'protein_name',
        accessor: row => {
            let name = (manualMetadata[row.targetName]?.protein_name ||
            manualMetadata[row.targetName]?.description ||
            uniprotMetadata[row.targetName]?.protein_name);
            name = name ? name.slice(0, 40) : '';
            return name;
        },
        Header: 'Protein name',
        units: null,
    },{
        id: 'target_family',
        accessor: row => {
            let value = pipelineMetadata[row.targetName]?.target_family;
            return value ? value.charAt(0).toUpperCase() + value.slice(1) : null;
        },
        Header: 'Family',
        units: '',
    },{
        id: 'uniprot_id',
        accessor: row => uniprotMetadata[row.targetName]?.uniprot_id,
        Header: 'Uniprot ID'
    }
    
    // {
    //     id: 'plate_id',
    //     accessor: row => pipelineMetadata[row.targetName].plate_design_id,
    //     Header: 'Plate ID',
    //     units: null,
    // },{
    //     id: 'well_id',
    //     accessor: row => pipelineMetadata[row.targetName].well_id,
    //     Header: 'Well',
    //     units: null,
    // },{
    //     id: 'hek_tpm',
    //     accessor: row => Math.round(pipelineMetadata[row.targetName].hek_tpm),
    //     Header: 'Expression',
    //     units: 'tpm',
    // },{
    //     id: 'facs_intensity',
    //     accessor: row => pipelineMetadata[row.targetName].facs_results.rel_median_log,
    //     Header: 'FACS intensity',
    //     units: 'log a.u.',
    // },{
    //     id: 'facs_area',
    //     accessor: row => Math.round(pipelineMetadata[row.targetName].facs_results.area*100),
    //     Header: 'FACS area',
    //     units: '%',
    // },
];

