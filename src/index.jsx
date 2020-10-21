import * as d3 from 'd3';
import React, { useState, useEffect, useContext } from 'react';
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
    // and is included in the URL of the 'target', 'fovs', and 'annotations' pages

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
            let page = match?.params.page || 'target';

            //if we are on a target-non-specific page, redirect to the profile page
            const targetNonSpecificPages = ['gallery', 'dashboard', 'microscopy', 'interactor'];
            page = targetNonSpecificPages.includes(page) ? 'target' : page;
            
            const newUrl = `/${page}/${newCellLineId}${history.location.search}`;
            console.log(`Pushing to history: ${newUrl}`);
            history.push(newUrl);
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
    const modeContext = useContext(settings.ModeContext);

    // retrieve a cellLineId from the target name query 
    // HACK: if there's more than one matching ensg_id or oc_id, we arbitrarily pick one
    useEffect(() => {
        if (!geneName || !doSearch) return;

        // hack: remove slashes, which are used in some cytoscape node labels
        const sanitizedGeneName = geneName.split('/')[0]

        const url = `${settings.apiUrl}/search/${sanitizedGeneName}?publication_ready=${modeContext==='public'}`; 
        console.log(`Search url: ${url}`);
        d3.json(url).then(result => {
            if (result.oc_ids) {
                setCellLineId(result.oc_ids[0].replace('OPCT', ''));
            } else if (result.ensg_ids) {
                history.push(`/interactor/${result.ensg_ids[0]}${history.location.search}`);
            } else {
                // TODO: popup warning that no results were found
                console.log(`No search results for gene name "${geneName}"`);
            }
            setDoSearch(false);            
        });
    }, [doSearch]);

    const handleGeneNameSearch = (query) => { setGeneName(query); setDoSearch(true); };
    return handleGeneNameSearch;
}


function App() {
    const modeContext = useContext(settings.ModeContext);

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

    const publicCellLineRoutes = [
        <Route 
            path={"/target/:cellLineId"}
            render={props => (
                <TargetProfile 
                    {...props} 
                    cellLineId={cellLineId} 
                    setCellLineId={setCellLineId}
                    handleGeneNameSearch={handleGeneNameSearch} 
                />
            )}
        />,
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
    ];

    const privateCellLineRoutes = [
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
        />,
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
    ];

    return (
        <div>
            <Navbar handleGeneNameSearch={handleGeneNameSearch}/>
            <Switch>

                <Route path="/" exact={true}>
                    <div>This is the homepage</div>
                </Route>

                {publicCellLineRoutes}
                {modeContext==='private' ? privateCellLineRoutes : null}

                <Route path="/target"></Route>
                <Route path="/gallery" component={Gallery}/>
                <Route path="/dashboard" component={Dashboard}/>

                {/* TODO: fix this - FOVOverview needs a plateId prop */}
                {/* <Route path="/microscopy" component={FOVOverview}/>, */}

                <Route>
                    <div className="f2 pa3 w-100 ma">Page not found</div>
                </Route>
            </Switch>
        </div>
    )
}

let appMode = settings.defaultAppMode;

// only allow setting the appMode from the URL if the defaultAppMode is 'private'
const urlParams = new URLSearchParams(window.location.search);
if (appMode==='private') appMode = urlParams.get('mode') || appMode;

ReactDOM.render(
    <BrowserRouter>
        <settings.ModeContext.Provider value={appMode}>
            <App/>
        </settings.ModeContext.Provider>
    </BrowserRouter>, 
    document.getElementById('root')
);

