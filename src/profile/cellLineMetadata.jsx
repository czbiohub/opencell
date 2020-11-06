import React, { useState, useEffect, useContext } from 'react';
import {cellLineMetadataDefinitions} from './metadataDefinitions.js';
import { MetadataItem } from './common.jsx';
import settings from '../common/settings.js';
import * as annotationDefs from '../common/annotationDefs.js';


export function CellLineMetadata (props) {
    const modeContext = useContext(settings.ModeContext);

    // metadata items to display in the header for opencell targets
    let targetItemLayouts = [
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

    // TODO: metadata items for interactors (none, for now)
    const interactorItemLayouts = [];
    const itemLayouts = props.isInteractor ? interactorItemLayouts : targetItemLayouts;
    const metadataItems = itemLayouts.map(item => {
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

    const opencellStatus = props.data.metadata?.cell_line_id ? 'tagged' : 'untagged';
    let tagType = props.data.metadata?.target_terminus;
    tagType = tagType ? `(${tagType}-terminus)` : '';

    return (
        <div className="flex-wrap items-center pt3 pb3 clm-container">

            {/* protein name */}
            <div className="w-100 blue clm-target-name">
                {props.data.metadata?.target_name}
            </div>

            {/* protein descriptoin */}
            <div className="w-100 clm-protein-description pb2">
                {props.data.uniprot_metadata?.protein_name}
            </div>

            <div className="w-100">
                <div className='clm-opencell-status'>{`OpenCell status: ${opencellStatus} ${tagType}`}</div>
            </div>

            {modeContext==='private' ? metadataItems : null}
        </div>
    );
}


export function ExternalLinks (props) {
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
        <div className="pt2 pb3">
            {linkItems}
        </div>
    );
}


function LocalizationAnnotation (props) {
    const label = annotationDefs.categoryNameToLabel(props.name);
    
    const gradeRectangles = []
    for (let grade = 1; grade <= parseInt(props.grade); grade++) {
        gradeRectangles.push(
            <div className='flex items-center localization-grade-container'>
                <div className={`localization-grade localization-grade-${grade}`}></div>
            </div>
        );
    }
    return (
        <div className='w-90 flex'>
            <div className='w-50 flex items-center'>{gradeRectangles}</div>
            <div className='w-50 localization-row'>{label}</div>
        </div>
    );
}


export function LocalizationAnnotations (props) {

    // the public localization-related cell line annotation categories
    const allPublicCategories = annotationDefs.publicLocalizationCategories.map(d => d.name);
    
    // the public graded categories associated with the current cell line
    let gradedCategories = props.data.annotation.categories?.map(categoryName => {
        const grade = categoryName.slice(-1);
        const name = categoryName.replace(/_[1,2,3]$/, '');
        if (name!==categoryName && allPublicCategories.includes(name)) return {name, grade};
    });
    gradedCategories = gradedCategories || [];

    // drop nulls and sort by grade
    gradedCategories = gradedCategories.filter(d => !!d)
    gradedCategories.sort((a, b) => a.grade > b.grade ? -1 : 1);

    return (
        <div className="pt2 pb3">
            <div className='w-90 flex b pb1'>
            </div>
            {gradedCategories.map(category => {
                return <LocalizationAnnotation name={category.name} grade={category.grade}/>
            })}
        </div>
    );
}
