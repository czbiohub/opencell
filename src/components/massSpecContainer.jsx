import * as d3 from 'd3';
import React, { useState, useEffect, useContext } from 'react';
import classNames from 'classnames';

import MassSpecScatterPlotContainer from './massSpecScatterPlot/massSpecScatterPlotContainer.jsx';
import MassSpecNetworkContainer from './massSpecNetwork/massSpecNetworkContainer.jsx';
import MassSpecTableContainer from './massSpecTableContainer.jsx';

import { SectionHeader, Tab, Tabs } from './common.jsx';
import * as popoverContents from './popoverContents.jsx';


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
            geneName={props.geneName}
            handleGeneNameSearch={props.handleGeneNameSearch}
        />
    );

    if (props.layout==='tabs') return (
        <Tabs activeTabId='network'>
            <Tab 
                id='network' 
                title='Interaction network'
                component={network}
                popoverContent={popoverContents.interactionNetworkHeader}
            />
            <Tab 
                id='scatterplot' 
                title='Scatterplots' 
                component={scatterplot}
                popoverContent={popoverContents.scatterplotsHeader}
            />
            <Tab 
                id='table' 
                title='Interactors table' 
                component={table}
                popoverContent={popoverContents.interactionTableHeader}
            />
        </Tabs>
    );

    if (props.layout==='columns') return (
        <div className='flex'>
            <div className='w-50 pr3'>
                <SectionHeader 
                    title='Interaction network' 
                    popoverContent={popoverContents.interactionNetworkHeader}
                />
                {network}
            </div>
            <div className='w-50 pr2'>
                <SectionHeader 
                    title='Table of interactors'
                    popoverContent={popoverContents.interactionTableHeader}
                />
                {table}
            </div>
        </div>
    );
}