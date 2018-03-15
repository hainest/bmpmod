import corner

import matplotlib
import matplotlib.pyplot as plt

import numpy as np

import massmod_func as massmod
import defaultparams.uconv as uconv
import defaultparams.cosmology as cosmo

import scipy
import scipy.integrate


def seplog(n):
    '''
    For a float of the form n=fac*10**power, seperates out "fac" and "power". Used with the intent of making nice looking annotations on a plot.
    '''
    power=int(np.floor(np.log10(n)))
    fac=n/(10.**power)
    return [fac,power]


'''
Plotting
'''

def plt_mcmc_freeparam(mcmc_results,samples,tspec_data,cluster):

    '''
    Make a corner plot from the MCMC posterior distribution of free-parameter values.

    Args:
    -----
    mcmc_results (array): 
    samples (array): posterior MCMC distribution of free-param vals
    tspec_data (astropy table): table containg profile information about temperature

    Results:
    --------
    fig1 (plot)
    '''


    fig1 = corner.corner(samples, labels=["$c$", "$R_s$", r"$\rho_{\star,0,\mathrm{Sersic}}$"])


    plt.annotate('$r_{\mathrm{ref}}$='+str(int(tspec_data['radius'][cluster['refindex']]))+' kpc',(0.7,0.9),xycoords='figure fraction')

    plt.annotate(r'$c = '+str(np.round(mcmc_results['c'][0],decimals=1))+'_{-'+str(np.round(mcmc_results['c'][2],decimals=2))+'}^{+'+str(np.round(mcmc_results['c'][1],decimals=2))+'}$',(0.7,0.8),xycoords='figure fraction')
    plt.annotate(r'$R_{s} = '+str(np.round(mcmc_results['rs'][0],decimals=1))+'_{-'+str(np.round(mcmc_results['rs'][2],decimals=1))+'}^{+'+str(np.round(mcmc_results['rs'][1],decimals=1))+'}$ kpc',(0.7,0.75),xycoords='figure fraction')
    plt.annotate(r'$log(\rho_{\star,0,\mathrm{Sersic}} [M_{\odot}]) = '+str(np.round(mcmc_results['normsersic'][0],decimals=1))+'_{-'+str(np.round(mcmc_results['normsersic'][2],decimals=2))+'}^{+'+str(np.round(mcmc_results['normsersic'][1],decimals=2))+'}$',(0.7,0.7),xycoords='figure fraction')

    return fig1



###########################################################################
###########################################################################
###########################################################################

def plt_summary(ne_data,tspec_data,nemodel,mcmc_results,cluster):

    '''
    Make a summary plot containing the gas density profile, temperature profile, and mass profile. Annotations for all relevant calculated quantities.

    Args:
    -----
    ne_data (astropy table): table containing profile information about gas denisty
    tspec_data (astropy table): table containg profile information about temperature    
    nemodel (dictionary): info about ne profile fit including param values and errors
    mcmc_results (dictionary): values and errors of free-params of MCMC as well as quantites calculated from the posterior MCMC distribution



    Results:
    --------
    fig2 (plot):
         subfig 1: plot of observed gas density profile and fitted gas density profile
         subfig 2: plot of observed temperature profile and model temperature profile
         subfig 3: mass profile of cluster - includes total and components of DM, stars, gas
    '''



    fig2=plt.figure(2,(8,8))
    plt.figure(2)

    matplotlib.rcParams['font.size']=10
    matplotlib.rcParams['axes.labelsize']=12
    matplotlib.rcParams['legend.fontsize']=10
    matplotlib.rcParams['mathtext.default']='regular'
    matplotlib.rcParams['mathtext.fontset']='stixsans'


    '''
    gas density
    '''
    ax=fig2.add_subplot(2,2,1) 

    plt.loglog(ne_data['radius'],ne_data['ne'],'o',color='#707070',markersize=2)
    
    plt.errorbar(ne_data['radius'],ne_data['ne'],xerr=[ne_data['radius_lowerbound'],ne_data['radius_upperbound']],yerr=ne_data['ne_err'],linestyle='none',color='#707070')

    plt.xlim(xmin=1)
    ax.set_xscale("log", nonposy='clip')
    ax.set_yscale("log", nonposx='clip')

    plt.xlabel('r [kpc]')
    plt.ylabel('$n_{e}$ [cm$^{-3}$]')



    plt_densityprof(nemodel,annotations=1)

    '''
    final kT profile with c, rs
    '''

    tfit_arr=massmod.Tmodel_func(mcmc_results['c'][0], mcmc_results['rs'][0], mcmc_results['normsersic'][0], ne_data, tspec_data, nemodel,cluster)



    ax=fig2.add_subplot(2,2,2) 
    
    plt.semilogx(tspec_data['radius'],tspec_data['tspec'],'bo')

    plt.errorbar(tspec_data['radius'],tspec_data['tspec'],xerr=[tspec_data['radius_lowerbound'],tspec_data['radius_upperbound']],yerr=[tspec_data['tspec_lowerbound'],tspec_data['tspec_upperbound']],linestyle='none',color='b')
    plt.xlabel('r [kpc]')
    plt.ylabel('kT [keV]')

    plt.annotate('$r_{\mathrm{ref}}$='+str(int(tspec_data['radius'][cluster['refindex']]))+' kpc',(0.05,0.9),xycoords='axes fraction')

    plt.ylim(0,4)
    plt.xlim(xmin=1)

    plt.semilogx(tspec_data['radius'],np.array(tfit_arr),'r-')


    ##########################################################################



    '''
    OVERDENSITY RADIUS: MASS PROFILE
    '''

    ax=fig2.add_subplot(2,2,3) 

    xplot=np.logspace(np.log10(1.),np.log10(900.),100)

    mass_nfw=massmod.nfw_mass_model(xplot,mcmc_results['c'][0],mcmc_results['rs'][0],cluster['z'])/uconv.Msun
    mass_dev=massmod.sersic_mass_model(xplot,mcmc_results['normsersic'][0],cluster) #Msun

    intfunc = lambda x: massmod.mgas_intmodel(x,nemodel)
    mass_gas=[]
    for xx in xplot:
        mass_gas.append(scipy.integrate.quad(intfunc,0,xx)[0]) 

    mass_tot=mass_nfw+mass_dev+mass_gas



    plt.loglog(xplot,mass_tot,'r-',label='M$_{\mathrm{tot}}$')
    plt.loglog(xplot,mass_nfw,'b-',label='M$_{\mathrm{DM}}$')
    plt.loglog(xplot,mass_dev,'g-',label='M$_{\star}$')
    plt.loglog(xplot,mass_gas,'y-',label='M$_{\mathrm{gas}}$')

    handles,labels=ax.get_legend_handles_labels()
    plt.legend(handles,labels,loc=2)
    

    plt.xlim(xmin=2)
    plt.ylim(ymin=6.*10**10.,ymax=10**14.) #to match g07

    plt.xlabel('r [kpc]')
    plt.ylabel('mass [$M_{\odot}$]')




    #add final annotations for fit
    c_err=(np.abs(mcmc_results['c'][1])+np.abs(mcmc_results['c'][2]))/2.
    rs_err=(np.abs(mcmc_results['rs'][1])+np.abs(mcmc_results['rs'][2]))/2.
    normsersic_err=(np.abs(mcmc_results['normsersic'][1])+np.abs(mcmc_results['normsersic'][2]))/2.

    plt.annotate(r'$c_{'+str(int(cosmo.overdensity))+'} = '+str(np.round(mcmc_results['c'][0],decimals=1))+'_{-'+str(np.round(mcmc_results['c'][2],decimals=2))+'}^{+'+str(np.round(mcmc_results['c'][1],decimals=2))+'}$',(0.55,0.45),xycoords='figure fraction')
    plt.annotate(r'$R_{s} = '+str(np.round(mcmc_results['rs'][0],decimals=1))+'_{-'+str(np.round(mcmc_results['rs'][2],decimals=1))+'}^{+'+str(np.round(mcmc_results['rs'][1],decimals=1))+'}$ kpc',(0.55,0.4),xycoords='figure fraction')
    plt.annotate(r'$log(\rho_{\star,0,\mathrm{Sersic}} [M_{\odot}]) = '+str(np.round(mcmc_results['normsersic'][0],decimals=1))+'_{-'+str(np.round(mcmc_results['normsersic'][2],decimals=2))+'}^{+'+str(np.round(mcmc_results['normsersic'][1],decimals=2))+'}$',(0.55,0.35),xycoords='figure fraction')


    plt.annotate(r'$R_{eff}=$'+str(cluster['bcg_re'])+' kpc',(0.8,0.45),xycoords='figure fraction')
    plt.annotate(r'$n_{\mathrm{Sersic}}$='+str(cluster['bcg_sersic_n']),(0.8,0.4),xycoords='figure fraction')



    plt.annotate('$R_{'+str(int(cosmo.overdensity))+'}='+str(int(np.round(mcmc_results['rdelta'][0],decimals=0)))+'_{-'+str(int(np.round(mcmc_results['rdelta'][2],decimals=0)))+'}^{+'+str(int(np.round(mcmc_results['rdelta'][1],decimals=0)))+'}$ kpc',(0.55,0.25),xycoords='figure fraction')


    plt.annotate('$M_{'+str(int(cosmo.overdensity))+'}='+str(np.round(seplog(mcmc_results['mdelta'][0])[0],decimals=2))+'_{-'+str(np.round(mcmc_results['mdelta'][2]*10**-seplog(mcmc_results['mdelta'][0])[1],decimals=2))+'}^{+'+str(np.round(mcmc_results['mdelta'][1]*10**-seplog(mcmc_results['mdelta'][0])[1],decimals=2))+'} \ 10^{'+str(seplog(mcmc_results['mdelta'][0])[1])+'} \ M_{\odot}$',(0.55,0.2),xycoords='figure fraction')


    plt.annotate('$M_{DM}(R_{'+str(int(cosmo.overdensity))+'})='+str(np.round(seplog(mcmc_results['mdm'][0])[0],decimals=2))+'_{-'+str(np.round(mcmc_results['mdm'][2]*10**-seplog(mcmc_results['mdm'][0])[1],decimals=2))+'}^{+'+str(np.round(mcmc_results['mdm'][1]*10**-seplog(mcmc_results['mdm'][0])[1],decimals=2))+'} \ 10^{'+str(seplog(mcmc_results['mdm'][0])[1])+'} \ M_{\odot}$',(0.55,0.15),xycoords='figure fraction')



    plt.annotate('$M_{\star}(R_{'+str(int(cosmo.overdensity))+'})='+str(np.round(seplog(mcmc_results['mstars'][0])[0],decimals=2))+'_{-'+str(np.round(mcmc_results['mstars'][2]*10**-seplog(mcmc_results['mstars'][0])[1],decimals=2))+'}^{+'+str(np.round(mcmc_results['mstars'][1]*10**-seplog(mcmc_results['mstars'][0])[1],decimals=2))+'} \ 10^{'+str(seplog(mcmc_results['mstars'][0])[1])+'} \ M_{\odot}$',(0.55,0.1),xycoords='figure fraction')

    plt.annotate('$M_{gas}(R_{'+str(int(cosmo.overdensity))+'})='+str(np.round(seplog(mcmc_results['mgas'][0])[0],decimals=2))+'_{-'+str(np.round(mcmc_results['mgas'][2]*10**-seplog(mcmc_results['mgas'][0])[1],decimals=2))+'}^{+'+str(np.round(mcmc_results['mgas'][1]*10**-seplog(mcmc_results['mgas'][0])[1],decimals=2))+'} \ 10^{'+str(seplog(mcmc_results['mgas'][0])[1])+'} \ M_{\odot}$',(0.55,0.05),xycoords='figure fraction')


    return fig2



#############################################################################
#############################################################################
#############################################################################


def plt_densityprof(nemodel,annotations):


    '''
    Helper function to plot the best-fitting model of the gas density profile.

    Args:
    -----   
    nemodel (dictionary): info about ne profile fit including param values and errors


    Results:
    --------
    plt (plot): a plot with annotations of the best-fitting model of the gas density profile.

    '''



    #add model to plot
    rplot=np.linspace(0,1000.,1000)

    
    if nemodel['type'] == 'double_beta':

        plt.plot(rplot,massmod.doublebetamodel(nemodel['parvals'],rplot),'r')

        if annotations==1:
            plt.annotate(r'$n_{e,0,1}='+str(np.round(nemodel['parvals'][0],decimals=3))+'_{'+str(np.round(nemodel['parmins'][0],decimals=3))+'}^{+'+str(np.round(nemodel['parmaxes'][0],decimals=3))+'}$ cm$^{-3}$',(0.02,0.4),xycoords='axes fraction')
            plt.annotate('$r_{c,1}='+str(np.round(nemodel['parvals'][1],decimals=2))+'_{'+str(np.round(nemodel['parmins'][1],decimals=2))+'}^{+'+str(np.round(nemodel['parmaxes'][1],decimals=2))+'}$ kpc',(0.02,0.35),xycoords='axes fraction')
            plt.annotate(r'$\beta_1='+str(np.round(nemodel['parvals'][2],decimals=2))+'_{'+str(np.round(nemodel['parmins'][2],decimals=2))+'}^{+'+str(np.round(nemodel['parmaxes'][2],decimals=2))+'}$',(0.02,0.3),xycoords='axes fraction')

            plt.annotate(r'$n_{e,0,2}='+str(np.round(nemodel['parvals'][3],decimals=3))+'_{'+str(np.round(nemodel['parmins'][3],decimals=3))+'}^{+'+str(np.round(nemodel['parmaxes'][3],decimals=3))+'}$ cm$^{-3}$',(0.02,0.25),xycoords='axes fraction')
            plt.annotate('$r_{c,2}='+str(np.round(nemodel['parvals'][4],decimals=2))+'_{'+str(np.round(nemodel['parmins'][4],decimals=2))+'}^{+'+str(np.round(nemodel['parmaxes'][4],decimals=2))+'}$ kpc',(0.02,0.2),xycoords='axes fraction')
            plt.annotate(r'$\beta_2='+str(np.round(nemodel['parvals'][5],decimals=2))+'_{'+str(np.round(nemodel['parmins'][5],decimals=2))+'}^{+'+str(np.round(nemodel['parmaxes'][5],decimals=2))+'}$',(0.02,0.15),xycoords='axes fraction')


            plt.annotate('$\chi^2_r$='+str(np.round(nemodel['rchisq'],decimals=2)),(0.02,0.05),xycoords='axes fraction')


    if nemodel['type'] == 'double_beta_tied':

        plt.plot(rplot,massmod.doublebetamodel_tied(nemodel['parvals'],rplot),'r')

        if annotations==1:
            plt.annotate(r'$n_{e,0,1}='+str(np.round(nemodel['parvals'][0],decimals=3))+'_{'+str(np.round(nemodel['parmins'][0],decimals=3))+'}^{+'+str(np.round(nemodel['parmaxes'][0],decimals=3))+'}$ cm$^{-3}$',(0.02,0.4),xycoords='axes fraction')
            plt.annotate('$r_{c,1}='+str(np.round(nemodel['parvals'][1],decimals=2))+'_{'+str(np.round(nemodel['parmins'][1],decimals=2))+'}^{+'+str(np.round(nemodel['parmaxes'][1],decimals=2))+'}$ kpc',(0.02,0.35),xycoords='axes fraction')
            plt.annotate(r'$\beta_1='+str(np.round(nemodel['parvals'][2],decimals=2))+'_{'+str(np.round(nemodel['parmins'][2],decimals=2))+'}^{+'+str(np.round(nemodel['parmaxes'][2],decimals=2))+'}$',(0.02,0.3),xycoords='axes fraction')
        
            plt.annotate(r'$n_{e,0,2}='+str(np.round(nemodel['parvals'][3],decimals=3))+'_{'+str(np.round(nemodel['parmins'][3],decimals=3))+'}^{+'+str(np.round(nemodel['parmaxes'][3],decimals=3))+'}$ cm$^{-3}$',(0.02,0.25),xycoords='axes fraction')
            plt.annotate('$r_{c,2}='+str(np.round(nemodel['parvals'][4],decimals=2))+'_{'+str(np.round(nemodel['parmins'][4],decimals=2))+'}^{+'+str(np.round(nemodel['parmaxes'][4],decimals=2))+'}$ kpc',(0.02,0.2),xycoords='axes fraction')
            plt.annotate(r'$\beta_2=\beta_1$',(0.02,0.15),xycoords='axes fraction')
        

            plt.annotate('$\chi^2_r$='+str(np.round(nemodel['rchisq'],decimals=2)),(0.02,0.05),xycoords='axes fraction')


    

    if nemodel['type'] == 'single_beta':

        plt.plot(rplot,massmod.betamodel(nemodel['parvals'],rplot),'r')

        if annotations==1:
            plt.annotate(r'$n_{e,0}='+str(np.round(nemodel['parvals'][0],decimals=3))+'_{'+str(np.round(nemodel['parmins'][0],decimals=3))+'}^{+'+str(np.round(nemodel['parmaxes'][0],decimals=3))+'}$ cm$^{-3}$',(0.02,0.25),xycoords='axes fraction')
            plt.annotate('$r_{c}='+str(np.round(nemodel['parvals'][1],decimals=2))+'_{'+str(np.round(nemodel['parmins'][1],decimals=2))+'}^{+'+str(np.round(nemodel['parmaxes'][1],decimals=2))+'}$ kpc',(0.02,0.2),xycoords='axes fraction')
            plt.annotate(r'$\beta='+str(np.round(nemodel['parvals'][2],decimals=2))+'_{'+str(np.round(nemodel['parmins'][2],decimals=2))+'}^{+'+str(np.round(nemodel['parmaxes'][2],decimals=2))+'}$',(0.02,0.15),xycoords='axes fraction')


            plt.annotate('$\chi^2_r$='+str(np.round(nemodel['rchisq'],decimals=2)),(0.02,0.05),xycoords='axes fraction')


    if nemodel['type'] == 'cusped_beta':

        plt.plot(rplot,massmod.cuspedbetamodel(nemodel['parvals'],rplot),'r')

        if annotations==1:
            plt.annotate(r'$n_{e,0}='+str(np.round(nemodel['parvals'][0],decimals=3))+'_{'+str(np.round(nemodel['parmins'][0],decimals=3))+'}^{+'+str(np.round(nemodel['parmaxes'][0],decimals=3))+'}$ cm$^{-3}$',(0.02,0.3),xycoords='axes fraction')
            plt.annotate('$r_{c}='+str(np.round(nemodel['parvals'][1],decimals=2))+'_{'+str(np.round(nemodel['parmins'][1],decimals=2))+'}^{+'+str(np.round(nemodel['parmaxes'][1],decimals=2))+'}$ kpc',(0.02,0.25),xycoords='axes fraction')
            plt.annotate(r'$\beta='+str(np.round(nemodel['parvals'][2],decimals=2))+'_{'+str(np.round(nemodel['parmins'][2],decimals=2))+'}^{+'+str(np.round(nemodel['parmaxes'][2],decimals=2))+'}$',(0.02,0.2),xycoords='axes fraction')
            plt.annotate(r'$\epsilon='+str(np.round(nemodel['parvals'][3],decimals=2))+'_{'+str(np.round(nemodel['parmins'][3],decimals=2))+'}^{+'+str(np.round(nemodel['parmaxes'][3],decimals=2))+'}$',(0.02,0.15),xycoords='axes fraction')

            plt.annotate('$\chi^2_r$='+str(np.round(nemodel['rchisq'],decimals=2)),(0.02,0.05),xycoords='axes fraction')


    return plt





###########################################################################
###########################################################################
###########################################################################

def plt_summary_nice(ne_data,tspec_data,nemodel,mcmc_results,cluster):

    '''
    Make a summary plot containing the gas density profile, temperature profile, and mass profile. Annotations for all relevant calculated quantities.

    Nice version to go in paper.

    Args:
    -----
    ne_data (astropy table): table containing profile information about gas denisty
    tspec_data (astropy table): table containg profile information about temperature    
    nemodel (dictionary): info about ne profile fit including param values and errors
    mcmc_results (dictionary): values and errors of free-params of MCMC as well as quantites calculated from the posterior MCMC distribution



    Results:
    --------
    fig3 (plot):
         subfig 1: plot of observed gas density profile and fitted gas density profile
         subfig 2: plot of observed temperature profile and model temperature profile
         subfig 3: mass profile of cluster - includes total and components of DM, stars, gas
    '''



    fig3=plt.figure(3,(12,4))
    plt.figure(3)

    matplotlib.rcParams['font.size']=10
    matplotlib.rcParams['axes.labelsize']=12
    matplotlib.rcParams['legend.fontsize']=10
    matplotlib.rcParams['mathtext.default']='regular'
    matplotlib.rcParams['mathtext.fontset']='stixsans'


    '''
    gas density
    '''
    ax=fig3.add_subplot(1,3,1) 

    plt.loglog(ne_data['radius'],ne_data['ne'],'o',color='#707070',markersize=2)
    
    plt.errorbar(ne_data['radius'],ne_data['ne'],xerr=[ne_data['radius_lowerbound'],ne_data['radius_upperbound']],yerr=ne_data['ne_err'],linestyle='none',color='#707070')

    plt.xlim(xmin=1)
    ax.set_xscale("log", nonposy='clip')
    ax.set_yscale("log", nonposx='clip')

    plt.xlabel('r [kpc]')
    plt.ylabel('$n_{e}$ [cm$^{-3}$]')



    plt_densityprof(nemodel,annotations=0)

    '''
    final kT profile with c, rs
    '''

    tfit_arr=massmod.Tmodel_func(mcmc_results['c'][0], mcmc_results['rs'][0], mcmc_results['normsersic'][0], ne_data, tspec_data, nemodel,cluster)



    ax=fig3.add_subplot(1,3,2) 
    
    plt.semilogx(tspec_data['radius'],tspec_data['tspec'],'bo')

    plt.errorbar(tspec_data['radius'],tspec_data['tspec'],xerr=[tspec_data['radius_lowerbound'],tspec_data['radius_upperbound']],yerr=[tspec_data['tspec_lowerbound'],tspec_data['tspec_upperbound']],linestyle='none',color='b')
    plt.xlabel('r [kpc]')
    plt.ylabel('kT [keV]')


    plt.ylim(0,4)
    plt.xlim(xmin=1)

    plt.semilogx(tspec_data['radius'],np.array(tfit_arr),'r-')


    ##########################################################################



    '''
    OVERDENSITY RADIUS: MASS PROFILE
    '''

    ax=fig3.add_subplot(1,3,3) 

    xplot=np.logspace(np.log10(1.),np.log10(900.),100)

    mass_nfw=massmod.nfw_mass_model(xplot,mcmc_results['c'][0],mcmc_results['rs'][0],cluster['z'])/uconv.Msun
    mass_dev=massmod.sersic_mass_model(xplot,mcmc_results['normsersic'][0],cluster) #Msun

    intfunc = lambda x: massmod.mgas_intmodel(x,nemodel)
    mass_gas=[]
    for xx in xplot:
        mass_gas.append(scipy.integrate.quad(intfunc,0,xx)[0]) 

    mass_tot=mass_nfw+mass_dev+mass_gas



    plt.loglog(xplot,mass_tot,'r-',label='M$_{\mathrm{tot}}$')
    plt.loglog(xplot,mass_nfw,'b-',label='M$_{\mathrm{DM}}$')
    plt.loglog(xplot,mass_dev,'g-',label='M$_{\star}$')
    plt.loglog(xplot,mass_gas,'y-',label='M$_{\mathrm{gas}}$')

    handles,labels=ax.get_legend_handles_labels()
    plt.legend(handles,labels,loc=2)
    

    plt.xlim(xmin=2)
    plt.ylim(ymin=6.*10**10.,ymax=10**14.) #to match g07

    plt.xlabel('r [kpc]')
    plt.ylabel('mass [$M_{\odot}$]')




    #add final annotations for fit
    c_err=(np.abs(mcmc_results['c'][1])+np.abs(mcmc_results['c'][2]))/2.
    rs_err=(np.abs(mcmc_results['rs'][1])+np.abs(mcmc_results['rs'][2]))/2.
    normsersic_err=(np.abs(mcmc_results['normsersic'][1])+np.abs(mcmc_results['normsersic'][2]))/2.




    return fig3

