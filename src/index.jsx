import React from 'react';
import ReactDOM from 'react-dom';

import {
	BrowserRouter,
	Switch,
	Route
  } from "react-router-dom";

import { useHistory } from "react-router-dom";

import 'tachyons';
import './common/common.css';

import Navbar from './common/navbar.jsx';
import Dashboard from './dashboard/Dashboard';
import Profile from './profile/Profile.jsx';
import Gallery from './gallery/Gallery.jsx';
import FOVOverview from './microscopy/FOVOverview.jsx';

function App() {
	return (
		<div>
			<Navbar/>
			<Switch>
				<Route path="/" exact={true}>
					<div>This is the homepage</div>
				</Route>

				<Route path="/dashboard" component={Dashboard}/>

				<Route 
					path={["/profile/:cellLineId", "/profile"]} 
					component={Profile}
				/>

				<Route 
					path={["/fovs/:cellLineId", "/fovs"]}
					render={props => (<Profile {...props} showFovAnnotator/>)}
				/>

				<Route 
					path={["/annotations/:cellLineId", "/annotations"]}
					render={props => (<Profile {...props} showTargetAnnotator/>)}
				/>

				<Route path="/gallery" component={Gallery}/>

				{/* TODO: fix this - FOVOverview needs a plateId prop */}
				<Route path="/microscopy" component={FOVOverview}/>,

				<Route>
					<div>Page not found</div>
				</Route>
			</Switch>
		</div>
	)
}

ReactDOM.render(
	<BrowserRouter><App/></BrowserRouter>, 
	document.getElementById('root')
);

