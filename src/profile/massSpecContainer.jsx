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

    // idType is set to 'ensg' when the pulldownId is undefined
    // so that the interactor network is shown on both the interactor page
    // and on the target page for targets without pulldowns
    const [id, idType] = props.pulldownId ? [props.pulldownId, 'pulldown'] : [props.ensgId, 'ensg'];

    const network = (
        <MassSpecNetworkContainer
            id={id}
            idType={idType}
            handleGeneNameSearch={props.handleGeneNameSearch}
        />
    );

    // note that the scatterplot is only defined for pulldowns, not interactors,
    // and makes its own API request to get the pulldown's hits
    const scatterplot = (
        <MassSpecScatterPlotContainer
            pulldownId={props.pulldownId}
            handleGeneNameSearch={props.handleGeneNameSearch}
        />
    );

    const table = (
        <MassSpecTableContainer
            id={id}
            idType={idType}
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
            <div className='w-50 pr3'>
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