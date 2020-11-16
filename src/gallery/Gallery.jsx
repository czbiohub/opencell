
import * as d3 from 'd3';
import React, { Component } from 'react';
import classNames from 'classnames';
import { Button, Radio, RadioGroup, MenuItem, Menu } from "@blueprintjs/core";

import 'tachyons';
import 'react-table/react-table.css';
import "@blueprintjs/core/lib/css/blueprint.css";

import ViewerContainer from '../profile/viewerContainer.jsx';
import MultiSelectContainer from './multiSelectContainer.jsx';
import ButtonGroup from '../profile/buttonGroup.jsx';

import settings from '../common/settings.js';
import * as utils from '../common/utils.js';
import * as annotationDefs from '../common/annotationDefs.js';
import {cellLineMetadataDefinitions} from '../profile/metadataDefinitions.js';

import '../common/common.css';
import '../profile/Profile.css';
import './gallery.css';


function appendCategoryLabels (categories) {
    return categories.map(category => {
        category.label = annotationDefs.categoryNameToLabel(category.name);
        return category;
    });
}

function Lightbox (props) {
    return (
        <div 
            className='lightbox-container' 
            onClick={event => {
                if (event.target.className==='lightbox-container') props.hideLightbox();
            }}>
            <div 
                className='pa3 br3 ba b--black-70' 
                style={{margin: 'auto', width: '650px', backgroundColor: 'white'}}>
                <div className='f3'>{`FOVs for ${props.targetName}`}</div>
                <ViewerContainer
                    cellLineId={props.cellLineId}
                    fovs={props.fovs}
                    rois={props.rois}
                    fovId={props.fovId}
                    roiId={props.roiId}
                    isLowGfp={false}
                    changeRoi={props.changeRoi}
                />
            </div>
        </div>
    );
}


function Thumbnail (props) {
    const proteinNameDef = cellLineMetadataDefinitions.filter(def => def.id === 'protein_name')[0];
    const metadata = props.cellLine.metadata;
    return (
        <div className='gallery-thumbnail-container'>
            <img 
                className='thumbnail'
                onClick={() => props.onThumbnailImageClick(metadata)}
                src={`data:image/jpg;base64,${props.cellLine.best_fov?.thumbnails?.data}`}
            />
            <div className='gallery-thumbnail-caption'>
                <span 
                    className='f4 gallery-thumbnail-caption-link'
                    onClick={() => props.onThumbnailCaptionClick(metadata)}>
                    {`${metadata.target_name}`}
                </span>
                <br/>
                <span className='f6'>{`${proteinNameDef.accessor(props.cellLine)}`}</span>
            </div>
        </div>
    );
}


class Gallery extends Component {
    static contextType = settings.ModeContext;

    constructor (props) {
        super(props);

        this.allQcCategories = appendCategoryLabels(annotationDefs.qcCategories);
        this.allTargetFamilies = appendCategoryLabels(annotationDefs.targetFamilies);
        
        this.allLocalizationCategories = annotationDefs.publicLocalizationCategories;
        if (this.context==='private') {
            this.allLocalizationCategories = [
                ...annotationDefs.publicLocalizationCategories,
                ...annotationDefs.privateLocalizationCategories,
            ];
        }
        this.allLocalizationCategories = appendCategoryLabels(this.allLocalizationCategories);
    
        this.state = {
            loaded: false,

            // set the default selected QC category to publication_ready 
            // (note that in 'public' mode, the QC category selection component is hidden, 
            // so only the publication-ready targets will be displayed)
            selectedQcCategories: this.allQcCategories.filter(item => item.name === 'publication_ready'),

            // set the default localization category to something pretty
            selectedLocalizationCategories: this.allLocalizationCategories.filter(item => item.name === 'cytoskeleton'),

            // no families selected by default (and these are hidden in public mode)
            selectedTargetFamilies: [],

            // the list of selected cell lines
            selectedCellLines: [],

            // whether to select lines that have any or all of the selected localization categories
            selectionMode: 'All',

            fovs: [],
            rois: [],
            roiId: undefined,
            fovId: undefined,
            cellLineId: undefined,
            targetName: undefined,

            pageNum: 0,
            pageSize: 18,
            showLightbox: false,
        };

        this.cellLines = [];
        this.loadData = this.loadData.bind(this);
    }

    loadMetadata () {
        // load the cell line metadata for all cell lines
        this.setState({loaded: false});
        d3.json(`${settings.apiUrl}/lines`).then(data => {
            this.cellLines = data;
            this.loadData();
        });
    }

    loadData () {
        // load the thumbnails for the selected cell lines

        // simplify the cell line metadata and strip the grades from the annotation categories
        let lines = this.cellLines.map(line => {
            return {
                id: line.metadata.cell_line_id, 
                family: line.metadata.target_family,
                categories: line.annotation.categories?.map(name => name.replace(/_[1,2,3]$/, '')) || [],
            };
        });

        // select the lines with *all* of the selected QC categories 
        for (let category of this.state.selectedQcCategories) {
            lines = lines.filter(line => line.categories.includes(category.name));
        }

        // select the lines that have either any or all of the selected localization categories
        let selectedLines;
        if (this.state.selectionMode==='All') {
            selectedLines = [...lines];
            for (let category of this.state.selectedLocalizationCategories) {
                selectedLines = selectedLines.filter(line => line.categories.includes(category.name));
            }
        }
        if (this.state.selectionMode==='Any') {
            selectedLines = [];
            for(let category of this.state.selectedLocalizationCategories) {
                selectedLines.push(...lines.filter(line => line.categories.includes(category.name)));
            }
        }

        // limit to the first n lines to avoid slow loading times
        const maxNum = 999;
        const ids = selectedLines.map(line => line.id).slice(0, maxNum);

        // load the thumbnails for the selected cell lines
        this.setState({loaded: false});
        if (!ids.length) {
            this.setState({selectedCellLines: [], loaded: true});
            return;
        }
        const url = `${settings.apiUrl}/lines?fields=best-fov&ids=${ids.join(',')}`;
        d3.json(url).then(data => {
            // sort lines alphabetically by target_name
            const selectedCellLines = data.sort((a, b) => {
                return a.metadata.target_name > b.metadata.target_name ? 1 : -1;
            });
            this.setState({selectedCellLines, loaded: true});
        });
    }

    componentDidMount () {
        this.loadMetadata();
    }

    componentDidUpdate (prevProps, prevState) {
        if (this.state.reload && !prevState.reload) {
            this.setState({reload: false});
            this.loadData();
        }
        if (prevState.cellLineId!==this.state.cellLineId) {
            utils.getAnnotatedFovMetadata(
                this.state.cellLineId, fovState => this.setState({...fovState})
            );    
        }
    }

    updateCategories(categoryType, categories) {
        this.setState({[categoryType]: categories});
    }

    render () {

        const thumbnails = this.state.selectedCellLines.map(line => {
            return (
                <Thumbnail 
                    cellLine={line} 
                    onThumbnailImageClick={metadata => {
                        this.setState({
                            cellLineId: metadata.cell_line_id, 
                            targetName: metadata.target_name,
                            showLightbox: true,
                        });
                    }}
                    onThumbnailCaptionClick={metadata => {
                        window.open(`http://${window.location.host}/target/${metadata.cell_line_id}`);
                    }}
                />
            );
        });

        let overlay = null;
        if (!this.state.loaded) overlay = <div className='f2 tc loading-overlay'>Loading...</div>;
        if (this.state.loaded && !this.state.selectedCellLines.length) {
            overlay = <div className='f2 tc'>No targets found</div>;
        }

        const privateMultiSelectContainers = [
            <div className="pr3 w-20">
                <div className="f4">{"QC annotations"}</div>
                <MultiSelectContainer
                    items={this.allQcCategories}
                    selectedItems={this.state.selectedQcCategories}
                    updateSelectedItems={items => this.updateCategories('selectedQcCategories', items)}
                />
            </div>,
            <div className="pr3 w-20">
                <div className="f4">{"Target families"}</div>
                <MultiSelectContainer
                    items={this.allTargetFamilies}
                    selectedItems={this.state.selectedTargetFamilies}
                    updateSelectedItems={items => this.updateCategories('selectedTargetFamilies', items)}
                />
            </div>
        ];

        return (
            <div>
                <div className="pa4 w-100">
                    <div className="flex" style={{alignItems: 'flex-start'}}>
                        <div className="pr3 w-33">
                            <div className="f4">{"Select localization annotations"}</div>
                            <MultiSelectContainer
                                items={this.allLocalizationCategories}
                                selectedItems={this.state.selectedLocalizationCategories}
                                updateSelectedItems={
                                    items => this.updateCategories('selectedLocalizationCategories', items)
                                }
                            />
                        </div>
                        {this.context==='private' ? privateMultiSelectContainers : null}
                        <ButtonGroup
                            className='pr3'
                            label='Selection mode'
                            values={['Any', 'All']}
                            activeValue={this.state.selectionMode}
                            onClick={value => this.setState({selectionMode: value})}
                        />
                        <div className='pt3'>
                            <div 
                                className='f4 pl2 pr2 simple-button' 
                                onClick={() => {this.setState({reload: true})}}
                            >
                            {'Load'}
                            </div>
                        </div>
                    </div>

                    <div className='pa3 gallery-thumbnail-grid-container'>{thumbnails}</div>

                </div>

                {overlay}

                {this.state.showLightbox ? (
                    <Lightbox
                        hideLightbox={() => this.setState({showLightbox: false})}
                        changeRoi={(roiId, fovId) => this.setState({roiId, fovId})}
                        {...this.state}
                    />
                ) : (
                    null
                )}
            </div>

        );
    }
}

export default Gallery;



