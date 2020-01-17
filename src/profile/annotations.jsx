
import * as d3 from 'd3';
import React, { Component } from 'react';
import {Checkbox, Button} from '@blueprintjs/core';

import 'tachyons';
import "@blueprintjs/core/lib/css/blueprint.css";

import settings from '../common/settings.js';
import '../common/common.css';
import './Profile.css';


/// human-readable category labels
// (the categories themselves are lower_camel_case versions of these labels)
const localizationLabels = [
    'Nuclear', 'Nuclear membrane', 'Nuclear punctae', 'Chromatin',
    'Nucleolus', 'Nucleolus-GC', 'Nucleolus-FC/DFC', 'Nucleolar ring',
    'Membrane', 'Cytoplasmic', 'Cytoskeleton', 
    'ER', 'Golgi', 'Mitochondria', 'Centrosome', 'Vesicles',
    'Big aggregates', 'Small aggregates', 'Diffuse', 'Textured',
    'Cell contact', 'Nucleus-cytoplasm variation'
];

const qcLabels = [
    'Pretty', 'Interesting', 
    'No GFP', 'Low GFP', 'Heterogeneous GFP', 'Low HDR',
    'Re-sort', 'Over-exposed', 'Disk artifact', 'Cross-contamination',
];


async function putData(url, data) {
    const response = await fetch(url, {
        method: 'PUT',
        mode: 'cors',
        cache: 'no-cache',
        credentials: 'same-origin',
        headers: {'Content-Type': 'application/json'},
        referrerPolicy: 'no-referrer',
        body: JSON.stringify(data),
    });
    return await response;
}


class CheckboxGroup extends Component {
    constructor (props) {
        super(props);
    }

    render() {

        const checkboxes = this.props.labels.map(label => {
            const category = label.toLowerCase().replace(/(-| |\\|\/)/g, '_');
            return (
                <Checkbox
                    label={label}
                    key={category}
                    name={category} 
                    checked={this.props.categories.includes(category)}
                    onChange={this.props.onChange}
                />
            );
        });

        return (
            <div className='pb2'>
                <div className="pb2 f4">{this.props.title}</div>
                {checkboxes}
            </div>
        );

    }
}


class AnnotationsForm extends Component {

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
        // submit the annotations
        
        const data = {
            comment: this.state.comment,
            categories: this.state.categories,
            fov_ids: [...new Set(this.props.fovIds)],
            timestamp: (new Date()).toString(),
        };

        putData(`${settings.apiRoot}/annotations/${this.props.cellLineId}`, data)
            .then(response => {
                console.log(response);
                if (!response.ok) throw new Error('Error submitting annotations');
                this.setState({submissionStatus: 'success'});
            })
            .catch(error => this.setState({submissionStatus: 'danger'}));

    }


    fetchData () {
        // load the list of categories into state.categories
        // load the comment string into state.comment
        fetch(`${settings.apiRoot}/annotations/${this.props.cellLineId}`)
            .then(response => {
                if (!response.ok) {
                    throw new Error(`Error getting annotations for cell line ${this.props.cellLineId}`);
                }
                return response.json();
            })
            .then(data => {
                this.setState({categories: data.categories, comment: data.comment, submissionStatus: ''});
            })
            .catch(error => {
                this.setState({categories: [], comment: '', submissionStatus: ''});
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
                
                <div className='w-100 pt3'>
                    <div className='fl dib w-50'>
                        <CheckboxGroup
                            title='Localization flags'
                            labels={localizationLabels}
                            categories={this.state.categories}
                            onChange={event => this.onCheckboxChange(event)}
                        />
                    </div>
                    <div className='fl dib w-50'>
                        <CheckboxGroup
                            title='QC flags'
                            labels={qcLabels}
                            categories={this.state.categories}
                            onChange={event => this.onCheckboxChange(event)}
                        />
                    </div>
                </div>

                <div className='fl dib w-100'>
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
                />
            </form>
        );

    }

}

export default AnnotationsForm;