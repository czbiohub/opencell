import React, { Component } from 'react';


function SectionHeader (props) {
    return (
        <div className="bb b--black-10">
            <div className="f3 section-header">{props.title}</div>
        </div>
    );
}


export {
    SectionHeader
};