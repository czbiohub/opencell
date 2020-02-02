import numpy as np
from opencell.imaging import utils


def test_autoscale():

    # all zeros in, all zeros out
    im_in = np.zeros((10,), dtype=float)
    im_out = utils.autoscale(im_in, percentile=0, dtype='uint8')
    np.testing.assert_array_equal(im_in.astype('uint8'), im_out)

    # all equal values in, all zeros out
    im_in = np.ones((10,), dtype=float)
    im_out = utils.autoscale(im_in, percentile=0, dtype='uint8')
    np.testing.assert_array_equal((0*im_in).astype('uint8'), im_out)

    # check min and max values with no percentile
    im_in = np.array([1, 11])
    im_out8 = utils.autoscale(im_in, percentile=0, dtype='uint8')
    im_out16 = utils.autoscale(im_in, percentile=0, dtype='uint16')
    assert im_out8[0] == 0
    assert im_out8[1] == 255
    assert im_out16[0] == 0
    assert im_out16[1] == 65535

    # test percentiles
    im_in = np.concatenate((np.zeros(5) + 1, np.zeros(85) + 5, np.zeros(10) + 6), axis=0)
    im_out = utils.autoscale(im_in, percentile=0, dtype='uint8')
    assert set(im_out[:]) == set([0, 255*4/5, 255])

    im_out = utils.autoscale(im_in, percentile=1, dtype='uint8')
    assert set(im_out[:]) == set([0, 255*4/5, 255])

    im_out = utils.autoscale(im_in, percentile=6, dtype='uint8')
    assert set(im_out[:]) == set([0, 255])

    im_out = utils.autoscale(im_in, percentile=11, dtype='uint8')
    assert set(im_out[:]) == set([0, ])
