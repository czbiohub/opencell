import React, { useState, useEffect, useContext } from 'react';
import './sequencingPlot.css';


export default function SequencingPlot (props) {
    const data = {
        HDR: props.data.hdr,
        WT: props.data.unmodified,
        Other: props.data.nhej + props.data.mixed,
    };

    if (props.data.hdr===undefined) {
        return <div className='pt2 pb3 f5 gray'>No sequencing data available</div>
    }

    const styles = {
        'HDR': {backgroundColor: '#86BCE3'},
        'WT': {backgroundColor: '#ccc'},
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
        const width = Math.round(100 * data[category]);
        if (width === 0) return null;
        return <span
            className='sequencing-bar'
            key={category}
            style={{flexBasis: `${width}%`, ...styles[category]}}>
        </span>
    });

    const legend = Object.keys(data).map(category => {
        return <div key={category} className='pr3 flex'>
            <div className='sequencing-legend-dot' style={styles[category]}/>
            <div className='f7 pl1'>
                <span className='b pr1'>{`${category}`}</span>
                <span className='black-50'>{`${Math.round(100*data[category])}%`}</span>
            </div>
        </div>
    });

    return (
        <div className='w-100 pt2 pb3'>
            <span className='w-100 flex flex-row sequencing-bar-container'>{bars}</span>
            <div className='w-100 flex flex-row pt2'>{legend}</div>
        </div>
    );
}
