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

    let history = useHistory();
    let match = useRouteMatch('/:mode');
    const [cellLineId, setCellLineId] = useState();

    const onSetCellLineId = (newCellLineId, push = true) => {

        newCellLineId = parseInt(newCellLineId);
        if (isNaN(newCellLineId) || newCellLineId===cellLineId) return;

        // note: history.push must be called before setCellLineId to avoid a race-like condition
        // in which history.push triggers the Profile component's back-button callback
        // to call setCellLineId again before the call to setCellLineId here has 'finished'
        if (push) {
            console.log(`Pushing to history: /${match.params.mode}/${newCellLineId}`);
            history.push(`/${match.params.mode}/${newCellLineId}`);
        }

        console.log(`setCellLineId changing id from ${cellLineId} to ${newCellLineId}`);
        setCellLineId(newCellLineId);
    }
    return [cellLineId, onSetCellLineId];
}


function App() {

    const [cellLineId, setCellLineId] = useCellLineId();
    const [targetNameQuery, setTargetNameQuery] = useState();

    // retrieve a cellLineId from the target name query 
    useEffect(() => {
        if (!targetNameQuery) return;
        d3.json(`${settings.apiUrl}/lines?target=${targetNameQuery}`).then(lines => {
            for (const line of lines) {
                if (line) {
                    setCellLineId(line.metadata.cell_line_id, true);
                    break;
                }
            }
        });
    }, [targetNameQuery]);


    let history = useHistory();
    let location = useLocation();
    let match = useRouteMatch('/:mode/:cellLineId');


    // handle the back button
    useEffect(() => {
        return () => {
            if (history.action === "POP" && match?.isExact) {
                console.log(`back button handler with ${match.params.cellLineId}`);
            }
        }
    }, []);


    return (
        <div>
            <Navbar onSearchChange={setTargetNameQuery}/>
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

