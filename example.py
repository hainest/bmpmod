import numpy as np

import matplotlib
import matplotlib.pyplot as plt

import astropy
import astropy.table as atpy
from astropy import cosmology
from astropy.cosmology import FlatLambdaCDM
import astropy.units as u
from astropy.table import Column

import sherpa
import sherpa.ui as ui

import scipy
import scipy.integrate
import scipy.optimize as op


import time

import emcee
import corner


#suppress log info from sherpa
import logging
logger = logging.getLogger("sherpa")
logger.setLevel(logging.ERROR)


# default parameters and unit conversion factors
import defaultparams.params as params
import defaultparams.uconv as uconv

# functions to read data into format used by module
from bmpmod.set_prof_data import set_ne, set_tspec, set_meta

# functions to fit the gas density profile
from bmpmod.fit_density import fitne, find_nemodeltype

# functions to determine mass profile through backwards modelling
from bmpmod.fit_massprof import fit_ml, fit_mcmc

# functions to analyze the marginalized posterior distribution
from bmpmod.posterior_mcmc import calc_posterior_mcmc, samples_results

# plotting functions
from bmpmod.plotting import plt_mcmc_freeparam, plt_summary, plt_summary_nice

# functions specifically to generate mock data from Vikhlinin+ profiles
from exampledata.vikhlinin_prof import vikhlinin_tprof, vikhlinin_neprof, gen_mock_data

if __name__ == '__main__':

    # select any cluster ID from the Vikhlinin+ paper
    clusterID = 'A262'

    clustermeta, ne_data, tspec_data, nemodel_vikhlinin, tmodel_vikhlinin \
        = gen_mock_data(clusterID=clusterID,
                        N_ne=25,
                        N_temp=12,
                        noise_ne=0.15,
                        noise_temp=0.05,
                        refindex=-1,
                        incl_mstar=1,
                        incl_mgas=1)

    ########################################################################
    ########################################################################
    #######################################################################

    '''
    Gas density profile
    '''

    # fit all four ne moels and return the model with the lowest
    # reduced chi-squared as nemodeltype
    nemodeltype, fig1 = find_nemodeltype(ne_data=ne_data,
                                        tspec_data=tspec_data,
                                        optplt=1)
    print 'model with lowest reduced chi-squared:', nemodeltype

    # Find the parameters and errors of the seleted gas density model
    nemodel = fitne(ne_data=ne_data,
                    tspec_data=tspec_data,
                    nemodeltype=str(nemodeltype))  # [cm^-3]

    ##########################################################################
    #########################################################################
    ##########################################################################

    '''
    Maximum likelihood parameter estimation
    '''

    ml_results = fit_ml(ne_data, tspec_data, nemodel, clustermeta)

    '''
    MCMC estimation of mass profile model parameters
    '''

    # fit for the mass model and temperature profile model through MCMC
    samples, sampler = fit_mcmc(ne_data=ne_data,
                                tspec_data=tspec_data,
                                nemodel=nemodel,
                                clustermeta=clustermeta,
                                ml_results=ml_results,
                                Ncores=3,
                                Nwalkers=20,
                                Nsteps=20,
                                Nburnin=10)

    # calculate R500 and M(R500) for each step of MCMC chain
    samples_aux = calc_posterior_mcmc(samples=samples,
                                      nemodel=nemodel,
                                      clustermeta=clustermeta,
                                      Ncores=1)

    # combine all MCMC results
    mcmc_results = samples_results(samples=samples,
                                   samples_aux=samples_aux,
                                   clustermeta=clustermeta)

    for key in mcmc_results.keys():
        print 'MCMC: '+str(key)+' = '+str(mcmc_results[str(key)])

    ##########################################################################
    #########################################################################
    ##########################################################################

    '''
    Plot the results
    '''

    # Corner plot of marginalized posterior distribution of free params
    # from MCMC
    fig2 = plt_mcmc_freeparam(mcmc_results=mcmc_results,
                              samples=samples,
                              sampler=sampler,
                              tspec_data=tspec_data,
                              clustermeta=clustermeta)


    # Summary plot: density profile, temperature profile, mass profile
    fig3, ax1, ax2 = plt_summary(ne_data=ne_data,
                                 tspec_data=tspec_data,
                                 nemodel=nemodel,
                                 mcmc_results=mcmc_results,
                                 clustermeta=clustermeta)

    # add vikhlinin model to density plot
    xplot = np.logspace(np.log10(min(ne_data['radius'])),
                        np.log10(max(ne_data['radius'])), 1000)
    ax1.plot(xplot, vikhlinin_neprof(nemodel_vikhlinin, xplot), 'k')
    # plt.xlim(xmin=min(ne_data['radius']))

    # add viklinin model to temperature plot
    xplot = np.logspace(np.log10(min(tspec_data['radius'])),
                        np.log10(max(tspec_data['radius'])), 1000)
    ax2.plot(xplot, vikhlinin_tprof(tmodel_vikhlinin, xplot), 'k-')

    #plt.tight_layout()
    plt.show()
