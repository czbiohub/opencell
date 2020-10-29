import * as d3 from 'd3';
import React, { useState, useEffect, useContext } from 'react';
import classNames from 'classnames';

import MassSpecScatterPlotContainer from './massSpecScatterPlotContainer.jsx';
import MassSpecNetworkContainer from './massSpecNetworkContainer.jsx';
import MassSpecTableContainer from './massSpecTableContainer.jsx';

import { SectionHeader, Tab, Tabs } from './common.jsx';
import settings from '../common/settings.js';
import popoverContents from '../common/popoverContents.jsx';

export default function MassSpecContainer (props) {

    // logic to determine the API url for the cytoscape network elements,
    // so that the interactor network is shown on the target page for targets without pulldowns
    const endpoint = props.pulldownId ? 'pulldowns' : 'interactors';
    const id = props.pulldownId ? props.pulldownId : props.ensgId;
    const url = `${settings.apiUrl}/${endpoint}/${id}/network`;

    const network = (
        <MassSpecNetworkContainer
            url={url}
            pulldownId={props.pulldownId}
            handleGeneNameSearch={props.handleGeneNameSearch}
        />
    );
    const scatterplot = (
        <MassSpecScatterPlotContainer
            pulldownId={props.pulldownId}
            handleGeneNameSearch={props.handleGeneNameSearch}
        />
    );
    const table = (
        <MassSpecTableContainer
            url={url}
            handleGeneNameSearch={props.handleGeneNameSearch}
        />
    );

    if (props.layout==='tabs') return (
        <Tabs activeTabId='network'>
            <Tab id='network' title='Interaction network' component={network}/>
            <Tab id='scatterplot' title='Scatterplots' component={scatterplot}/>
            <Tab id='table' title='Table of interactors' component={table}/>
        </Tabs>
    );

    if (props.layout==='columns') return (
        <div className='flex'>
            <div className='w-50'>
                <SectionHeader title='Interaction network'/>
                {network}
            </div>
            <div className='w-50 pr2'>
                <SectionHeader title='Interacting targets'/>
                {table}
            </div>
        </div>
    );
}