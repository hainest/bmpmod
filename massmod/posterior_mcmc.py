import defaultparams.params as params

from joblib import Parallel, delayed

from mass_models import *
from gen import *

import scipy
import scipy.integrate

def calc_rdelta_p(row, nemodel, cluster):

    '''
    Radius corresponding to the input overdensity,
    i.e. M(Rdelta)/ Vol(Rdelta) = overdensity * rho_crit

    The total mass, DM mass, stellar mass of BCG, and ICM gas mass is then
    computed within this radius (rdelta).



    Args:
    -----
    c (float): mass concentration prameter of NFW profile
    rs (float) [kpc]: scale radius of NFW profile
    normsersic: normalization of stellar mass profile
    nemodel_bfp: parameters describing gas density profile

    Returns:
    --------
    rdelta: radius corresponding to overdensity
    mdelta: total mass wihin rdelta
    mdm: dark matter mass within rdelta
    mstars: stellar mass of central galaxy wihtn rdelta
    mgas: gas mass within rdelta

    '''


    c = row[0]
    rs = row[1]
    if cluster['count_mstar']==1:
        normsersic = row[2]
    elif cluster['count_mstar']==0:
        normsersic=0.
        mass_dev = 0.

    # rdelta(dm only first)
    rdelta_dm = c*rs
    # this is the radius where the density of dm interior is 500*cosmo.rho_crit
    # within this radius the total mass density will be >500*cosmo.rho_crit,
    # so need a larger radius to get to 500

    # calculate mass density at rdelta_dm
    mass_nfw = nfw_mass_model(rdelta_dm, c, rs, cluster['z'])  # [kg]

    if cluster['count_mstar']==1:
        mass_dev = sersic_mass_model(rdelta_dm, normsersic, cluster)*uconv.Msun  # [kg]

    intfunc = lambda x: mgas_intmodel(rdelta_dm, nemodel)
    mass_gas = scipy.integrate.quad(intfunc, 0, rdelta_dm)[0]*uconv.Msun  # [kg]

    mass_tot = mass_nfw+mass_dev+mass_gas

    rho_crit = calc_rhocrit(cluster['z'])
    ratio = (mass_tot/((4./3.)*np.pi*rdelta_dm**3.))/rho_crit


    # now let's step forward to find true rdelta(total mass)
    rdelta_tot = int(rdelta_dm)
    while ratio > cosmo.overdensity:

        rdelta_tot += 1

        mass_nfw = nfw_mass_model(rdelta_tot, c, rs, cluster['z'])  # [kg]

        if cluster['count_mstar']==1:
            mass_dev = sersic_mass_model(rdelta_tot, normsersic, cluster)*uconv.Msun  # [kg]

        intfunc = lambda x: mgas_intmodel(rdelta_tot, nemodel)
        mass_gas = scipy.integrate.quad(intfunc, 0, rdelta_tot)[0]*uconv.Msun  # [kg]

        mass_tot = mass_nfw+mass_dev+mass_gas

        rho_crit = calc_rhocrit(cluster['z'])
        ratio = (mass_tot/((4./3.)*np.pi*rdelta_tot**3.))/rho_crit

    return rdelta_tot, mass_tot/uconv.Msun, mass_nfw/uconv.Msun, mass_dev/uconv.Msun, mass_gas/uconv.Msun



def calc_posterior_mcmc(samples, nemodel, cluster, Ncores=params.Ncores):

    '''
    Calculate the radius corresponding to the given overdensity i.e. the radius
     corresponding to a mean overdensity that is some factor times the critical
     densiy at the redshift of the cluster. Within this radius, calculate the
     total mass, DM mass, stellar mass, gas mass.


    Args:
    -----
    samples (array): contains the posterior MCMC distribution
            col 0: c
            col 1: rs
            col 2: normsersic

    nemodel_bfp (array): contains parameters for best fitting model to the gas
        density profile


    Returns:
    --------
    samples_aux (array): contains output quantities based on the posterior
        MCMC distribution
            col 0: Rdelta
            col 1: Mdelta
            col 2: M(DM, delta)
            col 3: M(stars, delta)
            col 4: M(gas, delta)


    Notes:
    ------
    Utilizes JOBLIB for multi-threading. Number of cores as given in
        params file.
    JOBLIB: https://pythonhosted.org/joblib/

    '''

    samples_aux = Parallel(n_jobs=Ncores)(
        delayed(calc_rdelta_p)(row, nemodel, cluster) for row in samples)

    return np.array(samples_aux)




def samples_results(samples,samples_aux,cluster):


    if cluster['count_mstar']==1:
        c_mcmc, rs_mcmc, normsersic_mcmc = map(lambda v: (v[1], v[2]-v[1], v[1]-v[0]),zip(*np.percentile(samples, [16, 50, 84],axis=0)))
    elif cluster['count_mstar']==0:
        c_mcmc, rs_mcmc = map(lambda v: (v[1], v[2]-v[1], v[1]-v[0]),zip(*np.percentile(samples, [16, 50, 84],axis=0)))

    rdelta_mcmc, mdelta_mcmc, mdm_mcmc, mstars_mcmc, mgas_mcmc = map(lambda v: (v[1], v[2]-v[1], v[1]-v[0]),zip(*np.percentile(samples_aux, [16, 50, 84],axis=0)))

    print 'MCMC results'
    print 'MCMC: c=' ,c_mcmc
    print 'MCMC: rs=', rs_mcmc
    if cluster['count_mstar']==1:
        print 'MCMC: normsersic=', normsersic_mcmc


    mcmc_results={}
    mcmc_results['c']=c_mcmc
    mcmc_results['rs']=rs_mcmc
    mcmc_results['rdelta']=rdelta_mcmc
    mcmc_results['mdelta']=mdelta_mcmc
    mcmc_results['mdm']=mdm_mcmc
    mcmc_results['mgas']=mgas_mcmc
    
    if cluster['count_mstar']==1:
        mcmc_results['normsersic']=normsersic_mcmc
        mcmc_results['mstars']=mstars_mcmc
 
    return mcmc_results