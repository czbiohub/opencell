
import numpy as np
from opencell.facs import constants as facs_constants
FITC, SSCA, FSCA = facs_constants.FITC, facs_constants.SSCA, facs_constants.FSCA


def transform_and_gate_dataset(dataset):
    '''
    Apply hard-coded gates to select viable single cells,
    and hlog-transform the dataset

    Parameters
    ----------
    dataset : an FCMeasurement instance

    '''

    # transform first...
    dataset = dataset.transform('hlog', channels=[FITC, FSCA, SSCA], b=facs_constants.HLOG_B)
    
    # ...and then apply the gates
    dataset = dataset.gate(facs_constants.VIABLE_GATE).gate(facs_constants.SINGLET_GATE)

    return dataset


def hlog_inverse(value):
    '''
    Inverse of base-10 hyperlog transform
    Copied directly from Nathan's 'FACS_QC_v8.py' script
    '''

    b = facs_constants.HLOG_B

    # -------------------------------------------------------------------------
    # 
    # these constants are copied from Nathan's script
    # TODO: understand what they mean
    r = 10**4
    d = np.log10(2**18)
    #
    # -------------------------------------------------------------------------
    
    aux = 1. * d / r * value
    s = np.sign(value)
    if s.shape:
        s[s == 0] = 1
    elif s == 0:
        s = 1
    return s * 10 ** (s * aux) + b * aux - s

