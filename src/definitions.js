

export const columnDefs = [
    {
        Header: 'Plate ID',
        accessor: 'plate_design_id',
        width: 50,
    },{
        Header: 'Well ID',
        accessor: 'well_id',
        width: 50,
    },{
        Header: 'EP date',
        id: 'electroporation_date',
        accessor: d => {
            // hack-ish way to display the date in the form '%Y-%m-%d'
            const date = new Date(d.electroporation_date); 
            return date.toJSON() ? date.toJSON().slice(0, 10) : 'missing date';
        },
    },{
        Header: 'Gene name',
        accessor: 'target_name',
        width: 100,
    },{
        Header: 'Gene family',
        accessor: 'target_family',
        width: 100,
    },{
        Header: 'Terminus',
        accessor: 'target_terminus',
        width: 50,
    },{
        Header: 'ENST ID',
        accessor: 'transcript_id',
        width: 150,
    },{
        Header: 'TPM (HEK293)',
        accessor: 'hek_tpm',
        width: 70,
    },{
        Header: 'Protospacer name',
        accessor: 'protospacer_name',
    },{
        Header: 'Protospacer notes',
        accessor: 'protospacer_notes',
    },{
        Header: 'Protospacer sequence',
        accessor: 'protospacer_sequence',
    },{
        Header: 'Template name',
        accessor: 'template_name',
    },{
        Header: 'Template notes',
        accessor: 'template_notes',
    },{
        Header: 'Template sequence',
        accessor: 'template_sequence',
    },{
        id: 'facs_area',
        Header: 'FACS area',
        accessor: row => {
            if (row.facs) return row.facs.area;
            return undefined;
        }
    },{
        id: 'facs_rel_median_log',
        Header: 'FACS intensity (median)',
        accessor: row => {
            if (row.facs) return row.facs.rel_median_log;
            return undefined;
        }
    },{
        id: 'facs_rel_percentile99_log',
        Header: 'FACS intensity (max)',
        accessor: row => {
            if (row.facs) return row.facs.rel_percentile99_log;
            return undefined;
        }
    },{
        id: 'facs_raw_std',
        Header: 'FACS width',
        accessor: row => {
            if (row.facs) return row.facs.raw_std;
            return undefined;
        }
    },{
        id: 'facs_plot',
        Header: 'FACS plot',
        accessor: row => null,
    },
];

// copy id from accessor
// *** WARNING: this assumes that columnDefs without an id have a string-valued accessor ***
columnDefs.forEach(def => def.id = def.id ? def.id : def.accessor);

// default selected columns
export const defaultSelectedColumns = [
    'plate_design_id', 'well_id', 'target_name', 'target_family'];


export const columnGroups = [
    {
        name: 'Metadata',
        ids: [
            'plate_design_id', 
            'well_id', 
            'electroporation_date',
        ],
    },{
        name: 'Target',
        ids: [
            'target_name', 
            'target_family', 
            'target_terminus', 
            'transcript_id', 
            'hek_tpm'],
    },{
        name: 'Crispr design',
        ids: [
            'protospacer_name', 
            'protospacer_notes', 
            'protospacer_sequence',
            'template_name', 
            'template_notes', 
            'template_sequence',
            ''
        ],
    },{
        name: 'FACS',
        ids: [
            'facs_area',
            'facs_rel_median_log',
            'facs_rel_percentile99_log',
            'facs_raw_std',
            'facs_plot',
        ],
    },{
        name: 'Sequencing',
        ids: [],
    },{
        name: 'Imaging',
        ids: [],
    },{
        name: 'Annotations',
        ids: [],
    }
];


// definitions for filters
export const filterDefs = [
    {
        name: 'Plate ID',
        accessor: 'plate_design_id',
        values: [],
    },{
        name: 'Gene family',
        accessor: 'target_family',
        values: [],
    },{
        name: 'FACS score',
        accessor: 'facs_score',
        values: [],
    }
];

