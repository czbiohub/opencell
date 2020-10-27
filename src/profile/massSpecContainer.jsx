import * as d3 from 'd3';
import React, { useState, useEffect, useContext } from 'react';
import classNames from 'classnames';

import MassSpecScatterPlotContainer from './massSpecScatterPlotContainer.jsx';
import MassSpecNetworkContainer from './massSpecNetworkContainer.jsx';
import MassSpecTableContainer from './massSpecTableContainer.jsx';

import { SectionHeader } from './common.jsx';
import settings from '../common/settings.js';
import popoverContents from '../common/popoverContents.jsx';

export default function MassSpecContainer (props) {

    const [mode, useMode] = useState('network');

    // logic to determine the API url for the cytoscape network elements,
    // so that the interactor network is shown on the target page for targets without pulldowns
    const endpoint = props.pulldownId ? 'pulldowns' : 'interactors';
    const id = props.pulldownId ? props.pulldownId : props.ensgId;
    const url = `${settings.apiUrl}/${endpoint}/${id}/network`;

    let content;
    if (mode==='network') {
        content = (
            <MassSpecNetworkContainer
                width={700}
                height={600}
                url={url}
                pulldownId={props.pulldownId}
                handleGeneNameSearch={props.handleGeneNameSearch}
            />
        );
    }
    if (mode==='scatterplot') {
        content = (
            <MassSpecScatterPlotContainer
                pulldownId={props.pulldownId}
                handleGeneNameSearch={props.handleGeneNameSearch}
            />
        );
    }
    if (mode==='table') {
        content = (
            <MassSpecTableContainer
                url={url}
                handleGeneNameSearch={props.handleGeneNameSearch}
            />
        );
    }

    const headerClassNames = ['f4', 'mr5', 'section-header',];

    return (
        <div>
        <div className="flex bb b--black-10">
            <div 
                className={classNames(headerClassNames, {'section-header-active': mode==='network'})}
                onClick={() => useMode('network')}
                key='network'
            >
                Interaction Network
            </div>
            <div 
                className={classNames(headerClassNames, {'section-header-active': mode==='scatterplot'})}
                onClick={() => useMode('scatterplot')}
                key='scatterplot'
            >
                Scatterplots
            </div>
            <div 
                className={classNames(headerClassNames, {'section-header-active': mode==='table'})}
                onClick={() => useMode('table')}
                key='table'
            >
                Table of interactors
            </div>
        </div>
        {content}
    </div>
    );
}