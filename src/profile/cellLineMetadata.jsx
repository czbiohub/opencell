import React, {Component} from 'react';
import {cellLineMetadataDefinitions} from './metadataDefinitions.js';
import { MetadataItem } from './common.jsx';



export default function CellLineMetadata (props) {

    // metadata items to display in the header
    let definitionIds = [
        'uniprot_id',
        'target_family', 
        'target_terminus', 
        'plate_id', 
        'well_id', 
        'hdr_all', 
        'hdr_modified', 
        'facs_grade',
    ];

    const definitions = cellLineMetadataDefinitions.filter(
        def => definitionIds.includes(def.id)
    );

    const items = definitions.map(def => {
        return (
            <MetadataItem
                key={def.id}
                scale={4}
                className="pr2 clm-item"
                value={def.accessor(props.cellLine)}
                label={def.Header}
                units={def.units}
            />
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
