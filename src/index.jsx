import * as d3 from 'd3';
import React, { useState, useEffect, useLayoutEffect } from 'react';
import ReactDOM from 'react-dom';

import {
    BrowserRouter,
    Switch,
    Route,
    Redirect,
    useHistory, 
    useLocation, 
    useParams, 
    useRouteMatch
 } from "react-router-dom";

import 'tachyons';
import './common/common.css';

import Navbar from './common/navbar.jsx';
import Dashboard from './dashboard/Dashboard';
import TargetProfile from './profile/targetProfile.jsx';
import InteractorProfile from './profile/interactorProfile.jsx';
import Gallery from './gallery/Gallery.jsx';
import FOVOverview from './microscopy/FOVOverview.jsx';
import settings from './common/settings.js';


function useCellLineId () {
    // manages the current cellLineId, which is both an app-level piece of state
    // and is included in the URL of the 'profile', 'fovs', and 'annotations' pages

    let history = useHistory();
    let match = useRouteMatch('/:page');
    const [cellLineId, setCellLineId] = useState();

    const onSetCellLineId = (newCellLineId, push = true) => {

        newCellLineId = parseInt(newCellLineId);
        if (isNaN(newCellLineId)) return;

        // note: history.push must be called before setCellLineId to avoid a race-like condition
        // in which history.push triggers the Profile component's back-button callback
        // to call setCellLineId again before the call to setCellLineId here has returned
        if (push) {

            // if we are on the home page, redirect to the profile page
            let page = match?.params.page || 'profile';

            //if we are on a target-non-specific page, redirect to the profile page
            const targetNonSpecificPages = ['gallery', 'dashboard', 'microscopy', 'interactor'];
            page = targetNonSpecificPages.includes(page) ? 'profile' : page;

            console.log(`Pushing to history: /${page}/${newCellLineId}`);
            history.push(`/${page}/${newCellLineId}`);
        }

        console.log(`setCellLineId changing id from ${cellLineId} to ${newCellLineId}`);
        setCellLineId(newCellLineId);
    }
    return [cellLineId, onSetCellLineId];
}


function useGeneNameSearch (setCellLineId) {
    // returns a callback to execute when the user hits enter in a target search textbox,
    // which needs to both update the search query if it has changed and also call setCellLineId
    // even if the search has not changed, in order to run the page redirection in setCellLineId
    // (e.g., to redirect from /gallery to /profile even if the search, and cellLineId, is unchanged)
    
    let history = useHistory();
    const [doSearch, setDoSearch] = useState(false);
    const [geneName, setGeneName] = useState();

    // retrieve a cellLineId from the target name query 
    useEffect(() => {
        if (!geneName || !doSearch) return;
        d3.json(`${settings.apiUrl}/search/${geneName}`).then(result => {
            if (result.oc_id) {
                setCellLineId(result.oc_id.replace('OPCT', ''));
            } else if (result.ensg_ids) {
                history.push(`/interactor/${result.ensg_ids[0]}`);
            } else {
                // TODO: popup warning that no results were found
            }
            setDoSearch(false);            
        });
    }, [doSearch]);

    const handleGeneNameSearch = (query) => { setGeneName(query); setDoSearch(true); };
    return handleGeneNameSearch;
}


function App() {

    const [cellLineId, setCellLineId] = useCellLineId();
    const handleGeneNameSearch = useGeneNameSearch(setCellLineId);

    // handle the back button
    const history = useHistory();
    const match = useRouteMatch('/:mode/:cellLineId');
    useEffect(() => {
        return () => {
            if (history.action === "POP" && match?.isExact) {
                console.log(`back button handler with ${match.params.cellLineId}`);
            }
        }
    }, []);


    return (
        <div>
            <Navbar handleGeneNameSearch={handleGeneNameSearch}/>
            <Switch>

                <Route path="/" exact={true}>
                    <div>This is the homepage</div>
                </Route>

                <Route 
                    path={"/profile/:cellLineId"}
                    render={props => (
                        <TargetProfile 
                            {...props} 
                            cellLineId={cellLineId} 
                            setCellLineId={setCellLineId}
                            handleGeneNameSearch={handleGeneNameSearch} 
                        />
                    )}
                />

                <Route 
                    path={"/fovs/:cellLineId"}
                    render={props => (
                        <TargetProfile 
                            {...props} 
                            cellLineId={cellLineId} 
                            setCellLineId={setCellLineId}
                            showFovAnnotator
                        />
                    )}
                />

                <Route 
                    path={"/annotations/:cellLineId"}
                    render={props => (
                        <TargetProfile 
                            {...props} 
                            cellLineId={cellLineId} 
                            setCellLineId={setCellLineId} 
                            showTargetAnnotator
                        />
                    )}
                />

                <Route 
                    path={"/interactor/:ensgId"}
                    render={props => (
                        <InteractorProfile 
                            {...props} 
                            setCellLineId={setCellLineId}
                            handleGeneNameSearch={handleGeneNameSearch} 
                        />
                    )}
                />

                <Route path="/profile"></Route>
                <Route path="/gallery" component={Gallery}/>
                <Route path="/dashboard" component={Dashboard}/>

                {/* TODO: fix this - FOVOverview needs a plateId prop */}
                <Route path="/microscopy" component={FOVOverview}/>,

                <Route>
                    <div className="f2 pa3 w-100 ma">Page not found</div>
                </Route>
            </Switch>
        </div>
    )
}

ReactDOM.render(
    <BrowserRouter><App/></BrowserRouter>, 
    document.getElementById('root')
);

