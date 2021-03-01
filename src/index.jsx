import * as d3 from 'd3';
import React, { useState, useEffect, useContext } from 'react';
import ReactDOM from 'react-dom';
import ReactGA from 'react-ga';
import {Alert} from '@blueprintjs/core';
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
import UMAPContainer from './umap/umapContainer.jsx';
import About from './about/About.jsx';
import SearchResults from './common/searchResults.jsx';
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

            // if we are on a target-non-specific page, redirect to the profile page
            const targetNonSpecificPages = [
                'gallery', 'dashboard', 'microscopy', 'interactor', 'search'
            ];
            page = targetNonSpecificPages.includes(page) ? 'target' : page;
            
            const newUrl = `/${page}/${newCellLineId}${history.location.search}`;
            //console.log(`Pushing to history: ${newUrl}`);
            history.push(newUrl);
        }

        //console.log(`setCellLineId changing id from ${cellLineId} to ${newCellLineId}`);
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
    const [doSearch, setDoSearch] = useState(true);
    const [searchResultsFound, setSearchResultsFound] = useState(true);
    const [geneName, setGeneName] = useState();
    const modeContext = useContext(settings.ModeContext);

    // retrieve a cellLineId from the target name query 
    // HACK: if there's more than one matching ensg_id or oc_id, we arbitrarily pick one
    useEffect(() => {

        if (!geneName || !doSearch) return;

        // hack: remove slashes, which are used in some cytoscape node labels
        const sanitizedGeneName = geneName.split('/')[0]

        const url = `
            ${settings.apiUrl}/search/${sanitizedGeneName}?publication_ready=${modeContext==='public'}
        `;
        d3.json(url).then(result => {
            if (result.oc_ids) {
                setCellLineId(result.oc_ids[0].replace('OPCT', ''));
            } else if (result.ensg_ids) {
                history.push(`/interactor/${result.ensg_ids[0]}${history.location.search}`);
            } else {
                setSearchResultsFound(false);
                return;
            }
        });
    }, [geneName]);

    const searchAlert = (
            <Alert
                style={{minWidth: '500px'}}
                isOpen={!searchResultsFound && geneName}
                confirmButtonText='Okay'
                canEscapeKeyCancel={true}
                canOutsideClickCancel={true}
                onClose={() => setSearchResultsFound(true)}
                onOpened={(node) => {
                    node.focus();
                    node.onkeyup = event => (event.keyCode===13) ? setSearchResultsFound(true) : null;
                }}
            >
                <p className='f4'>{`No gene named '${geneName?.toUpperCase()}' found in OpenCell`}</p>
            </Alert>
    );

    const handleGeneNameSearch = (query) => { setGeneName(query); setDoSearch(true); };
    return [searchAlert, handleGeneNameSearch];
}


function useGoogleAnalytics () {
    const location = useLocation();
    useEffect(() => {
        ReactGA.initialize(settings.gaTrackingId);
        ReactGA.pageview(`${location.pathname}${location.search}`);
    }, [location]);
}


function App() {

    const modeContext = useContext(settings.ModeContext);
    if (modeContext==='public') useGoogleAnalytics();

    const [cellLineId, setCellLineId] = useCellLineId();
    const [searchAlert, handleGeneNameSearch] = useGeneNameSearch(setCellLineId);

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
            key='target'
            path="/target"
            exact strict
            render={props => (
                <TargetProfile 
                    {...props} 
                    setCellLineId={setCellLineId}
                    handleGeneNameSearch={handleGeneNameSearch} 
                />
            )}
        />,
        <Route 
            key='target'
            path="/target/:cellLineId"
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
            key='interactor'
            path="/interactor/:ensgId"
            render={props => (
                <InteractorProfile 
                    {...props} 
                    setCellLineId={setCellLineId}
                    handleGeneNameSearch={handleGeneNameSearch} 
                />
            )}
        />,
        <Route 
            key='search'
            path="/search/:query"
            render={props => (
                <SearchResults 
                    {...props} 
                    setCellLineId={setCellLineId}
                    handleGeneNameSearch={handleGeneNameSearch} 
                />
            )}
        />
    ];

    const privateCellLineRoutes = [
        <Route 
            key='fovs'
            path="/fovs/:cellLineId"
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
            key='annotations'
            path="/annotations/:cellLineId"
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
                <Route path="/" exact={true} component={About}/>

                {publicCellLineRoutes}
                {modeContext==='private' ? privateCellLineRoutes : null}

                <Route path="/target"></Route>
                <Route path="/gallery" component={Gallery}/>
                <Route path="/umap" component={UMAPContainer}/>
                <Route path="/dashboard" component={Dashboard}/>

                <Route><div className="f2 pa3 w-100 ma">Page not found</div></Route>
            </Switch>
            {searchAlert}
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

