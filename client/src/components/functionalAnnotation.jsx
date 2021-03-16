import React from 'react';
import './functionalAnnotation.css';

export default function FunctionalAnnotation (props) {
    return (
        <div className='pt2 functional-annotation-container'>
            <p>{props.content}</p>
        </div>
    );
}