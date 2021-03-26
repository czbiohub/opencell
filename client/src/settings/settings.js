import React, { Component } from 'react';

// the xy size of the z-stack
const zSliceSize = 600;

// the number of z-slices in the z-stack
const numZSlices = 27;

// the type of mass-spec clustering results to display
const clusteringAnalysisType = 'primary:mcl_i3.0_haircut:keepcore_subcluster:mcl_hybrid_stoichs_7.0_1113';
// 'primary:mcl_i3.0_haircut:keepcore_subcluster:mcl_hybrid_stoichs_3.0_20210111'

// constants defined by webpack at buildtime
let apiUrl = `${APP_SERVER==='ess' ? 'http' : 'https'}://${API_URL}`;
let defaultAppMode = APP_MODE;
let gaTrackingId = GA_TRACKING_ID;

const ModeContext = React.createContext();

export default {
    zSliceSize,
    numZSlices,
    clusteringAnalysisType,
    apiUrl,
    ModeContext,
    defaultAppMode,
    gaTrackingId,
}
