
import pipelineMetadata from './data/pipeline_metadata.json';
import manualMetadata from './data/manual_metadata.json';


// column defs for the datatable; also used by header.jsx
export const metadataDefinitions = [
    {   
        id: 'protein_name',
        accessor: row => manualMetadata[row.targetName].protein_name,
        Header: 'Protein name',
        units: null,
    },{
        id: 'uniprot_id',
        accessor: row => manualMetadata[row.targetName].uniprot_id,
        Header: 'Uniprot ID',
        units: null,
    },{
        id: 'target_family',
        accessor: row => {
            let value = pipelineMetadata[row.targetName].target_family;
            return value.charAt(0).toUpperCase() + value.slice(1);
        },
        Header: 'Family',
        units: '',
    },{
        id: 'hek_tpm',
        accessor: row => Math.round(pipelineMetadata[row.targetName].hek_tpm),
        Header: 'Expression',
        units: 'tpm',
    },{
        id: 'hdr_all',
        accessor: row => Math.round(pipelineMetadata[row.targetName].sequencing_results.hdr_all*100),
        Header: 'HDR frequency',
        units: '%',
    },{
        id: 'facs_intensity',
        accessor: row => pipelineMetadata[row.targetName].facs_results.rel_median_log,
        Header: 'FACS intensity',
        units: 'log a.u.',
    }
];

