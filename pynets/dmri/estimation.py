# -*- coding: utf-8 -*-
"""
Created on Tue Nov  7 10:40:07 2017
Copyright (C) 2018
@author: Derek Pisner (dPys)
"""
import warnings
import numpy as np
import nibabel as nib
warnings.filterwarnings("ignore")
np.warnings.filterwarnings('ignore')
warnings.filterwarnings("ignore", message="numpy.ufunc size changed")


def tens_mod_fa_est(gtab_file, dwi_file, B0_mask):
    '''
    Estimate a tensor FA image to use for registrations.

    Parameters
    ----------
    gtab_file : str
        File path to pickled DiPy gradient table object.
    dwi_file : str
        File path to diffusion weighted image.
    B0_mask : str
        File path to B0 brain mask.

    Returns
    -------
    fa_path : str
        File path to FA Nifti1Image.
    B0_mask : str
        File path to B0 brain mask Nifti1Image.
    gtab_file : str
        File path to pickled DiPy gradient table object.
    dwi_file : str
        File path to diffusion weighted Nifti1Image.
    '''
    import os
    from dipy.io import load_pickle
    from dipy.reconst.dti import TensorModel
    from dipy.reconst.dti import fractional_anisotropy

    data = nib.load(dwi_file).get_fdata()
    gtab = load_pickle(gtab_file)

    print('Generating simple tensor FA image to use for registrations...')
    nodif_B0_img = nib.load(B0_mask)
    B0_mask_data = nodif_B0_img.get_fdata().astype('bool')
    nodif_B0_affine = nodif_B0_img.affine
    model = TensorModel(gtab)
    mod = model.fit(data, B0_mask_data)
    FA = fractional_anisotropy(mod.evals)
    FA[np.isnan(FA)] = 0
    fa_img = nib.Nifti1Image(FA.astype(np.float32), nodif_B0_affine)
    fa_path = "%s%s" % (os.path.dirname(B0_mask), '/tensor_fa.nii.gz')
    nib.save(fa_img, fa_path)
    return fa_path, B0_mask, gtab_file, dwi_file


def tens_mod_est(gtab, data, wm_in_dwi):
    '''
    Estimate a tensor model from dwi data.

    Parameters
    ----------
    gtab : Obj
        DiPy object storing diffusion gradient information
    data : array
        4D numpy array of diffusion image data.
    wm_in_dwi : str
        File path to white-matter tissue segmentation Nifti1Image.

    Returns
    -------
    tensor_odf : obj
        Tensor-estimated orientation distribution function.
    '''
    from dipy.reconst.dti import TensorModel
    from dipy.data import get_sphere
    print('Fitting tensor model...')
    sphere = get_sphere('repulsion724')
    wm_in_dwi_mask = nib.load(wm_in_dwi).get_fdata().astype('bool')
    model = TensorModel(gtab)
    mod = model.fit(data, wm_in_dwi_mask)
    tensor_odf = mod.odf(sphere)
    return tensor_odf


def csa_mod_est(gtab, data, wm_in_dwi):
    '''
    Estimate a Constant Solid Angle (CSA) model from dwi data.

    Parameters
    ----------
    gtab : Obj
        DiPy object storing diffusion gradient information
    data : array
        4D numpy array of diffusion image data.
    wm_in_dwi : str
        File path to white-matter tissue segmentation Nifti1Image.

    Returns
    -------
    csa_mod : obj
        Spherical harmonics coefficients of the CSA-estimated reconstruction model.
    '''
    from dipy.reconst.shm import CsaOdfModel
    print('Fitting CSA model...')
    wm_in_dwi_mask = nib.load(wm_in_dwi).get_fdata().astype('bool')
    model = CsaOdfModel(gtab, sh_order=6)
    csa_mod = model.fit(data, wm_in_dwi_mask).shm_coeff
    return csa_mod


def csd_mod_est(gtab, data, wm_in_dwi):
    '''
    Estimate a Constrained Spherical Deconvolution (CSD) model from dwi data.

    Parameters
    ----------
    gtab : Obj
        DiPy object storing diffusion gradient information.
    data : array
        4D numpy array of diffusion image data.
    wm_in_dwi : str
        File path to white-matter tissue segmentation Nifti1Image.

    Returns
    -------
    csd_mod : obj
        Spherical harmonics coefficients of the CSD-estimated reconstruction model.
    '''
    from dipy.reconst.csdeconv import ConstrainedSphericalDeconvModel, recursive_response
    print('Fitting CSD model...')
    wm_in_dwi_mask = nib.load(wm_in_dwi).get_fdata().astype('bool')
    try:
        print('Reconstructing...')
        model = ConstrainedSphericalDeconvModel(gtab, None, sh_order=6)
    except:
        print('Falling back to recursive response...')
        response = recursive_response(gtab, data, mask=wm_in_dwi_mask, sh_order=8, peak_thr=0.01, init_fa=0.08,
                                      init_trace=0.0021, iter=8, convergence=0.001, parallel=False)
        print('CSD Reponse: ' + str(response))
        model = ConstrainedSphericalDeconvModel(gtab, response)
    csd_mod = model.fit(data, wm_in_dwi_mask).shm_coeff
    return csd_mod


def streams2graph(atlas_mni, streams, overlap_thr, dir_path, track_type, target_samples, conn_model, network, node_size,
                  dens_thresh, ID, roi, min_span_tree, disp_filt, parc, prune, atlas, uatlas, labels,
                  coords, norm, binary, voxel_size='2mm'):
    '''
    Use tracked streamlines as a basis for estimating a structural connectome.

    Parameters
    ----------
    atlas_mni : str
        File path to atlas parcellation Nifti1Image in T1w-warped MNI space.
    streams : str
        File path to streamline array sequence in .trk format.
    overlap_thr : int
        Number of voxels for which a given streamline must intersect with an ROI
        for an edge to be counted.
    dir_path : str
        Path to directory containing subject derivative data for a given pynets run.
    track_type : str
        Tracking algorithm used (e.g. 'local' or 'particle').
    target_samples : int
        Total number of streamline samples specified to generate streams.
    conn_model : str
        Connectivity reconstruction method (e.g. 'csa', 'tensor', 'csd').
    network : str
        Resting-state network based on Yeo-7 and Yeo-17 naming (e.g. 'Default')
        used to filter nodes in the study of brain subgraphs.
    node_size : int
        Spherical centroid node size in the case that coordinate-based centroids
        are used as ROI's for tracking.
    dens_thresh : bool
        Indicates whether a target graph density is to be used as the basis for
        thresholding.
    ID : str
        A subject id or other unique identifier.
    roi : str
        File path to binarized/boolean region-of-interest Nifti1Image file.
    min_span_tree : bool
        Indicates whether local thresholding from the Minimum Spanning Tree
        should be used.
    disp_filt : bool
        Indicates whether local thresholding using a disparity filter and
        'backbone network' should be used.
    parc : bool
        Indicates whether to use parcels instead of coordinates as ROI nodes.
    prune : bool
        Indicates whether to prune final graph of disconnected nodes/isolates.
    atlas : str
        Name of atlas parcellation used.
    uatlas : str
        File path to atlas parcellation Nifti1Image in MNI template space.
    labels : list
        List of string labels corresponding to graph nodes.
    coords : list
        List of (x, y, z) tuples corresponding to a coordinate atlas used or
        which represent the center-of-mass of each parcellation node.
    norm : int
        Indicates method of normalizing resulting graph.
    binary : bool
        Indicates whether to binarize resulting graph edges to form an
        unweighted graph.
    voxel_size : str
        Target isotropic voxel resolution of all input Nifti1Image files.

    Returns
    -------
    atlas_mni : str
        File path to atlas parcellation Nifti1Image in T1w-warped MNI space.
    streams : str
        File path to streamline array sequence in .trk format.
    conn_matrix : array
        Adjacency matrix stored as an m x n array of nodes and edges.
    track_type : str
        Tracking algorithm used (e.g. 'local' or 'particle').
    target_samples : int
        Total number of streamline samples specified to generate streams.
    dir_path : str
        Path to directory containing subject derivative data for given run.
    conn_model : str
        Connectivity reconstruction method (e.g. 'csa', 'tensor', 'csd').
    network : str
        Resting-state network based on Yeo-7 and Yeo-17 naming (e.g. 'Default')
        used to filter nodes in the study of brain subgraphs.
    node_size : int
        Spherical centroid node size in the case that coordinate-based centroids
        are used as ROI's for tracking.
    dens_thresh : bool
        Indicates whether a target graph density is to be used as the basis for
        thresholding.
    ID : str
        A subject id or other unique identifier.
    roi : str
        File path to binarized/boolean region-of-interest Nifti1Image file.
    min_span_tree : bool
        Indicates whether local thresholding from the Minimum Spanning Tree
        should be used.
    disp_filt : bool
        Indicates whether local thresholding using a disparity filter and
        'backbone network' should be used.
    parc : bool
        Indicates whether to use parcels instead of coordinates as ROI nodes.
    prune : bool
        Indicates whether to prune final graph of disconnected nodes/isolates.
    atlas : str
        Name of atlas parcellation used.
    uatlas : str
        File path to atlas parcellation Nifti1Image in MNI template space.
    labels : list
        List of string labels corresponding to graph nodes.
    coords : list
        List of (x, y, z) tuples corresponding to a coordinate atlas used or
        which represent the center-of-mass of each parcellation node.
    norm : int
        Indicates method of normalizing resulting graph.
    binary : bool
        Indicates whether to binarize resulting graph edges to form an
        unweighted graph.
    '''
    from dipy.tracking.streamline import Streamlines
    from dipy.tracking._utils import (_mapping_to_voxel, _to_voxel_coordinates)
    import networkx as nx
    from itertools import combinations
    from collections import defaultdict
    import time

    # Read Streamlines
    streamlines_mni = nib.streamlines.load(streams)
    streamlines = Streamlines(streamlines_mni.streamlines)

    # Load parcellation
    atlas_data = nib.load(atlas_mni).get_fdata()

    # Instantiate empty networkX graph object & dictionary
    # Create voxel-affine mapping
    lin_T, offset = _mapping_to_voxel(np.eye(4), voxel_size)
    mx = len(np.unique(atlas_data.astype(np.int64)))
    g = nx.Graph(ecount=0, vcount=mx)
    edge_dict = defaultdict(int)
    node_dict = dict(zip(np.unique(atlas_data), np.arange(mx)))

    # Add empty vertices
    for node in range(mx):
        g.add_node(node)

    # Build graph
    start_time = time.time()
    for s in streamlines:
        # Map the streamlines coordinates to voxel coordinates
        points = _to_voxel_coordinates(s, lin_T, offset)

        # get labels for label_volume
        i, j, k = points.T
        lab_arr = atlas_data[i, j, k]
        endlabels = []
        for lab in np.unique(lab_arr):
            if lab > 0:
                if np.sum(lab_arr == lab) >= overlap_thr:
                    endlabels.append(node_dict[lab])

        edges = combinations(endlabels, 2)
        for edge in edges:
            lst = tuple([int(node) for node in edge])
            edge_dict[tuple(sorted(lst))] += 1

        edge_list = [(k[0], k[1], v) for k, v in edge_dict.items()]
        g.add_weighted_edges_from(edge_list)
    print("%s%s%s" % ('Graph construction runtime: ',
    np.round(time.time() - start_time, 1), 's'))

    # Convert to numpy matrix
    conn_matrix_raw = nx.to_numpy_matrix(g)

    # Enforce symmetry
    conn_matrix_symm = np.maximum(conn_matrix_raw, conn_matrix_raw.T)

    # Remove background label
    conn_matrix = conn_matrix_symm[1:, 1:]

    return atlas_mni, streams, conn_matrix, track_type, target_samples, dir_path, conn_model, network, node_size, dens_thresh, ID, roi, min_span_tree, disp_filt, parc, prune, atlas, uatlas, labels, coords, norm, binary
