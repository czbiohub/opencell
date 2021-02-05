
import * as d3 from 'd3';
import React, { Component } from 'react';
import {Checkbox, Button} from '@blueprintjs/core';

import 'tachyons';
import "@blueprintjs/core/lib/css/blueprint.css";

import * as utils from '../common/utils.js';
import settings from '../common/settings.js';
import '../common/common.css';
import './Profile.css';


/// human-readable category labels
// (the categories themselves are lower_camel_case versions of these labels)
const localizationLabels = [
    'Nucleoplasm', 'Nuclear membrane', 'Nuclear punctae', 'Chromatin',
    'Nucleolus', 'Nucleolus-GC', 'Nucleolus-FC/DFC', 'Nucleolar ring',
    'Nucleus-cytoplasm variation', 'Membrane', 'Cytoplasmic', 'Cytoskeleton', 
    'ER', 'Golgi', 'Peri-golgi', 'Mitochondria', 'Centrosome', 'Vesicles', 'Lysosome',
    'Big aggregates', 'Small aggregates', 'Diffuse', 'Textured',
    'Cell contact', 'Cilia', 'Focal adhesions',
];

const qcLabels = [
    'Publication ready', 'Do not publish', 'Heterogeneous GFP', 'Salvageable re-sort', 'Re-image',
    'No GFP', 'Low GFP', 'Low HDR',
    'Over-exposed', 'Disk artifact', 'Confluency off',
    'Cross-contamination', 'Re-sort',
    'Interesting', 'Pretty', 'Mitotic cells'
];


function CheckboxGroup (props) {

    const checkboxRows = props.labels.map(label => {
        const category = label.toLowerCase().replace(/(-| |\\|\/)/g, '_');
        let labels = [category];
        let subcategories = [category];

        if (props.includeGrades) {
            const grades = [1, 2, 3];
            labels = [...labels, ...grades];
            subcategories = [...subcategories, ...grades.map(grade => `${category}_${grade}`)];
        }

        const checkboxes = labels.map((label, ind) => {
            const subcategory = subcategories[ind];
            // hack to right-justify the grade categories
            const style = ind===1 ? {marginLeft: 'auto'} : {};
            return (
                <Checkbox
                    className='pr3'
                    style={style}
                    label={label}
                    key={subcategory}
                    name={subcategory} 
                    checked={props.categories.includes(subcategory)}
                    onChange={props.onChange}
                />
            );
        });
        return (
            <div className='flex flex-row bb b--dashed b--black-30 pt2'>{checkboxes}</div>
        );
    });

    return (
        <div>
            <div className="pb2 f4">{props.title}</div>
            {checkboxRows}
        </div>
    );
}


export default class TargetAnnotator extends Component {

    constructor (props) {
        super(props);
        this.state = {
            loaded: false,
            comment: '',
            categories: [],
            submissionStatus: '',
        };

        this.onCheckboxChange.bind(this);
        this.onTextAreaChange.bind(this);
        this.onSubmit.bind(this);
    }


    onCheckboxChange (event) {
        const category = event.target.name;
        let categories = this.state.categories;
        if (categories.includes(category)) {
            categories = categories.filter(value => value !== category);
        } else {
            categories.push(category);
        }
        this.setState({categories});
    }


    onTextAreaChange (event) {
        this.setState({comment: event.target.value});
    }


    onSubmit () {
        const data = {
            comment: this.state.comment,
            categories: this.state.categories,
            client_metadata: {
                last_modified: (new Date()).toString(),
                displayed_fov_ids: [...new Set(this.props.fovIds)],
            }
        };

        utils.putData(`${settings.apiUrl}/lines/${this.props.cellLineId}/annotation`, data)
            .then(response => {
                console.log(response);
                if (!response.ok) throw new Error('Error submitting annotation');
                this.setState({submissionStatus: 'success'});
            })
            .catch(error => this.setState({submissionStatus: 'danger'}));
    }


    fetchData () {
        fetch(`${settings.apiUrl}/lines/${this.props.cellLineId}/annotation`)
            .then(response => {
                if (!response.ok) {
                    throw new Error(`Error getting annotation for cell line ${this.props.cellLineId}`);
                }
                return response.json();
            })
            .then(data => {
                this.setState({
                    categories: data.categories, 
                    comment: data.comment, 
                    submissionStatus: ''
                });
            })
            .catch(error => {
                this.setState({
                    categories: [], 
                    comment: '', 
                    submissionStatus: ''
                });
            });
    }


    componentDidMount () {
        if (this.props.cellLineId) this.fetchData();
    }


    componentDidUpdate (prevProps) {
        // load the data if the cellLineId has changed
        if (this.props.cellLineId!==prevProps.cellLineId) {
            this.fetchData();
        }
    }


    render () {
        return (
            <form>
                <div className='flex flex-wrap w-100 pt3'>
                    <div className='w-70'>
                        <CheckboxGroup
                            title='Localization flags'
                            labels={localizationLabels}
                            categories={this.state.categories}
                            onChange={event => this.onCheckboxChange(event)}
                            includeGrades={true}
                        />
                    </div>
                    <div className='w-30 pl3'>
                        <CheckboxGroup
                            title='QC flags'
                            labels={qcLabels}
                            categories={this.state.categories}
                            onChange={event => this.onCheckboxChange(event)}
                            includeGrades={false}
                        />
                    </div>
                </div>

                <div className='w-100 pt3'>
                    <div className="pb2 f4">{"Comments"}</div>
                    <textarea
                        style={{width: '100%', height: 100}}
                        onChange={event => this.onTextAreaChange(event)}
                        value={this.state.comment}
                    />
                </div>

                <Button
                    text={'Submit'}
                    className={'bp3-button'}
                    onClick={event => this.onSubmit()}
                    intent={this.state.submissionStatus || 'none'}
                    disabled={this.props.readOnly}
                />
            </form>
        );

    }

}
