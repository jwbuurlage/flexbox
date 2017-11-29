#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test simulation including phase-contrast effect.
We will simulate conditions close to micro-CT of a sea shell.
"""
#%%
import flexData
import flexProject
import flexUtil
import flexModel
import flexSpectrum

import numpy

#%% Create volume and forward project:
    
# Initialize images:    
x = 5
h = 512 * x
vol = numpy.zeros([1, h, h], dtype = 'float32')
proj = numpy.zeros([1, 361, h], dtype = 'float32')

# Define a simple projection geometry:
src2obj = 100     # mm
det2obj = 100     # mm   
det_pixel = 0.001 / x # mm (1 micron)

geometry = flexData.create_geometry(src2obj, det2obj, det_pixel, [0, 360], 361)

# Create phantom (150 micron wide, 15 micron wall thickness):
vol = flexModel.phantom(vol.shape, 'bubble', [150*x, 50*x])     
flexProject.forwardproject(proj, vol, geometry)

#%%
# Get the material refraction index:
c = flexSpectrum.find_nist_name('Calcium Carbonate')    
rho = c['density'] 

energy = 30 # KeV
n = flexSpectrum.material_refraction(energy, 'CaCO3', rho)

#%% Proper Fresnel propagation for phase-contrast:
   
# Create Contrast Transfer Functions for phase contrast effect and detector blurring    
phase_ctf = flexModel.get_ctf(proj.shape[::2], 'fresnel', [det_pixel, energy, src2obj, det2obj])

sigma = det_pixel 
phase_ctf *= flexModel.get_ctf(proj.shape[::2], 'gaussian', [det_pixel, sigma])

# Electro-magnetic field image:
proj_i = numpy.exp(-proj * n )
#proj_i = numpy.abs(numpy.exp(-proj * n ))**2

# Field intensity:
proj_i = flexModel.apply_ctf(proj_i, phase_ctf) ** 2

flexUtil.display_slice(proj_i, title = 'Projections (phase contrast)')

#%% Reconstruct with phase contrast:
    
vol_rec = numpy.zeros_like(vol)

flexProject.FDK(-numpy.log(proj_i), vol_rec, geometry)
flexUtil.display_slice(vol_rec, title = 'FDK')  
    
#%% Invertion of phase contrast based on dual-CTF model:
    
# Propagator (Dual CTF):
alpha = numpy.imag(n) / numpy.real(n)
dual_ctf = flexModel.get_ctf(proj.shape[::2], 'dual_ctf', [det_pixel, energy, src2obj, det2obj, alpha])
dual_ctf *= flexModel.get_ctf(proj.shape[::2], 'gaussian', [det_pixel, sigma])

# Use inverse convolution to solve for blurring and pci
proj_inv = flexModel.deapply_ctf(proj_i, dual_ctf, epsilon = 0.1)

# Depending on epsilon there is some lof frequency bias introduced...
proj_inv /= proj_inv.max()

flexUtil.display_slice(proj_inv, title = 'Inverted phase contrast')   

# Reconstruct:
vol_rec = numpy.zeros_like(vol)
flexProject.FDK(-numpy.log(proj_inv), vol_rec, geometry)
flexUtil.display_slice(vol_rec, title = 'FDK')   

#%% SIRT:
 
vol_rec = numpy.zeros_like(vol)    
flexProject.SIRT(-numpy.log(proj_inv), vol_rec, geometry, 50, options = {'bounds':[0, 50]})  
  
flexUtil.display_slice(vol_rec, title = 'SIRT') 

flexUtil.display_slice(vol, title = 'Ground Truth') 

#%% Simplified phase contrast simulation:
    
# Intensity image:    
proj_i = numpy.abs(numpy.exp(-proj * n )) ** 2   

flexUtil.display_slice(proj_i, title = 'Projections (intensity)') 

# Propagate (approximate):
alpha = numpy.imag(n) / numpy.real(n)
dual_ctf = flexModel.get_ctf(proj.shape[::2], 'dual_ctf', [det_pixel, energy, src2obj, det2obj, alpha])    
dual_ctf *= flexModel.get_ctf(proj.shape[::2], 'gaussian', [det_pixel, sigma])

proj_i = flexModel.apply_ctf(proj_i, dual_ctf)

flexUtil.display_slice(proj_i, title = 'Projections (approx. phase contrast)')  
flexUtil.plot(dual_ctf)