
import * as d3 from 'd3';
import React, { Component } from 'react';
import classNames from 'classnames';
import { Button, Radio, RadioGroup, MenuItem, Menu } from "@blueprintjs/core";

import Navbar from '../common/navbar.jsx';
import Header from '../profile/header.jsx';

import 'tachyons';
import 'react-table/react-table.css';
import "@blueprintjs/core/lib/css/blueprint.css";

import ViewerContainer from '../profile/viewerContainer.jsx';
import MultiSelectContainer from './multiSelectContainer.jsx';
import settings from '../common/settings.js';
import * as utils from '../common/utils.js';
import {cellLineMetadataDefinitions} from '../profile/metadataDefinitions.js';

import '../common/common.css';
import '../profile/Profile.css';
import './gallery.css';


const localizationCategories = [
    {'name': 'cytoplasmic', 'num': 630},
    {'name': 'nuclear', 'num': 594},
    {'name': 'vesicles', 'num': 350},
    {'name': 'membrane', 'num': 192},
    {'name': 'chromatin', 'num': 149},
    {'name': 'textured', 'num': 127},
    {'name': 'er', 'num': 125},
    {'name': 'small_aggregates', 'num': 112},
    {'name': 'nuclear_punctae', 'num': 110},
    {'name': 'nucleus_cytoplasm_variation', 'num': 92},
    {'name': 'golgi', 'num': 90},
    {'name': 'diffuse', 'num': 82},
    {'name': 'nucleolus_gc', 'num': 73},
    {'name': 'cytoskeleton', 'num': 52},
    {'name': 'cell_contact', 'num': 50},
    {'name': 'centrosome', 'num': 45},
    {'name': 'nuclear_membrane', 'num': 44},
    {'name': 'nucleolus_fc_dfc', 'num': 32},
    {'name': 'big_aggregates', 'num': 30},
    {'name': 'nucleolus', 'num': 30},
    {'name': 'nucleolar_ring', 'num': 17},
    {'name': 'mitochondria', 'num': 14},
    {'name': 'mitotic_cells', 'num': 7},
    {'name': 'cilia', 'num': 4},
];


const qcCategories = [
    {'name': 'publication_ready', 'num': 1235},
    {'name': 'no_gfp', 'num': 338},
    {'name': 'interesting', 'num': 288},
    {'name': 'pretty', 'num': 187},
    {'name': 'low_gfp', 'num': 179},
    {'name': 'salvageable_re_sort', 'num': 170},
    {'name': 'heterogeneous_gfp', 'num': 163},
    {'name': 'low_hdr', 'num': 137},
    {'name': 're_image', 'num': 103},
    {'name': 'disk_artifact', 'num': 43},
    {'name': 'cross_contamination', 'num': 14},
    {'name': 'rare_gfp', 'num': 6},
    {'name': 'over_exposed', 'num': 4},
];


// the 20 most frequent target families
const families = [
    {'name': 'kinase', 'num': 179},
    {'name': 'SLC', 'num': 74},
    {'name': 'chaperone', 'num': 52},
    {'name': 'endocytosis', 'num': 50},
    {'name': 'proteasome', 'num': 43},
    {'name': 'motor', 'num': 39},
    {'name': 'Diana', 'num': 39},
    {'name': 'transport', 'num': 38},
    {'name': 'BAR', 'num': 35},
    {'name': 'nuclear transport', 'num': 34},
    {'name': 'ER', 'num': 34},
    {'name': 'GEF', 'num': 33},
    {'name': 'PIP metabolism', 'num': 33},
    {'name': 'GAP', 'num': 31},
    {'name': 'positive control', 'num': 30},
    {'name': 'orphan', 'num': 29},
    {'name': 'RNA binding', 'num': 29},
    {'name': 'SNARE', 'num': 28},
    {'name': 'Peter Tuhl', 'num': 25},
    {'name': 'centrosome', 'num': 23},
];


const proteinNameDef = cellLineMetadataDefinitions.filter(def => def.id === 'protein_name')[0];


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
    const metadata = props.cellLine.metadata;
    return (
        <div className='thumbnail-container'>
            <img 
                className='thumbnail'
                onClick={() => props.onThumbnailImageClick(metadata)}
                src={`data:image/jpg;base64,${props.cellLine.best_fov?.thumbnails?.data}`}
            />
            <div className='thumbnail-caption'>
                <span 
                    className='f4 thumbnail-caption-link'
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

    constructor (props) {
        super(props);
        this.urlParams = new URLSearchParams(window.location.search);

        this.state = {
            loaded: false,
            qcCategories: qcCategories.filter(item => item.name === 'publication_ready'),
            localizationCategories: localizationCategories.filter(item => item.name === 'nucleolus'),
            families: [],
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
            utils.loadFovs(this.state.cellLineId, fovState => this.setState({...fovState}));    
        }
    }

    updateCategories(categoryType, categories) {
        this.setState({[categoryType]: categories, reload: true});
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
                        window.open(`http://opencell.czbiohub.org/profile?target=${metadata.target_name}`);
                    }}
                />
            );
        });

        return (
            <div>
                <div className="pa4 w-100">

                    <div className="flex">
                        <div className="pa3 w-30">
                            <div className="f4">{"Localization annotations"}</div>
                            <MultiSelectContainer
                                items={localizationCategories}
                                selectedItems={this.state.localizationCategories}
                                updateSelectedItems={items => this.updateCategories('localizationCategories', items)}
                            />
                        </div>
                        <div className="pa3 w-30">
                            <div className="f4">{"QC annotations"}</div>
                            <MultiSelectContainer
                                items={qcCategories}
                                selectedItems={this.state.qcCategories}
                                updateSelectedItems={items => this.updateCategories('qcCategories', items)}
                            />
                        </div>
                        <div className="pa3 w-30">
                            <div className="f4">{"Target families"}</div>
                            <MultiSelectContainer
                                items={families}
                                selectedItems={this.state.families}
                                updateSelectedItems={items => this.updateCategories('families', items)}
                            />
                        </div>

                    </div>

                    <div className='pa3 thumbnail-grid-container'>{thumbnails}</div>

                </div>
    
                {this.state.loaded ? null : <div className='loading-overlay'/>}
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



