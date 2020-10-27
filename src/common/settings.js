import React, { Component } from 'react';

// the xy size of the z-stack
const zSliceSize = 600;

// the number of z-slices in the z-stack
const numZSlices = 27;

// constants defined by webpack at buildtime
let apiUrl = API_URL;
let defaultAppMode = DEFAULT_APP_MODE;
let gaTrackingId = GA_TRACKING_ID;

const ModeContext = React.createContext();

export default {
    zSliceSize,
    numZSlices,
    apiUrl,
    ModeContext,
    defaultAppMode,
    gaTrackingId,
}
