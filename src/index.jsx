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
import Profile from './profile/Profile.jsx';
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
            const targetNonSpecificPages = ['gallery', 'dashboard', 'microscopy'];
            page = targetNonSpecificPages.includes(page) ? 'profile' : page;

            console.log(`Pushing to history: /${page}/${newCellLineId}`);
            history.push(`/${page}/${newCellLineId}`);
        }

        console.log(`setCellLineId changing id from ${cellLineId} to ${newCellLineId}`);
        setCellLineId(newCellLineId);
    }
    return [cellLineId, onSetCellLineId];
}


function useTargetSearch (setCellLineId) {
    // returns a callback to execute when the user hits enter in a target search textbox,
    // which needs to both update the search query if it has changed and also call setCellLineId
    // even if the search has not changed, in order to run the page redirection in setCellLineId
    // (e.g., to redirect from /gallery to /profile even if the search, and cellLineId, is unchanged)
    
    const [doSearch, setDoSearch] = useState(false);
    const [targetNameQuery, setTargetNameQuery] = useState();

    // retrieve a cellLineId from the target name query 
    useEffect(() => {
        if (!targetNameQuery || !doSearch) return;
        d3.json(`${settings.apiUrl}/lines?target=${targetNameQuery}`).then(lines => {
            for (const line of lines) {
                if (line) {
                    setCellLineId(line.metadata.cell_line_id, true);
                    setDoSearch(false);
                    break;
                }
            }
        });
    }, [doSearch]);

    const onTargetSearch = (query) => { setTargetNameQuery(query); setDoSearch(true); };
    return onTargetSearch;
}


function App() {

    const [cellLineId, setCellLineId] = useCellLineId();
    const onTargetSearch = useTargetSearch(setCellLineId);

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
            <Navbar onSearchChange={onTargetSearch}/>
            <Switch>
                <Route path="/" exact={true}>
                    <div>This is the homepage</div>
                </Route>

                <Route path="/dashboard" component={Dashboard}/>

                <Route 
                    path={"/profile/:cellLineId"}
                    render={props => (
                        <Profile 
                            {...props} cellLineId={cellLineId} setCellLineId={setCellLineId}
                        />
                    )}
                />

                {/* default initial target */}
                <Route path={"/profile"}></Route>

                <Route 
                    path={"/fovs/:cellLineId"}
                    render={props => (
                        <Profile 
                            {...props} cellLineId={cellLineId} setCellLineId={setCellLineId} showFovAnnotator
                        />
                    )}
                />

                <Route 
                    path={"/annotations/:cellLineId"}
                    render={props => (
                        <Profile 
                            {...props} cellLineId={cellLineId} setCellLineId={setCellLineId} showTargetAnnotator
                        />
                    )}
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

