import React from 'react';
import './functionalAnnotation.css';

export default function FunctionalAnnotation (props) {
    return (
        <div className='pt1 functional-annotation-container'>
            <p>{props.content}</p>
        </div>
    );
}
