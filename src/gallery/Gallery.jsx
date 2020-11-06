
import * as d3 from 'd3';
import React, { Component } from 'react';
import classNames from 'classnames';
import { Button, Radio, RadioGroup, MenuItem, Menu } from "@blueprintjs/core";

import 'tachyons';
import 'react-table/react-table.css';
import "@blueprintjs/core/lib/css/blueprint.css";

import ViewerContainer from '../profile/viewerContainer.jsx';
import MultiSelectContainer from './multiSelectContainer.jsx';
import settings from '../common/settings.js';
import * as utils from '../common/utils.js';
import * as annotationDefs from '../common/annotationDefs.js';
import {cellLineMetadataDefinitions} from '../profile/metadataDefinitions.js';

import '../common/common.css';
import '../profile/Profile.css';
import './gallery.css';


function generateCategoryLabels (categories) {
    categories.forEach(category => {
        category.label = annotationDefs.categoryNameToLabel(category.name)
    });
    return categories;
}

const qcCategories = generateCategoryLabels(annotationDefs.qcCategories);
const localizationCategories = generateCategoryLabels(annotationDefs.publicLocalizationCategories);
const targetFamilies = generateCategoryLabels(annotationDefs.targetFamilies);

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
        this.state = {
            loaded: false,
            qcCategories: qcCategories.filter(item => item.name === 'publication_ready'),
            localizationCategories: localizationCategories.filter(item => item.name === 'nucleolus'),
            targetFamilies: [],
            selectedCellLines: [],

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
        // when the selected categories or families are changed

        this.setState({loaded: false});

        let lines = this.cellLines.map(line => {
            return {
                id: line.metadata.cell_line_id, 
                categories: line.annotation.categories || [],
                family: line.metadata.target_family,
            };
        });

        // filter for lines that have all of the selected categories
        // TODO: add button to toggle between 'all' and 'any'
        for (let category of [...this.state.localizationCategories, ...this.state.qcCategories]) {
            lines = lines.filter(line => line.categories.includes(category.name));
        }

        // limit to the first n lines to avoid slow loading times
        const maxNum = 999;
        const ids = lines.map(line => line.id).slice(0, maxNum);

        if (!ids.length) {
            this.setState({selectedCellLines: [], loaded: true});
        } else {
            const url = `${settings.apiUrl}/lines?fields=best-fov&ids=${ids.join(',')}`;
            d3.json(url).then(data => {
                // sort lines alphabetically by target_name
                const selectedCellLines = data.sort((a, b) => {
                    return a.metadata.target_name > b.metadata.target_name ? 1 : -1;
                });
                this.setState({selectedCellLines, loaded: true});
            });
        }
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
            utils.getAnnotatedFovMetadata(this.state.cellLineId, fovState => this.setState({...fovState}));    
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
            <div className="pa3 w-25">
                <div className="f4">{"QC annotations"}</div>
                <MultiSelectContainer
                    items={qcCategories}
                    selectedItems={this.state.qcCategories}
                    updateSelectedItems={items => this.updateCategories('qcCategories', items)}
                />
            </div>,
            <div className="pa3 w-25">
                <div className="f4">{"Target families"}</div>
                <MultiSelectContainer
                    items={targetFamilies}
                    selectedItems={this.state.targetFamilies}
                    updateSelectedItems={items => this.updateCategories('targetFamilies', items)}
                />
            </div>
        ];

        return (
            <div>
                <div className="pa4 w-100">

                    <div className="flex" style={{alignItems: 'flex-start'}}>
                        <div className="pa3 w-33">
                            <div className="f4">{"Select localization annotations"}</div>
                            <MultiSelectContainer
                                items={localizationCategories}
                                selectedItems={this.state.localizationCategories}
                                updateSelectedItems={items => this.updateCategories('localizationCategories', items)}
                            />
                        </div>
                        {this.context==='private' ? privateMultiSelectContainers : null}
                        <div className='pt4'>
                            <div className='f4 simple-button' onClick={() => {this.setState({reload: true})}}>
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



