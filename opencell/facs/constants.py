
from FlowCytometryTools import ThresholdGate, PolyGate

# channel names
FITC, SSCA, FSCA, FSCW = 'FITC-A', 'SSC-A', 'FSC-A', 'FSC-W'

# b-paramter for hlog transform
# (this is a kwarg for the FCMeasurement.transform method)
HLOG_B = 350.0

# the number of expected wild-type (negative control) datasets
NUM_CONTROL_DATASETS = 12

# hard-coded and empirically determined maximum wild-type FITC fluorescence
# (this is presumably specific to the HEK293 mNG1-11 line)
ESTIMATED_WT_ENDPOINT = 4000

# gate for viable cells
# this is copied directly from Nathan's 'FACS_QC_v8.py'
FSC_VIABLE_GATE = ThresholdGate(8650, ['FSC-A'], region='above')
SSC_VIABLE_GATE = ThresholdGate(8500, ['SSC-A'], region='above')
VIABLE_GATE = FSC_VIABLE_GATE & SSC_VIABLE_GATE

# polygon gate for singlets
# this is copied directly from Nathan's 'FACS_QC_v8.py'
SINGLET_GATE = PolyGate(
    [
        ('8750', '250'), ('9350', '240'),
        ('10000', '290'), ('10200', '390'),
        ('9500', '400'), ('9250', '390'),
        ('9000', '360'), ('8800', '300')
    ],
    ['FSC-A', 'FSC-W'])
