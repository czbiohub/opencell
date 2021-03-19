import React, { useState, useEffect, useContext } from 'react';
import chroma from 'chroma-js';

import { MetadataItem } from './metadata.jsx';
import settings from '../settings/settings.js';
import {cellLineMetadataDefinitions} from '../settings/metadataDefinitions.js';
import './cellLineMetadataTable.css';


export default function CellLineMetadataTable (props) {
    const modeContext = useContext(settings.ModeContext);

    // metadata items to display in the header for opencell targets
    let targetItemLayouts = [
        {
            id: 'target_terminus',
            width: 28,
            isPublic: true,
        },{
            id: 'protospacer_sequence',
            width: 70,
            isPublic: true,
        },{
            id: 'hdr_all',
            width: 24,
        },{
            id: 'other_all',
            width: 24,
        },{
            id: 'wt_all',
            width: 24,
        },{
            id: 'facs_grade',
            width: 24,
        },{
            id: 'plate_id',
            width: 33,
        },{
            id: 'well_id',
            width: 33,
        },{
            id: 'sort_count',
            width: 33,
        }
    ];

    // TODO: metadata items for interactors (none, for now)
    const interactorItemLayouts = [];

    let itemLayouts = props.isInteractor ? interactorItemLayouts : targetItemLayouts;
    if (modeContext==='public') itemLayouts = itemLayouts.filter(layout => layout.isPublic);

    const metadataItems = itemLayouts.map(item => {
        const def = cellLineMetadataDefinitions.filter(def => def.id===item.id)[0];
        return (
            <div
                key={def.id}
                className='pr2 pt1 pb1 clm-item clm-overflow-hidden'
                style={{flex: `1 1 ${item.width}%`}}
            >
                <MetadataItem
                    scale={5}
                    value={def.accessor(props.data)}
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
                {props.data.metadata?.target_name}
            </div>

            {/* protein descriptoin */}
            <div className="w-100 clm-protein-description pt2 pb2">
                {props.data.uniprot_metadata?.protein_name}
            </div>
            {metadataItems}
        </div>
    );
}
