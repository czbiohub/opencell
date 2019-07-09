

//     "cell_line_id": 2, 
//     "electroporation_date": "Tue, 16 Oct 2018 00:00:00 GMT", 
//     "facs_quality": null, 
//     "id": 381, 
//     "imaging_data": null, 
//     "plate_design_id": "P0005", 
//     "plate_instance_id": 5, 
//     "protospacer_name": "pl5_crRNA_A2_ACTB", 
//     "protospacer_notes": "cuts close to intron/exon junction", 
//     "protospacer_sequence": "GCTATTCTCGCAGCTCACCA", 
//     "sequencing_results": null, 
//     "target_family": "actin", 
//     "target_name": "ACTB", 
//     "target_terminus": "N_TERMINUS", 
//     "template_name": "pl5_mNG11_A2_ACTB", 
//     "template_notes": null, 
//     "template_sequence": "", 
//     "terminus_notes": "Allen collection", 
//     "transcript_id": "ENST00000331789", 
//     "transcript_notes": null, 
//     "well_id": "A02"


export const columnDefs = [
    {
        Header: 'Plate',
        accessor: 'plate_design_id',
    },{
        Header: 'Well',
        accessor: 'well_id',
    },{
        Header: 'Date',
        id: 'electroporation_date',
        accessor: d => {
            const date = new Date(d.electroporation_date); 
            return date.toJSON() ? date.toJSON().slice(0, 10) : 'missing date';
        },
    },{
        Header: 'Target',
        accessor: 'target_name',
    },{
        Header: 'Family',
        accessor: 'target_family',
    },{
        Header: 'Terminus',
        accessor: 'target_terminus',
    },
];


export const columnGroups = [
    {
        name: 'Metadata',
        ids: ['plate_design_id', 'well_id', 'electroporation_date'],
    },{
        name: 'Target',
        ids: ['target_name', 'target_family', 'target_terminus'],
    },{
        name: 'Protospacer',
        ids: ['protospacer_name', 'protospacer_notes', 'protospacer_sequence'],
    },{
        name: 'Template',
        ids: ['tempate_name', 'template_notes', 'template_sequence'],
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
        name: 'plateDesign',
        column: '',
        
    },
];

