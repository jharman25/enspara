import tempfile

from nose.tools import assert_equal, assert_is
from numpy.testing import assert_array_equal, assert_allclose

import numpy as np
import scipy.sparse

from . import builders
from .transition_matrices import assigns_to_counts, eigenspectrum, \
   trim_disconnected, TrimMapping
from .timescales import implied_timescales
from .test_data import TRIMMABLE

# array types we want to guarantee support for
ARR_TYPES = [
    np.array, scipy.sparse.lil_matrix, scipy.sparse.csr_matrix,
    scipy.sparse.coo_matrix, scipy.sparse.csc_matrix,
    scipy.sparse.dia_matrix, scipy.sparse.dok_matrix
]


def test_trim_mapping_construction():

    tm1 = TrimMapping()
    tm1.to_original = {0: 0, 1: 1, 2: 3, 3: 7}

    tm2 = TrimMapping()
    tm2.to_mapped = {0: 0, 1: 1, 3: 2, 7: 3}

    assert_equal(tm1, tm2)


def test_trim_mapping_roundtrip():
    transformations = [(0, 0),
                       (1, -1),
                       (2, 1),
                       (3, 2)]

    tm = TrimMapping(transformations)

    with tempfile.NamedTemporaryFile(mode='w') as f:
        tm.write(f)
        f.flush()

        with open(f.name, 'r') as f2:
            assert_equal(
                f2.read().split('\n'),
                ['original,mapped', '0,0', '1,-1', '2,1', '3,2', ''])
        with open(f.name, 'r') as f2:
            tm2 = TrimMapping.read(f2)
            assert_equal(tm, tm2)

    with tempfile.NamedTemporaryFile() as f:
        tm.save(f.name)
        tm2 = TrimMapping.load(f.name)
        assert_equal(tm, tm2)


def test_implied_timescales():

    in_assigns = TRIMMABLE['assigns']

    # test without symmetrization
    tscales = implied_timescales(in_assigns, lag_times=range(1, 5),
                                 method=builders.normalize)
    expected = TRIMMABLE['no_trimming']['implied_timescales']['normalize']

    assert_allclose(tscales, expected, rtol=1e-03)

    # test with explicit symmetrization
    tscales = implied_timescales(
        in_assigns, lag_times=range(1, 5), method=builders.transpose)
    expected = TRIMMABLE['no_trimming']['implied_timescales']['transpose']

    # test with trimming
    tscales = implied_timescales(
        in_assigns, lag_times=range(1, 5), method=builders.transpose,
        trim=True)
    expected = TRIMMABLE['trimming']['implied_timescales']['transpose']

    assert_allclose(tscales, expected, rtol=1e-03)

    tscales = implied_timescales(
        in_assigns, lag_times=range(1, 5), method=builders.transpose,
        trim=False, n_times=3)

    assert_equal(tscales.shape, (4, 3))


def test_eigenspectrum_types():

    expected_vals = np.array([1., 0.56457513, 0.03542487])
    expected_vecs = np.array(
        [[0.33333333,  0.8051731 , -0.13550992],
         [0.33333333, -0.51994159, -0.62954540],
         [0.33333333, -0.28523152,  0.76505532]])

    for arr_type in ARR_TYPES:
        probs = arr_type(
            [[0.7, 0.1, 0.2],
             [0.1, 0.5, 0.4],
             [0.2, 0.4, 0.4]])

        try:
            e_vals, e_vecs = eigenspectrum(probs)
        except ValueError:
            print("Failed on type %s" % arr_type)
            raise

        assert_allclose(e_vecs, expected_vecs)
        assert_allclose(e_vals, expected_vals)


def test_assigns_to_counts_negnums():
    '''assigns_to_counts ignores -1 values
    '''

    in_m = np.array(
            [[0, 2,  0, -1],
             [1, 2, -1, -1],
             [1, 0,  0, 1]])

    counts = assigns_to_counts(in_m)

    expected = np.array([[1, 1, 1],
                         [1, 0, 1],
                         [1, 0, 0]])

    assert_array_equal(counts.toarray(), expected)


def test_transpose_types():
    for arr_type in ARR_TYPES:

        in_m = arr_type(
            [[0, 2, 8],
             [4, 2, 4],
             [7, 3, 0]])
        out_m = builders.transpose(in_m)

        assert_equal(
            type(in_m), type(out_m),
            "builders.transpose was given %s but returned %s." %
            (type(in_m), type(out_m)))

        # cast to ndarray if necessary for comparison to correct result
        try:
            out_m = out_m.toarray()
        except AttributeError:
            pass

        out_m = np.round(out_m, decimals=1)

        expected = np.array(
            [[0.0, 0.3, 0.7],
             [0.4, 0.2, 0.4],
             [0.7, 0.3, 0.0]])

        assert_array_equal(
            out_m,
            expected)


def test_trim_disconnected():
    # 3 connected components, one disconnected (state 4)

    for arr_type in ARR_TYPES:
        given = arr_type([[1, 2, 0, 0],
                          [2, 1, 0, 1],
                          [0, 0, 1, 0],
                          [0, 1, 0, 2]])

        mapping, trimmed = trim_disconnected(given)
        assert_is(type(trimmed), type(given))

        expected_tcounts = np.array([[1, 2, 0],
                                     [2, 1, 1],
                                     [0, 1, 2]])

        try:
            trimmed = trimmed.toarray()
        except AttributeError:
            pass

        assert_array_equal(trimmed, expected_tcounts)

        expected_mapping = TrimMapping([(0, 0), (1, 1), (3, 2)])
        assert_equal(mapping, expected_mapping)

        mapping, trimmed = trim_disconnected(given, threshold=2)

        try:
            trimmed = trimmed.toarray()
        except AttributeError:
            pass

        expected_tcounts = np.array([[1, 2],
                                     [2, 1]])
        assert_array_equal(trimmed, expected_tcounts)

        expected_mapping = TrimMapping([(0, 0), (1, 1)])
        assert_equal(mapping, expected_mapping)