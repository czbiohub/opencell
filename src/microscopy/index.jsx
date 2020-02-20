import ReactDOM from 'react-dom';
import React, { Component } from 'react';
import {Checkbox, Button} from '@blueprintjs/core';

import 'tachyons';
import "@blueprintjs/core/lib/css/blueprint.css";

import settings from '../common/settings.js';
import '../common/common.css';
import '../profile/Profile.css';


class FOVCuration extends Component {

    constructor (props) {
        super(props);
        this.state = {};
    }

    render () {

    }

}


ReactDOM.render(
	<FOVCuration/>, 
	document.getElementById('root')
);

