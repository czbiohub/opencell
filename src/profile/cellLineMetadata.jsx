import React, { useState, useEffect, useContext } from 'react';
import {cellLineMetadataDefinitions} from './metadataDefinitions.js';
import { MetadataItem } from './common.jsx';
import settings from '../common/settings.js';


export function CellLineMetadata (props) {
    const modeContext = useContext(settings.ModeContext);

    // metadata items to display in the header for opencell targets
    let targetLayout = [
        {
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
            width: 33,
        },{
            id: 'well_id',
            width: 33,
        },{
            id: 'sort_count',
            width: 33,
        }
    ];

    // TODO: metadata items for interactors
    const interactorLayout = [];

    const layout = props.isInteractor ? interactorLayout : targetLayout;
    const metadataItems = layout.map(item => {
        const def = cellLineMetadataDefinitions.filter(def => def.id===item.id)[0];
        return (
            <div 
                key={def.id} 
                className='pr2 pt2 pb2 clm-item overflow-hidden' 
                style={{flex: `1 1 ${item.width}%`}}
            >
                <MetadataItem
                    scale={4}
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
            <div className="w-100 clm-protein-description">
                {props.data.uniprot_metadata?.protein_name}
            </div>

            {modeContext==='private' ? metadataItems : null}
        </div>
    );
}


export function ExternalLinks (props) {

    // links (the same for both targets and interactors)
    const linkLayout = [
        {
            id: 'uniprot',
            defId: 'uniprot_id',
            width: 30,
            label: 'UniProtKB',
            url: id => `https://www.uniprot.org/uniprot/${id}`,
        },{
            id: 'ensg',
            defId: 'ensg_id',
            width: 30,
            label: 'Ensembl',
            url: id => `https://uswest.ensembl.org/Homo_sapiens/Gene/Summary?g=${id}`,
        },{
            id: 'hpa',
            defId: 'ensg_id',
            width: 30,
            label: 'HPA',
            url: id => `https://www.proteinatlas.org/${id}`,
        },
    ];

    const linkItems = linkLayout.map(item => {
        const def = cellLineMetadataDefinitions.filter(def => def.id===item.defId)[0];
        const value = def.accessor(props.data);
        return (
            <div 
                key={item.id}
                className='f6 simple-button'
                onClick={() => window.open(item.url(value))}
            >
                {item.label}
            </div>
        );
    });

    return (
        <div className="pt2 pb3">
            {linkItems}
        </div>
    );
}