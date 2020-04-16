import * as d3 from 'd3';
import ReactDOM from 'react-dom';
import React, { Component } from 'react';
import FOVOverview from './FOVOverview.jsx';


const urlParams = new URLSearchParams(window.location.search);

ReactDOM.render(
	<FOVOverview plateId={urlParams.get('plate')}/>, 
	document.getElementById('root')
);

