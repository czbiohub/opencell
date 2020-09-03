import React, {Component} from 'react';
import {cellLineMetadataDefinitions} from './metadataDefinitions.js';
import { MetadataItem } from './common.jsx';



export default function CellLineMetadata (props) {

    // metadata items to display in the header
    const layout = [
        {
            id: 'target_family',
            width: 49,
        },{
            id: 'uniprot_id',
            width: 30,
        },{
            id: 'target_terminus',
            width: 24,
        },{
            id: 'hdr_all',
            width: 24,
        },{
            id: 'hdr_modified',
            width: 24,
        },{
            id: 'facs_grade',
            width: 24,
        },{
            id: 'plate_id',
            width: 24,
        },{
            id: 'well_id',
            width: 24,
        },{
            id: 'sort_count',
            width: 24,
        }
    ];

    const items = layout.map(item => {
        const def = cellLineMetadataDefinitions.filter(def => def.id===item.id)[0];
        return (
            <div 
                key={def.id} 
                className='pr2 pt2 pb2 clm-item overflow-hidden' 
                style={{flex: `1 1 ${item.width}%`}}
            >
                <MetadataItem
                    scale={4}
                    value={def.accessor(props.cellLine)}
                    label={def.Header}
                    units={def.units}
                />
            </div>
        );
    });

    return (

        <div className="flex-wrap items-center pt3 pb3 clm-container">

            {/* protein name */}
            <div className="w-100 blue clm-target-name">
                {props.cellLine.metadata?.target_name}
            </div>

            {/* protein descriptoin */}
            <div className="w-100 pb3 clm-protein-description overflow-hidden">
                {props.cellLine.uniprot_metadata?.protein_name}
            </div>

            {/* target metadata items */}
            {items}
        </div>
    );
}
