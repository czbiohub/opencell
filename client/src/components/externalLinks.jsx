import React, { useState, useEffect, useContext } from 'react';
import {cellLineMetadataDefinitions} from '../settings/metadataDefinitions.js';


export default function ExternalLinks (props) {
    // note that external links are the same for both targets and interactors

    const linkLayouts = [
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

    const linkItems = linkLayouts.map(item => {
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
        <div className="pt2 pb3 flex items-center">
            <div className='pr2'>Links: </div>
            {linkItems}
        </div>
    );
}

