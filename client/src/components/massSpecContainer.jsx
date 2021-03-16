import * as d3 from 'd3';
import React, { useState, useEffect, useContext } from 'react';
import classNames from 'classnames';
import { H5, Icon, Popover } from "@blueprintjs/core";

import MassSpecScatterPlotContainer from './massSpecScatterPlot/massSpecScatterPlotContainer.jsx';
import MassSpecNetworkContainer from './massSpecNetwork/massSpecNetworkContainer.jsx';
import MassSpecTableContainer from './massSpecTableContainer.jsx';
import SectionHeader from './sectionHeader.jsx';
import {SimpleButton} from './buttonGroup.jsx';

import * as popoverContents from './popoverContents.jsx';

import './massSpecContainer.scss'

function Tab (props) {
    return props.component;
}

function Tabs (props) {

    const [activeTabId, setActiveTabId] = useState(props.activeTabId);

    const tabs = props.children.map(child => {

        // const className = classNames(
        //     'f4', 'mr4', 'pt1', 'pl2', 'pr2', 'flex', 'items-center', 'tab-header', 
        //     {'tab-header-active': child.props.id===activeTabId}
        // );

        const popover = child.props.popoverContent ? (
            <div className='pl2'>
                <Popover>
                    <Icon icon='info-sign' iconSize={10} color="#bbb"/>
                    {child.props.popoverContent}
                </Popover>
            </div>
        ) : null;

        return (
            <SimpleButton
                active={child.props.id===activeTabId}
                onClick={() => setActiveTabId(child.props.id)}
                text={child.props.title}
                key={child.props.id}
            >
                {popover}
            </SimpleButton>

            // <div key={child.props.id} className={className} >
            //     <div className='pr2' onClick={() => setActiveTabId(child.props.id)}>
            //         {child.props.title}
            //     </div>
            //     {popover}
            // </div>
        );
    });

    const ActiveTab = props.children.filter(child => child.props.id===activeTabId)[0];
    return (
        <>
            <div className="flex">{tabs}</div>
            {ActiveTab}
        </>
    );
}


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

    let content;
    if (props.layout==='tabs') content = (
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
                title='Table of interactors' 
                component={table}
                popoverContent={popoverContents.interactionTableHeader}
            />
        </Tabs>
    );

    if (props.layout==='columns') content = (
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

    return (
        <div className='pt1'>{content}</div>
    );
}