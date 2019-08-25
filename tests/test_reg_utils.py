#!/usr/bin/env python
"""
Created on Monday July 29 16:19:14 2019

@authors: Ryan Hammonds

"""


try:
    import cPickle as pickle
except ImportError:
    import _pickle as pickle
import warnings
warnings.filterwarnings("ignore") 
import numpy as np
from pynets.registration import reg_utils
import nibabel as nib
from pathlib import Path   

def test_align():
    # Linear registrattion
    base_dir = str(Path(__file__).parent/"examples")
    anat_dir = base_dir + '/003/anat'
    inp = anat_dir + '/sub-003_T1w_brain.nii'
    ref = anat_dir + '/MNI152_T1_2mm_brain.nii.gz'
    out = anat_dir + '/highres2standard.nii.gz'
    xfm_out = anat_dir + '/highres2standard.mat'

    reg_utils.align(inp, ref, xfm=xfm_out, out=out, dof=12, searchrad=True, bins=256, interp=None, cost="mutualinfo", sch=None,
              wmseg=None, init=None)
    
    highres2standard_linear = nib.load(out)
    assert highres2standard_linear is not None
    
def test_applyxfm():
    base_dir = str(Path(__file__).parent/"examples")
    anat_dir = base_dir + '/003/anat'
    
    ## First test: Apply xfm from test_align to orig anat img. 
    inp = anat_dir + '/sub-003_T1w_brain.nii' 
    ref = anat_dir + '/MNI152_T1_2mm_brain.nii.gz'
    xfm = anat_dir + '/highres2standard.mat'
    aligned = anat_dir + '/highres2standard_2.nii.gz'
    reg_utils.applyxfm(ref, inp, xfm, aligned, interp='trilinear', dof=6)
    # Check test_applyfxm = test_align outputs
    out_applyxfm = nib.load(aligned)
    out_applyxfm_data = out_applyxfm.get_data()
    out_align_file = anat_dir + '/highres2standard.nii.gz'
    out_align = nib.load(out_align_file)
    out_align_data = out_align.get_data()
    check_eq_arrays = np.array_equal(out_applyxfm_data, out_align_data)
    assert check_eq_arrays is True
    
    ## Second test: Apply xfm to standard space roi (invert xfm first) >> native space roi.
    # ref is native space anat image
    ref = anat_dir + '/sub-003_T1w.nii'
    # input is standard space precuneus mask
    inp = anat_dir + '/precuneous_thr_bin.nii.gz'
    # xfm is standard2native from convert_xfm -omat standard2highres.mat highres2standard.mat
    xfm = anat_dir + '/standard2highres.mat'
    # precuenus mask in antive space
    aligned = anat_dir + '/precuneous2highres.nii.gz'
    
    reg_utils.applyxfm(ref, inp, xfm, aligned, interp='trilinear', dof=6)
    test_out = nib.load(aligned)
    assert test_out is not None
    
    
def test_align_nonlinear():
    # Nonlinear normlization
    base_dir = str(Path(__file__).parent/"examples")
    anat_dir = base_dir + '/003/anat'
    inp = anat_dir + '/sub-003_T1w.nii'
    ref = anat_dir + '/MNI152_T1_2mm.nii.gz'
    out = anat_dir + '/highres2standard_nonlinear.nii.gz'
    warp = anat_dir + '/highres2standard_warp'
    # affine mat created from test_align above.
    xfm = anat_dir + '/highres2standard.mat'
    
    reg_utils.align_nonlinear(inp, ref, xfm, out, warp, ref_mask=None, in_mask=None, config=None)
    
    highres2standard_nonlin = nib.load(out)
    assert highres2standard_nonlin is not None
    
def test_combine_xfms():
    # Combine func2anat and anat2std to create func2std mat
    base_dir = str(Path(__file__).parent/"examples")
    anat_dir = base_dir + '/003/anat'
    xfm1 = anat_dir + '/example_func2highres.mat'
    xfm2 = anat_dir + '/highres2standard.mat'
    xfmout = anat_dir + '/example_func2standard.mat'
    
    reg_utils.combine_xfms(xfm1, xfm2, xfmout)
    test_out = np.genfromtxt(xfmout, delimiter='  ')
    assert test_out is not None    
    
def test_invwarp():
    base_dir = str(Path(__file__).parent/"examples")
    anat_dir = base_dir + '/003/anat'
    ref = anat_dir + '/sub-003_T1w.nii'
    warp = anat_dir + '/highres2standard_warp'
    out = anat_dir + '/highres2standard_warp_inv.nii.gz'
    reg_utils.inverse_warp(ref, out, warp)
    out_warp = nib.load(out)
    assert out_warp is not None
    
def test_apply_warp():
    # Warp original anat to standard space using warp img (had to invwarp first) and linear mats
    base_dir = str(Path(__file__).parent/"examples")
    anat_dir = base_dir + '/003/anat'
    ref = anat_dir + '/MNI152_T1_2mm.nii.gz'
    inp = anat_dir + '/sub-003_T1w.nii'
    out = anat_dir + '/highres2standard_test_apply_warp.nii.gz'
    warp = anat_dir + '/highres2standard_warp.nii.gz'
    xfm = anat_dir + '/highres2standard.mat'
    
    reg_utils.apply_warp(ref, inp, out, warp, xfm=xfm, mask=None, interp=None, sup=False)
    highres2standard_apply_warp = anat_dir + '/highres2standard_test_apply_warp.nii.gz'
    highres2standard_apply_warp = nib.load(highres2standard_apply_warp)
    highres2standard_apply_warp = highres2standard_apply_warp.get_data()
    
    highres2standard_align_nonlinear = nib.load(anat_dir + '/highres2standard_nonlinear.nii.gz')
    highres2standard_align_nonlinear = highres2standard_align_nonlinear.get_data()
    check_eq_arrays = np.array_equal(highres2standard_apply_warp, highres2standard_align_nonlinear)
    assert check_eq_arrays is True
    
def test_segment_t1w():
    base_dir = str(Path(__file__).parent/"examples")
    anat_dir = base_dir + '/003/anat'
    t1w = anat_dir + '/sub-003_T1w.nii'
    basename = anat_dir + '/test_segment_t1w'
    out = reg_utils.segment_t1w(t1w, basename, opts='')
    print(out)
    assert out is not None
    
def test_transform_to_affine():
    base_dir = str(Path(__file__).parent/"examples")
    dwi_dir = base_dir + '/001/dmri'
    trac_out = dwi_dir + '/tractography'
    streams = trac_out + '/streamlines_Default_csa_10_5mm_curv[2_4_6]_step[0.1_0.2_0.5].trk'
    reg_utils.transform_to_affine(streams, header, affine)
    
def test_match_target_vox_res():
    base_dir = str(Path(__file__).parent/"examples")
    test_out = base_dir + '/003/test_out/test_match_target_vox_res'
    
    # Orig anat input has isotropic (1x1x1mm) dimensions.
    anat_img_file = test_out + '/sub-003_T1w.nii'
    anat_vox_size = '2mm'
    anat_out_dir = test_out
    anat_sens = 'anat'
    anat_img_file = reg_utils.match_target_vox_res(anat_img_file, anat_vox_size, anat_out_dir, anat_sens)
    anat_new_img = nib.load(anat_img_file)
    anat_dims = anat_new_img.header.get_zooms()
    anat_success = True
    for anat_dim in anat_dims[:3]:
        if anat_dim != 2:
            anat_success = False
    
    # Orig dMRI image has anisotropic (1.75x1.75x3mm) dimensions.
    dwi_img_file = test_out + '/sub-003_dwi.nii'
    dwi_vox_size = '1mm'
    dwi_out_dir = test_out 
    dwi_sens = 'dwi'
    dwi_img_file = reg_utils.match_target_vox_res(dwi_img_file, dwi_vox_size, dwi_out_dir, dwi_sens)
    dwi_new_img = nib.load(dwi_img_file)
    dwi_dims = dwi_new_img.header.get_zooms()
    dwi_success = True
    for dwi_dim in dwi_dims[:3]:
        if dwi_dim != 1:
            dwi_success = False
            
    assert anat_img_file is not None
    assert anat_success is True
    assert dwi_img_file is not None
    assert dwi_success is True
    
def test_reorient_dwi():
    base_dir = str(Path(__file__).parent/"examples")
    test_dir = base_dir + '/003/test_out/test_reorient_dwi'
    
    # iso_eddy_corrected_data_denoised_LAS.nii.gz was the original image in radiological orientation.
    # fslswapdim and fslorient manually used to create RAS image. This test attempts to convert RAS 
    # image back to LAS. Confirms by checking output array is equal to origal LAS image array.
    
    dwi_prep_rad = test_dir + '/iso_eddy_corrected_data_denoised_LAS.nii.gz'
    dwi_prep_neu = test_dir + '/iso_eddy_corrected_data_denoised_RAS.nii.gz'
    bvecs_orig = test_dir + '/bvec.bvec'
    out_dir = test_dir + '/output'
    
    dwi_prep_out, bvecs_out = reg_utils.reorient_dwi(dwi_prep_neu, bvecs_orig, out_dir)
    
    orig_rad = nib.load(dwi_prep_rad)
    orig_rad_data = orig_rad.get_data()
    
    reorient_rad = nib.load(dwi_prep_out)
    reorient_rad_data = reorient_rad.get_data()
    
    reorient_check = np.array_equal(orig_rad_data, reorient_rad_data)
    bvec_check = np.array_equal(bvecs_orig, bvecs_out)
    
    assert bvec_check is False
    assert reorient_check is True
    
def test_reorient_img():
    base_dir = str(Path(__file__).parent/"examples")
    test_dir = base_dir + '/003/test_out/test_reorient_img'
    
    # X axis increasing right to left (Radiological)
    img_in_radio = test_dir + '/sub-003_T1w_LAS.nii.gz'
    out_radio_dir = test_dir + '/output_LAS'
    
    # X axis increase from left to right (Neurological)
    img_in_neuro = test_dir + '/sub-003_T1w_RAS.nii'
    out_neuro_dir = test_dir + '/output_RAS'
    
    # Outputs should be in neurological orientation.
    LAStoRAS_img_out = reg_utils.reorient_img(img_in_radio, out_radio_dir)
    RAStoRAS_img_out = reg_utils.reorient_img(img_in_neuro, out_neuro_dir)
    
    # Original RAS data
    orig_RAS_img = nib.load(img_in_neuro)
    orig_RAS_data = orig_RAS_img.get_data()
    
    # Output from LAS input
    LAStoRAS_img = nib.load(LAStoRAS_img_out)
    LAStoRAS_data = LAStoRAS_img.get_data()
    
    # Output from RAS input
    RAStoRAS_img = nib.load(RAStoRAS_img_out)
    RAStoRAS_data = RAStoRAS_img.get_data()
    
    # Assert that arrays are equal
    check_LAS_input = np.array_equal(LAStoRAS_data, orig_RAS_data)
    check_RAS_input = np.array_equal(RAStoRAS_data, orig_RAS_data)
    check_both_outputs = np.array_equal(LAStoRAS_data, RAStoRAS_data)
    
    assert check_LAS_input is True
    assert check_RAS_input is True
    assert check_both_outputs is True
    
def test_check_orient_and_dims():
    # This test has a bak folder in its test_dir. 
    # To replicate test rm data in test_dir and cp from bak
    base_dir = str(Path(__file__).parent/"examples")
    test_dir = base_dir + '/003/test_out/test_check_orient_and_dims'
    
    # Antomical: 1x1x1mm 
    anat_LAS = test_dir + '/anat_LAS/sub-003_T1w_LAS.nii.gz'
    anat_RAS = test_dir + '/anat_RAS/sub-003_T1w_RAS.nii'
    # Diffusion: 2x2x2mm
    dmri_LAS = test_dir + '/dmri_LAS/iso_eddy_corrected_data_denoised_LAS.nii.gz'
    dmri_RAS = test_dir + '/dmri_RAS/iso_eddy_corrected_data_denoised_RAS.nii.gz'
    bvecs_LAS = test_dir + '/dmri_LAS/bvec.orig.bvec'
    bvecs_RAS = test_dir + '/dmri_RAS/bvec.trans.bvec'
    
    anat_LAStoRAS = reg_utils.check_orient_and_dims(anat_LAS, '2mm', bvecs=None)
    anat_RAStoRAS = reg_utils.check_orient_and_dims(anat_RAS, '2mm', bvecs=None)
    dmri_LAStoRAS, bvecs_LAStoRAS = reg_utils.check_orient_and_dims(dmri_RAS, '1mm', bvecs=bvecs_LAS)
    dmri_RAStoRAS, bvecs_RAStoRAS = reg_utils.check_orient_and_dims(dmri_LAS, '1mm', bvecs=bvecs_RAS)

    anat_LAStoRAS = nib.load(anat_LAStoRAS)
    anat_LAStoRAS_data = anat_LAStoRAS.get_data()
    
    anat_RAStoRAS = nib.load(anat_RAStoRAS)
    anat_RAStoRAS_data = anat_RAStoRAS.get_data()
    
    dmri_LAStoRAS = nib.load(dmri_LAStoRAS)
    dmri_LAStoRAS_data = dmri_LAStoRAS.get_data()
    dmri_RAStoRAS = nib.load(dmri_RAStoRAS)
    dmri_RAStoRAS_data = dmri_RAStoRAS.get_data()
    
    # Assert that output arrays are identical.
    anat_check = np.array_equal(anat_LAStoRAS_data, anat_RAStoRAS_data)
    dmri_check = np.array_equal(dmri_LAStoRAS_data, dmri_RAStoRAS_data)
    
    # Assert that voxel dimensions in ouputs are correct.
    anat_LAStoRAS_dims = anat_LAStoRAS.header.get_zooms()
    anat_RAStoRAS_dims = anat_RAStoRAS.header.get_zooms()
    dmri_LAStoRAS_dims = dmri_LAStoRAS.header.get_zooms()
    dmri_RAStoRAS_dims = dmri_RAStoRAS.header.get_zooms()
    
    anat_LAStoRAS_success = True
    anat_RAStoRAS_success = True
    dmri_LAStoRAS_success = True
    dmri_RAStoRAS_success = True
    
    for anat_LAStoRAS_dim in anat_LAStoRAS_dims[:3]:
        if anat_LAStoRAS_dim != 2:
            anat_LAStoRAS_success = False
    
    for anat_RAStoRAS_dim in anat_RAStoRAS_dims[:3]:
        if anat_RAStoRAS_dim != 2:
            anat_RAStoRAS_success = False
            
    for dmri_LAStoRAS_dim in dmri_LAStoRAS_dims[:3]:
        if dmri_LAStoRAS_dim != 1:
            dmri_LAStoRAS_success = False
    
    print(dmri_RAStoRAS_dims)
    for dmri_RAStoRAS_dim in dmri_RAStoRAS_dims[:3]:
        if dmri_RAStoRAS_dim != 1:
            dmri_RAStoRAS_success = False
    
    # Checks arrays    
    assert anat_check is True
    assert dmri_check is True
    # Checks voxel dimensions
    assert anat_LAStoRAS_success is True
    assert anat_RAStoRAS_success is True
    assert dmri_LAStoRAS_success is True
    assert dmri_RAStoRAS_success is True
            
    
    
    
    
    