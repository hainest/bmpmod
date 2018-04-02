import numpy as np

import scipy
import scipy.integrate
import scipy.optimize as op

import emcee

import defaultparams.params as params
import defaultparams.uconv as uconv

from joblib import Parallel, delayed

from mass_models import *
from density_models import *

import acor

import sys

import time

'''

Functions for backwards modelling the cluster mass profile by fitting the
observed temperature profile. Contains maximum likelihood and MCMC parameter
estimation routines.
'''


def intmodel(nemodel, rs, c, normsersic, r_arr, clustermeta):

    '''

    Model of the form \rho_gas * M_tot * r^-2; intended to be integrated when
    calculating Tmodel(r). \rho_gas is the model gas electron number density
    profile and M_tot is the total gravitating mass model.

    Args:
    -----
    nemodel (dictionary): dictionary storing the gas density profile model as
        output in fit_density()
    rs (float) [kpc]: scale radius of NFW profile
    c (float): concenration parameter of NFW profile
    normsersic (float): log(normalization [Msun kpc^-3]) of Sersic model for
        stellar mass profile of cluster central galaxy
    r_arr (array) [kpc]: radial position values of temperature profile
    clustermeta (dictionary): dictionary of cluster and analysis info produced
        by set_prof_data()

    Returns:
    --------
    Function to be integrated when solving for Tmodel(r)

    '''

    Mtot = nfw_mass_model(r_arr, c, rs, clustermeta['z'])
    if clustermeta['incl_mstar'] == 1:
        Mtot += sersic_mass_model(r_arr, normsersic, clustermeta)
    if clustermeta['incl_mgas'] == 1:
        Mtot += gas_mass_model(r_arr, nemodel)

    if nemodel['type'] == 'single_beta':
        return (betamodel(nemodel['parvals'], r_arr)
                * (1./uconv.Msun)*(uconv.cm_kpc**-3.)) \
            * (Mtot) \
            / (r_arr**2.)

    if nemodel['type'] == 'cusped_beta':
        return (cuspedbetamodel(nemodel['parvals'], r_arr)
                * (1./uconv.Msun)*(uconv.cm_kpc**-3.)) \
            * (Mtot) \
            / (r_arr**2.)

    if nemodel['type'] == 'double_beta':
        return (doublebetamodel(nemodel['parvals'], r_arr)
                * (1./uconv.Msun)*(uconv.cm_kpc**-3.)) \
            * (Mtot) \
            / (r_arr**2.)

    if nemodel['type'] == 'double_beta_tied':
        return (doublebetamodel_tied(nemodel['parvals'], r_arr)
                * (1./uconv.Msun)*(uconv.cm_kpc**-3.)) \
            * (Mtot) \
            / (r_arr**2.)


##############################################################################
##############################################################################
##############################################################################


def Tmodel_func(ne_data,
                tspec_data,
                nemodel,
                clustermeta,
                c, rs, normsersic=0):

    '''
    Calculates the non-parameteric model fit to the observed temperature
    profile. Tmodel(r) is calculated from Gastaldello+07 Eq. 2, which follows
    from solving the equation of hydrostatic equilibrium for temperature.


    Args:
    -----
    ne_data (astropy table): observed gas density profile
      in the form established by set_prof_data()
    tspec_data (astropy table): observed temperature profile
      in the form established by set_prof_data()

    nemodel (dictionary): dictionary storing the gas density profile model as
        output in fit_density()
    clustermeta (dictionary): dictionary of cluster and analysis info produced
        by set_prof_data()


    c (float): concenration parameter of NFW profile
    rs (float) [kpc]: scale radius of NFW profile
    normsersic (float): log(normalization [Msun kpc^-3]) of Sersic model for
        stellar mass profile of cluster central galaxy


    Returns:
    --------
    tfit_arr (array) [keV]: model temperature profile values. Position of
        model temperature profile is the same as the input tspec_data['radius']

    References:
    -----------
    Gastaldello, F., Buote, D. A., Humphrey, P. J., et al. 2007, ApJ, 669, 158
    '''

    # return Tmodel given param vals

    ne_ref = nemodel['nefit'][clustermeta['refindex']]
    tspec_ref = tspec_data['tspec'][clustermeta['refindex']]

    radius_ref = tspec_data['radius'][clustermeta['refindex']]

    tfit_arr = []  # to hold array of fit temperature
    # iterate over all radii values in profile
    for rr in range(0, len(tspec_data)):

        if rr == clustermeta['refindex']:
            tfit_arr.append(tspec_data['tspec'][rr])
            continue

        radius_selected = tspec_data['radius'][rr]
        ne_selected = nemodel['nefit'][rr]

        intfunc = lambda x: intmodel(nemodel,
                                     rs=rs,
                                     c=c,
                                     normsersic=normsersic,
                                     r_arr=x,
                                     clustermeta=clustermeta)

        finfac_t = ((params.mu*uconv.mA*uconv.G)
                    / (ne_selected*(uconv.cm_m**-3.)))  # [m6 kg-1 s-2]

        tfit_r = (tspec_ref*ne_ref/ne_selected) \
                 - (uconv.joule_kev*finfac_t*(uconv.Msun_kg**2.)
                    * (uconv.kpc_m**-4.)
                    * scipy.integrate.quad(intfunc, radius_ref,
                                           radius_selected)[0])
        # [kev]

        # print scipy.integrate.quad(intfunc,radius_ref,radius_selected)

        tfit_arr.append(tfit_r)

    return tfit_arr


##############################################################################
##############################################################################
##############################################################################

'''
Parameter estimation routines
'''


# define the log likelihood function, here assumes normal distribution
def lnlike(theta, x, y, yerr, ne_data, tspec_data, nemodel, clustermeta):
    '''
    The log(likelihood function) comparing observed and model temperature
        profile values.

    Args:
    -----
    theta (array): free-parameters of model
                   nominally of the form [c, rs, normsersic]
    x (?) [?]: positions of observed temperature profile
    y (array) [keV]: observed temperature profile temperature values
    yerr (array) [keV]: errors on temperauture profile values

    ne_data (astropy table): observed gas density profile
      in the form established by set_prof_data()
    tspec_data (astropy table): observed temperature profile
      in the form established by set_prof_data()

    nemodel (dictionary): dictionary storing the gas density profile model as
        output in fit_density()
    clustermeta (dictionary): dictionary of cluster and analysis info produced
        by set_prof_data()

    Returns:
    --------
    log of the gaussian likelood function

    '''

    if clustermeta['incl_mstar'] == 1:
        c, rs, normsersic = theta
    elif clustermeta['incl_mstar'] == 0:
        c, rs = theta
        normsersic = 0

    model = Tmodel_func(ne_data=ne_data,
                        tspec_data=tspec_data,
                        nemodel=nemodel,
                        clustermeta=clustermeta,
                        c=c,
                        rs=rs,
                        normsersic=normsersic)

    return -0.5*np.sum((((y-model)**2.)/(yerr**2.))
                       + np.log(2.*np.pi*(yerr**2.)))


# log-prior
def lnprior(theta,
            c_boundmin=params.c_boundmin,
            c_boundmax=params.c_boundmax,

            rs_boundmin=params.rs_boundmin,
            rs_boundmax=params.rs_boundmax,

            normsersic_boundmin=params.normsersic_boundmin,
            normsersic_boundmax=params.normsersic_boundmax):

    '''
    Ensures that free parameters do not go outside bounds

    Args:
    ----
    theta (array): current values of free-paramters; set by WHICH FUNCTION?
    '''
    if len(theta) == 3:
        c, rs, normsersic = theta

        if c_boundmin < c < c_boundmax \
           and rs_boundmin < rs < rs_boundmax \
           and normsersic_boundmin < normsersic < normsersic_boundmax:
            return 0.0
        return -np.inf

    elif len(theta) == 2:
        c, rs = theta

        if c_boundmin < c < c_boundmax and rs_boundmin < rs < rs_boundmax:
            return 0.0
        return -np.inf


# full-log probability function
def lnprob(theta, x, y, yerr, ne_data, tspec_data, nemodel, clustermeta):
    lp = lnprior(theta)
    if not np.isfinite(lp):
        return -np.inf
    return lp + lnlike(theta, x, y, yerr, ne_data, tspec_data, nemodel,
                       clustermeta)


def fit_ml(ne_data, tspec_data, nemodel, clustermeta,
           c_guess=params.c_guess,
           c_boundmin=params.c_boundmin,
           c_boundmax=params.c_boundmax,

           rs_guess=params.rs_guess,
           rs_boundmin=params.rs_boundmin,
           rs_boundmax=params.rs_boundmax,

           normsersic_guess=params.normsersic_guess,
           normsersic_boundmin=params.normsersic_boundmin,
           normsersic_boundmax=params.normsersic_boundmax):

    '''
    Perform maximum likelikhood parameter estimatation. Results can be used
    as initial guess for more MCMC parameter estimation analysis.

    Args:
    -----
    ne_data (astropy table): observed gas density profile
      in the form established by set_prof_data()
    tspec_data (astropy table): observed temperature profile
      in the form established by set_prof_data()

    nemodel (dictionary): dictionary storing the gas density profile model as
        output in fit_density()
    clustermeta (dictionary): dictionary of cluster and analysis info produced
        by set_prof_data()


    c_guess (float): starting value for estimation of c
    c_boundmin (float): lower boundary of parameter space that c will be searched over
    c_boundmax (float): upper boundary of parameter space that c will be searched over

    Returns:
    --------
    ml_results (array): results of Maximum-likelihood parameter estimation
       of the form [c_ml,rs_ml,normsersic_ml].


    '''

    nll = lambda *args: -lnlike(*args)

    if clustermeta['incl_mstar'] == 1:

        result = op.minimize(nll, [c_guess, rs_guess, normsersic_guess],
                             args=(tspec_data['radius'], tspec_data['tspec'],
                                   tspec_data['tspec_err'], ne_data,
                                   tspec_data, nemodel, clustermeta),
                             bounds=((c_boundmin, c_boundmax),
                                     (rs_boundmin, rs_boundmax),
                                     (normsersic_boundmin,
                                      normsersic_boundmax)))

        c_ml, rs_ml, normsersic_ml = result["x"]
        print 'MLE results'
        print 'MLE: c=', c_ml
        print 'MLE: rs=', rs_ml
        print 'MLE: normsersic=', normsersic_ml

        return [c_ml, rs_ml, normsersic_ml]

    elif clustermeta['incl_mstar'] == 0:
        result = op.minimize(nll, [c_guess, rs_guess],
                             args=(tspec_data['radius'], tspec_data['tspec'],
                                   tspec_data['tspec_err'], ne_data,
                                   tspec_data, nemodel, clustermeta),
                             bounds=((c_boundmin, c_boundmax),
                                     (rs_boundmin, rs_boundmax)))

        c_ml, rs_ml = result["x"]
        print 'MLE results'
        print 'MLE: c=', c_ml
        print 'MLE: rs=', rs_ml

        return [c_ml, rs_ml]


def fit_mcmc(ne_data, tspec_data, nemodel, clustermeta, ml_results,
             Ncores=params.Ncores,
             Nwalkers=params.Nwalkers,
             Nsteps=params.Nsteps,
             Nburnin=params.Nburnin):

    '''
    Perform a MCMC analysis on the free parameters of the cluster total
    gravitating mass model, utilizing the ensemble sampler of emcee.

    Args:
    -----

    ne_data (astropy table): observed gas density profile
      in the form established by set_prof_data()
    tspec_data (astropy table): observed temperature profile
      in the form established by set_prof_data()

    nemodel (dictionary): dictionary storing the gas density profile model as
        output in fit_density()
    clustermeta (dictionary): dictionary of cluster and analysis info produced
        by set_prof_data()

    ml_results (array): maximum-likelihood paramter estimation for mass model
        free params of the form [c_ml, rs_ml, normsersic_ml]

    Ncores (int): number of cores overwhich to run MCMC analysis
    Nwalkers (int): number of MCMC ensemble walkers
    Nsteps (int): number of steps each walker takes
    Nburnin (int): number of steps considered to be a part of the burn-in
        period of the chain; these burn-in steps will be excluded from the
        final MCMC parameter estiamtion

    Returns:
    --------
    samples (array): MCMC samples of posterior distribution; of the form:
                col 1: c
                col 2: rs
                col 3: log(normsersic)
            NB: length of samples array set by Nwalkers * Nsteps

    References:
    -----------
    EMCEE

    '''

    # initialize walkers - result comes from ML fit before

    if clustermeta['incl_mstar'] == 1:
        ndim, nwalkers = 3, Nwalkers
    elif clustermeta['incl_mstar'] == 0:
        ndim, nwalkers = 2, Nwalkers

    pos = [ml_results + 1e-4*np.random.randn(ndim) for i in range(nwalkers)]

    # sampler
    sampler = emcee.EnsembleSampler(nwalkers, ndim, lnprob,
                                    args=(tspec_data['radius'],
                                          tspec_data['tspec'],
                                          tspec_data['tspec_err'],
                                          ne_data,
                                          tspec_data, nemodel, clustermeta),
                                    threads=Ncores)
    # WHY ARE THE ARGS THE WAY THEY ARE???

    # # run ensemble sampler for given number of steps
    # start=time.time()
    # sampler.run_mcmc(pos, Nsteps)
    # end=time.time()
    # print end-start

    for i, result in enumerate(sampler.sample(pos, iterations=Nsteps)):
        if 100.*((float(i+1.))/Nsteps) % 10 == 0:
            print 'MCMC progress: '+"{0:5.1%}".format(float(i+1.) / Nsteps)

    samples = sampler.chain[:, Nburnin:, :].reshape((-1, ndim))
    # length of samples = walkers*steps

    # check acceptance rate: goal between 0.2-0.5
    # print 'acceptance rate of walkers:'
    # print sampler.acceptance_fraction

    # check autocorrelation time
    try:
        print 'autocorrelation time:', sampler.acor
    except:
        print 'autocorrelation time cannot be calculated'
    print ''

    # print emcee.autocorr.integrated_time()

    return samples, sampler
