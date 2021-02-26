import React, { useState, useEffect, useContext } from 'react';
import chroma from 'chroma-js';

import {cellLineMetadataDefinitions} from './metadataDefinitions.js';
import { MetadataItem } from './common.jsx';
import settings from '../common/settings.js';
import * as annotationDefs from '../common/annotationDefs.js';


export function CellLineMetadataTable (props) {
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
                className='pr2 pt2 pb2 clm-item overflow-hidden' 
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
        <div className="pt2 pb3 flex items-center">
            <div className='pr2'>Links: </div>
            {linkItems}
        </div>
    );
}


export function LocalizationAnnotation (props) {
    
    const gradeRectangles = []
    for (let grade = 1; grade <= parseInt(props.grade); grade++) {
        gradeRectangles.push(
            <div key={grade} className='flex items-center localization-grade-container'>
                <div className={`localization-grade localization-grade-${grade}`}></div>
            </div>
        );
    }

    const label = annotationDefs.categoryNameToLabel(props.name);
    return (
        <div className='w-90 flex'>
            <div className='flex items-center' style={{width: '120px'}}>{gradeRectangles}</div>
            <div className='w-70 pl1 localization-row'>{label}</div>
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
                return <LocalizationAnnotation 
                    key={category.name} 
                    name={category.name} 
                    grade={category.grade}
                />
            })}
        </div>
    );
}


export function SequencingPlot (props) {

    const data = {
        HDR: props.data.hdr,
        Other: props.data.nhej + props.data.mixed,
        WT: props.data.unmodified,
    };

    if (props.data.hdr===undefined) {
        return <div className='pt2 pb3 f5 gray'>No sequencing data found</div>
    }

    const styles = {
        'HDR': {backgroundColor: '#86BCE3'},
        'WT': {backgroundColor: '#aaa'},
    };

    // cross-hatched pattern for the 'other' category
    styles['Other'] = {
        background: `
            repeating-linear-gradient(
                45deg,
                #ccc,
                #ccc 3px,
                #aaa 3px,
                #aaa 6px
            )
    `};

    const bars = Object.keys(data).map(category => {
        return <div 
            className='f6 b pl2'
            key={category} 
            style={{
                flexBasis: `${Math.round(100*data[category])}%`, 
                ...styles[category],
            }}>
        </div>
    });

    const legend = Object.keys(data).map(category => {
        return <div key={category} className='pr3 flex'>
            <div style={{
                width: '11px', 
                height: '11px', 
                borderRadius: '3px',
                ...styles[category],
            }}/>
            <div className='f7 pl1'>{`${Math.round(100*data[category])}% ${category}`}</div>
        </div>
    });

    return (
        <div className='w-100 pt2 pb3'>
            <div className='f7 b flex flex-row justify-between'>
            </div>
            <div className='w-100 flex flex-row' style={{height: '15px'}}>
                {bars}
            </div>
            <div className='w-100 flex flex-row pt2'>
                {legend}
            </div>

        </div>
    );
}
