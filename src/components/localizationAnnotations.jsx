import React, { useState, useEffect, useContext } from 'react';
import chroma from 'chroma-js';

import * as annotationDefs from '../settings/annotationDefs.js';
import './localizationAnnotations.css';


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

