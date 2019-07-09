

export const columnDefs = [
    {
        Header: 'Plate ID',
        accessor: 'plate_design_id',
    },{
        Header: 'Well ID',
        accessor: 'well_id',
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
    },{
        Header: 'Gene family',
        accessor: 'target_family',
    },{
        Header: 'Terminus',
        accessor: 'target_terminus',
    },{
        Header: 'ENST ID',
        accessor: 'transcript_id',
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
    },
];

// copy id from accessor
columnDefs.forEach(def => def.id = def.id ? def.id : def.accessor);

// default selected columns
export const defaultSelectedColumns = [
    'plate_design_id', 'well_id', 'target_name', 'target_family'];


export const columnGroups = [
    {
        name: 'Metadata',
        ids: ['plate_design_id', 'well_id', 'electroporation_date'],
    },{
        name: 'Target',
        ids: ['target_name', 'target_family', 'target_terminus', 'transcript_id'],
    },{
        name: 'Crispr design',
        ids: [
            'protospacer_name', 'protospacer_notes', 'protospacer_sequence',
            'template_name', 'template_notes', 'template_sequence',
            ''
        ],
    },{
        name: 'Expression',
        ids: [],
    },{
        name: 'FACS',
        ids: [],
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

