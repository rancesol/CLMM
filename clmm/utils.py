"""General utility functions that are used in multiple modules"""
import numpy as np
from scipy.stats import binned_statistic
from scipy.special import gamma, gammainc
from astropy import units as u
from .constants import Constants as const
from scipy.integrate import quad



def compute_nfw_boost(rvals, rs=1000, b0=0.1) :
    """ Given a list of rvals, and optional rs and b0, return the corresponding boost factor at each rval

    Parameters
    ----------
    rvals : array_like
        radii
    rs : float (optional)
        scale radius for NFW in same units as rvals (default 2000 kpc)
    b0 : float (optional)

    Returns
    -------
    boost_factors : array_like

    """

    x = rvals/rs

    def _calc_finternal(x) :

        radicand = x**2-1

        finternal = -1j *  np.log( (1 + np.lib.scimath.sqrt(radicand)*1j) / (1 - np.lib.scimath.sqrt(radicand)*1j) ) / ( 2 * np.lib.scimath.sqrt(radicand) )

        return np.nan_to_num(finternal, copy=False, nan=1.0).real

    return 1. + b0 * (1 - _calc_finternal(x)) / (x**2 - 1)
        


def compute_powerlaw_boost(rvals, rs=1000, b0=0.1, alpha=-1.0) :
    """  Given a list of rvals, and optional rs and b0, and alpha, return the corresponding boost factor at each rval

    Parameters
    ----------
    rvals : array_like
        radii
    rs : float (optional)
        scale radius for NFW in same units as rvals (default 2000 kpc)
    b0 : float (optional)
    alpha : float (optional)
        exponent from Melchior+16

    Returns
    -------
    boost_factors : array_like

    """

    x = rvals/rs

    return 1. + b0 * (x)**alpha

    

boost_models = {'nfw_boost': compute_nfw_boost,
                'powerlaw_boost': compute_powerlaw_boost}

def correct_sigma_with_boost_values(rvals, sigma_vals, boost_factors):
    """ Given a boost model and sigma profile, compute corrected sigma

    Parameters
    ----------
    rvals : array_like
        radii
    sigma_vals : array_like
        uncorrected sigma with cluster member dilution
    boost_factors : array_like
        Boost values pre-computed

    Returns
    -------
    sigma_corrected : array_like
        correted radial profile
    """

    sigma_corrected = sigma_vals / boost_factors
    return sigma_corrected


def correct_sigma_with_boost_model(rvals, sigma_vals, boost_model='nfw_boost', **boost_model_kw):
    """ Given a boost model and sigma profile, compute corrected sigma

    Parameters
    ----------
    rvals : array_like
        radii
    sigma_vals : array_like
        uncorrected sigma with cluster member dilution
    boost_model : str, optional
        Boost model to use for correcting sigma
            `nfw_boost` - NFW profile model (Default)
            `powerlaw_boost` - Powerlaw profile
    

    Returns
    -------
    sigma_corrected : array_like
        correted radial profile
    """
    boost_model_func = boost_models[boost_model]
    boost_factors = boost_model_func(rvals, **boost_model_kw)

    sigma_corrected = sigma_vals / boost_factors
    return sigma_corrected

def compute_radial_averages(xvals, yvals, xbins, yerr=None, error_model='ste', weights=None):
    """ Given a list of xvals, yvals and bins, sort into bins. If xvals or yvals
    contain non-finite values, these are filtered.

    Parameters
    ----------
    xvals : array_like
        Values to be binned
    yvals : array_like
        Values to compute statistics on
    xbins: array_like
        Bin edges to sort into
    yerr : array_like, None
        Errors of component y
    error_model : str, optional
        Statistical error model to use for y uncertainties. (letter case independent)

            * `ste` - Standard error [=std/sqrt(n) in unweighted computation] (Default).
            * `std` - Standard deviation.

    weights: array_like, None
        Weights for averages.


    Returns
    -------
    mean_x : array_like
        Mean x value in each bin
    mean_y : array_like
        Mean y value in each bin
    err_y: array_like
        Error on the mean y value in each bin. Specified by error_model
    num_objects : array_like
        Number of objects in each bin
    binnumber: 1-D ndarray of ints
        Indices of the bins (corresponding to `xbins`) in which each value
        of `xvals` belongs.  Same length as `yvals`.  A binnumber of `i` means the
        corresponding value is between (xbins[i-1], xbins[i]).
    """
    # make case independent
    error_model = error_model.lower()
    # binned_statics throus an error in case of non-finite values, so filtering those out
    filt = np.isfinite(xvals)*np.isfinite(yvals)
    x, y = np.array(xvals)[filt], np.array(yvals)[filt]
    # normalize weights (and computers binnumber)
    wts = np.ones(x.size) if weights is None else np.array(weights, dtype=float)[filt]
    wts_sum, binnumber = binned_statistic(x, wts, statistic='sum', bins=xbins)[:3:2]
    objs_in_bins = (binnumber>0)*(binnumber<=wts_sum.size) # mask for binnumber in range
    wts[objs_in_bins] *= 1./wts_sum[binnumber[objs_in_bins]-1] # norm weights in each bin
    weighted_bin_stat = lambda vals: binned_statistic(x, vals*wts, statistic='sum', bins=xbins)[0]
    # means
    mean_x = weighted_bin_stat(x)
    mean_y = weighted_bin_stat(y)
    # errors
    data_yerr2 = 0 if yerr is None else weighted_bin_stat(np.array(yerr)[filt]**2*wts)
    stat_yerr2 = weighted_bin_stat(y**2)-mean_y**2
    if error_model == 'ste':
        stat_yerr2 *= weighted_bin_stat(wts) # sum(wts^2)=1/n for not weighted
    elif error_model != 'std':
        raise ValueError(f"{error_model} not supported err model for binned stats")
    err_y = np.sqrt(stat_yerr2+data_yerr2)
    # number of objects
    num_objects = np.histogram(x, xbins)[0]
    return mean_x, mean_y, err_y, num_objects, binnumber


def make_bins(rmin, rmax, nbins=10, method='evenwidth', source_seps=None):
    """ Define bin edges

    Parameters
    ----------
    rmin : float
        Minimum bin edges wanted
    rmax : float
        Maximum bin edges wanted
    nbins : float
        Number of bins you want to create, default to 10.
    method : str, optional
        Binning method to use (letter case independent):

            * `evenwidth` - Default, evenly spaced bins between rmin and rmax
            * `evenlog10width` - Logspaced bins with even width in log10 between rmin and rmax
            * `equaloccupation` - Bins with equal occupation numbers

    source_seps : array_like
        Radial distance of source separations

    Returns
    -------
    binedges: array_like, float
        n_bins+1 dimensional array that defines bin edges
    """
    # make case independent
    method = method.lower()
    # Check consistency
    if (rmin > rmax) or (rmin < 0.0) or (rmax < 0.0):
        raise ValueError(f"Invalid bin endpoints in make_bins, {rmin} {rmax}")
    if (nbins <= 0) or not isinstance(nbins, int):
        raise ValueError(
            f"Invalid nbins={nbins}. Must be integer greater than 0.")

    if method == 'evenwidth':
        binedges = np.linspace(rmin, rmax, nbins+1, endpoint=True)
    elif method == 'evenlog10width':
        binedges = np.logspace(np.log10(rmin), np.log10(
            rmax), nbins+1, endpoint=True)
    elif method == 'equaloccupation':
        if source_seps is None:
            raise ValueError(
                f"Binning method '{method}' requires source separations array")
        # by default, keep all galaxies
        seps = np.array(source_seps)
        mask = np.full(seps.size, True)
        if rmin is not None or rmax is not None:
            # Need to filter source_seps to only keep galaxies in the [rmin, rmax]
            rmin = seps.min() if rmin is None else rmin
            rmax = seps.max() if rmax is None else rmax
            mask = (seps >= rmin)*(seps <= rmax)
        binedges = np.percentile(seps[mask], tuple(
            np.linspace(0, 100, nbins+1, endpoint=True)))
    else:
        raise ValueError(
            f"Binning method '{method}' is not currently supported")

    return binedges


def convert_units(dist1, unit1, unit2, redshift=None, cosmo=None):
    """ Convenience wrapper to convert between a combination of angular and physical units.

    Supported units: radians, degrees, arcmin, arcsec, Mpc, kpc, pc
    (letter case independent)

    To convert between angular and physical units you must provide both
    a redshift and a cosmology object.

    Parameters
    ----------
    dist1 : array_like
        Input distances
    unit1 : str
        Unit for the input distances
    unit2 : str
        Unit for the output distances
    redshift : float
        Redshift used to convert between angular and physical units
    cosmo : CLMM.Cosmology
        CLMM Cosmology object to compute angular diameter distance to
        convert between physical and angular units

    Returns
    -------
    dist2: array_like
        Input distances converted to unit2
    """
    # make case independent
    unit1, unit2 = unit1.lower(), unit2.lower()
    # Available units
    angular_bank = {"radians": u.rad, "degrees": u.deg,
                    "arcmin": u.arcmin, "arcsec": u.arcsec}
    physical_bank = {"pc": u.pc, "kpc": u.kpc, "mpc": u.Mpc}
    units_bank = {**angular_bank, **physical_bank}
    # Some error checking
    if unit1 not in units_bank:
        raise ValueError(f"Input units ({unit1}) not supported")
    if unit2 not in units_bank:
        raise ValueError(f"Output units ({unit2}) not supported")
    # Try automated astropy unit conversion
    try:
        dist2 = (dist1*units_bank[unit1]).to(units_bank[unit2]).value
    # Otherwise do manual conversion
    except u.UnitConversionError:
        # Make sure that we were passed a redshift and cosmology
        if redshift is None or cosmo is None:
            raise TypeError(
                "Redshift and cosmology must be specified to convert units") \
                from u.UnitConversionError
        # Redshift must be greater than zero for this approx
        if not redshift > 0.0:
            raise ValueError("Redshift must be greater than 0.") from u.UnitConversionError
        # Convert angular to physical
        if (unit1 in angular_bank) and (unit2 in physical_bank):
            dist1_rad = (dist1*units_bank[unit1]).to(u.rad).value
            dist1_mpc = cosmo.rad2mpc(dist1_rad, redshift)
            dist2 = (dist1_mpc*u.Mpc).to(units_bank[unit2]).value
        # Otherwise physical to angular
        else:
            dist1_mpc = (dist1*units_bank[unit1]).to(u.Mpc).value
            dist1_rad = cosmo.mpc2rad(dist1_mpc, redshift)
            dist2 = (dist1_rad*u.rad).to(units_bank[unit2]).value
    return dist2


def convert_shapes_to_epsilon(shape_1, shape_2, shape_definition='epsilon', kappa=0):
    r""" Convert shape components 1 and 2 appropriately to make them estimators of the reduced shear
    once averaged.  The shape 1 and 2 components may correspond to ellipticities according the
    :math:`\epsilon`- or :math:`\chi`-definition, but also to the 1 and 2 components of the shear.
    See Bartelmann & Schneider 2001 for details (https://arxiv.org/pdf/astro-ph/9912508.pdf).

    The :math:`\epsilon`-ellipticity is a direct estimator of
    the reduced shear. The shear :math:`\gamma` may be converted to reduced shear :math:`g` if the
    convergence :math:`\kappa` is known. The conversions are given below.

    .. math::
     \epsilon = \frac{\chi}{1+(1-|\chi|^2)^{1/2}}

    .. math::
     g=\frac{\gamma}{1-\kappa}

    - If `shape_definition = 'chi'`, this function returns the corresponding `epsilon` ellipticities

    - If `shape_definition = 'shear'`, it returns the corresponding reduced shear, given the
      convergence `kappa`

    - If `shape_definition = 'epsilon'` or `'reduced_shear'`, it returns them as is as no conversion
      is needed.

    Parameters
    ----------
    shape_1 : array_like
        Input shapes or shears along principal axis (g1 or e1)
    shape_2 : array_like
        Input shapes or shears along secondary axis (g2 or e2)
    shape_definition : str
        Definition of the input shapes, can be ellipticities 'epsilon' or 'chi' or shears 'shear' or
        'reduced_shear'
    kappa : array_like
        Convergence for transforming to a reduced shear. Default is 0

    Returns
    -------
    epsilon_1 : array_like
        Epsilon ellipticity (or reduced shear) along principal axis (epsilon1)
    epsilon_2 : array_like
        Epsilon ellipticity (or reduced shear) along secondary axis (epsilon2)
    """

    if shape_definition in ('epsilon', 'reduced_shear'):
        epsilon_1, epsilon_2 = shape_1, shape_2
    elif shape_definition == 'chi':
        chi_to_eps_conversion = 1./(1.+(1-(shape_1**2+shape_2**2))**0.5)
        epsilon_1, epsilon_2 = shape_1*chi_to_eps_conversion, shape_2*chi_to_eps_conversion
    elif shape_definition == 'shear':
        epsilon_1, epsilon_2 = shape_1/(1.-kappa), shape_2/(1.-kappa)
    else:
        raise TypeError("Please choose epsilon, chi, shear, reduced_shear")
    return epsilon_1, epsilon_2


def build_ellipticities(q11, q22, q12):
    """ Build ellipticties from second moments. See, e.g., Schneider et al. (2006)

    Parameters
    ----------
    q11 : float or array
        Second brightness moment tensor, component (1,1)
    q22 : float or array
        Second brightness moment tensor, component (2,2)
    q12 :  float or array
        Second brightness moment tensor, component (1,2)

    Returns
    -------
    chi1, chi2 : float or array
        Ellipticities using the "chi definition"
    epsilon1, epsilon2 : float or array
        Ellipticities using the "epsilon definition"
    """
    norm_x, norm_e = q11+q22, q11+q22+2*np.sqrt(q11*q22-q12*q12)
    chi1, chi2 = (q11-q22)/norm_x, 2*q12/norm_x
    epsilon1, epsilon2 = (q11-q22)/norm_e, 2*q12/norm_e
    return chi1, chi2, epsilon1, epsilon2


def compute_lensed_ellipticity(ellipticity1_true, ellipticity2_true, shear1, shear2, convergence):
    r""" Compute lensed ellipticities from the intrinsic ellipticities, shear and convergence.
    Following Schneider et al. (2006)

    .. math::
        \epsilon^{\rm lensed}=\epsilon^{\rm lensed}_1+i\epsilon^{\rm lensed}_2=
        \frac{\epsilon^{\rm true}+g}{1+g^\ast\epsilon^{\rm true}},

    where, the complex reduced shear :math:`g` is obtained from the shear
    :math:`\gamma=\gamma_1+i\gamma_2` and convergence :math:`\kappa` as :math:`g =
    \gamma/(1-\kappa)`, and the complex intrinsic ellipticity is :math:`\epsilon^{\rm
    true}=\epsilon^{\rm true}_1+i\epsilon^{\rm true}_2`

    Parameters
    ----------
    ellipticity1_true : float or array
        Intrinsic ellipticity of the sources along the principal axis
    ellipticity2_true : float or array
        Intrinsic ellipticity of the sources along the second axis
    shear1 :  float or array
        Shear component (not reduced shear) along the principal axis at the source location
    shear2 :  float or array
        Shear component (not reduced shear) along the 45-degree axis at the source location
    convergence :  float or array
        Convergence at the source location
    Returns
    -------
    e1, e2 : float or array
        Lensed ellipicity along both reference axes.
    """
    # shear (as a complex number)
    shear = shear1+shear2*1j
    # intrinsic ellipticity (as a complex number)
    ellipticity_true = ellipticity1_true+ellipticity2_true*1j
    # reduced shear
    reduced_shear = shear/(1.0-convergence)
    # lensed ellipticity
    lensed_ellipticity = (ellipticity_true+reduced_shear) / \
        (1.0+reduced_shear.conjugate()*ellipticity_true)
    return np.real(lensed_ellipticity), np.imag(lensed_ellipticity)


def arguments_consistency(arguments, names=None, prefix=''):
    r"""Make sure all arguments have the same length (or are scalars)

    Parameters
    ----------
    arguments: list, arrays, tuple
        Group of arguments to be checked
    names: list, tuple
        Names for each array, optional
    prefix: str
        Customized prefix for error message

    Returns
    -------
    list, arrays, tuple
        Group of arguments, converted to numpy arrays if they have length
    """
    sizes = [len(arg) if hasattr(arg, '__len__')
             else None for arg in arguments]
    # check there is a name for each argument
    if names:
        if len(names) != len(arguments):
            raise TypeError(
                f'names (len={len(names)}) must have same length '
                f'as arguments (len={len(arguments)})')
        msg = ', '.join([f'{n}({s})' for n, s in zip(names, sizes)])
    else:
        msg = ', '.join([f'{s}' for s in sizes])
    # check consistency
    if any(sizes):
        # Check that all of the inputs have length and they match
        if not all(sizes) or any([s != sizes[0] for s in sizes[1:]]):
            # make error message
            raise TypeError(f'{prefix} inconsistent sizes: {msg}')
        return tuple(np.array(arg) for arg in arguments)
    return arguments


def _patch_rho_crit_to_cd2018(rho_crit_external):
    r""" Convertion factor for rho_crit of any external modult to
    CODATA 2018+IAU 2015

    rho_crit_external: float
        Critical density of the Universe in units of :math:`M_\odot\ Mpc^{-3}`
    """

    rhocrit_mks = 3.0*100.0*100.0/(8.0*np.pi*const.GNEWT.value)
    rhocrit_cd2018 = (rhocrit_mks*1000.0*1000.0*
        const.PC_TO_METER.value*1.0e6/const.SOLAR_MASS.value)

    return rhocrit_cd2018/rho_crit_external

_valid_types = {
    float: (float, int, np.floating, np.integer),
    int: (int, np.integer),
    'float_array': (float, int, np.floating, np.integer),
    'int_array': (int, np.integer)
    }

def _is_valid(arg, valid_type):
    r"""Check if argument is of valid type, supports arrays.

    Parameters
    ----------
    arg: any
        Argument to be tested.
    valid_type: str, type
        Valid types for argument, options are object types, list/tuple of types, or:

            * `int_array` - interger, interger array
            * `float_array` - float, float array

    Returns
    -------
    valid: bool
        Is argument valid
    """
    return (isinstance(arg[0], _valid_types[valid_type])
                if (valid_type in ('int_array', 'float_array') and np.iterable(arg))
                else isinstance(arg, _valid_types.get(valid_type, valid_type)))


def validate_argument(loc, argname, valid_type, none_ok=False, argmin=None, argmax=None,
                      eqmin=False, eqmax=False):
    r"""Validate argument type and raise errors.

    Parameters
    ----------
    loc: dict
        Dictionary with all input arguments. Should be locals().
    argname: str
        Name of argument to be tested.
    valid_type: str, type
        Valid types for argument, options are object types, list/tuple of types, or:

            * `int_array` - interger, interger array
            * `float_array` - float, float array

    none_ok: True
        Accepts None as a valid type.
    argmin (optional) : int, float, None
        Minimum value allowed.
    argmax (optional) : int, float, None
        Maximum value allowed.
    eqmin: bool
        Accepts min(arg)==argmin.
    eqmax: bool
        Accepts max(arg)==argmax.
    """
    var = loc[argname]
    # Check for None
    if none_ok and (var is None):
        return
    # Check for type
    valid = (any(_is_valid(var, types) for types in valid_type)
                if isinstance(valid_type, (list, tuple))
                else _is_valid(var, valid_type))
    if not valid:
        err = f'{argname} must be {valid_type}, received {type(var).__name__}'
        raise TypeError(err)
    # Check min/max
    if any(t is not None for t in (argmin, argmax)):
        try:
            var_array = np.array(var, dtype=float)
        except:
            err = f'{argname} ({type(var).__name__}) cannot be converted to number' \
                  ' for min/max validation.'
            raise TypeError(err)
        if argmin is not None:
            if (var_array.min()<argmin if eqmin else var_array.min()<=argmin):
                err = f'{argname} must be greater than {argmin},' \
                      f' received {"vec_min:"*(var_array.size-1)}{var}'
                raise ValueError(err)
        if argmax is not None:
            if (var_array.max()>argmax if eqmax else var_array.max()>=argmax):
                err = f'{argname} must be lesser than {argmax},' \
                      f' received {"vec_max:"*(var_array.size-1)}{var}'
                raise ValueError(err)

def compute_beta(z_s, z_cl, cosmo):
    r"""Geometric lensing efficicency  
    
    .. math:: 
        beta = max(0, Dang_ls/Dang_s)
        
    Eq.2 in https://arxiv.org/pdf/1611.03866.pdf    
    
    Parameters
    ----------
    z_cl: float
            Galaxy cluster redshift
    z_s:  float
            Source galaxy  redshift
    cosmo: Cosmology
        Cosmology object
    
    Returns
    -------
    float
        Geometric lensing efficicency
    """
    beta = np.heaviside(z_s-z_cl, 0) * cosmo.eval_da_z1z2(z_cl, z_s) / cosmo.eval_da(z_cl)
    return beta

def compute_beta_s(z_s, z_cl, z_inf, cosmo):
    r"""Geometric lensing efficicency ratio 
    
    .. math:: 
        beta_s =beta(z_s)/beta(z_inf)

    Parameters
    ----------
    z_cl: float
            Galaxy cluster redshift
    z_s:  float
            Source galaxy redshift
    z_inf: float
            Redshift at infinity
    cosmo: Cosmology
        Cosmology object
    
    Returns
    -------
    float
        Geometric lensing efficicency ratio
    """
    beta_s = compute_beta(z_s, z_cl, cosmo) / compute_beta(z_inf, z_cl, cosmo)
    return beta_s

def compute_beta_mean(z_cl, cosmo, zmax=10.0, delta_z_cut=0.1, zmin=None, z_distrib_func=None):
    r"""Mean value of the geometric lensing efficicency  
    
    .. math:: 
       \left\<beta\right\> =\frac{\sum_{z = z_{min}}^{z = z_{max}}\beta(z)p(z)}{\sum_{z = z_{min}}^{z = z_{max}}p(z)}

    Parameters
    ----------
    z_cl: float
            Galaxy cluster redshift
    z_inf: float
            Redshift at infinity
    z_distrib_func: one-parameter function
            Redshift distribution function. Default is\
            Chang et al (2013) distribution\
            function.
    zmin: float
            Minimum redshift to be set as the source of the galaxy\
             when performing the sum.
    zmax: float
            Maximum redshift to be set as the source of the galaxy\
            when performing the sum.
    delta_z_cut: float
            Redshift interval to be summed with $z_cl$ to return\
            $zmin$. This feature is not used if $z_min$ is provided by the user.
    cosmo: Cosmology
        Cosmology object
    
    Returns
    -------
    float
        Mean value of the geometric lensing efficicency
    """
    if z_distrib_func == None:
        z_distrib_func = _chang_z_distrib
    def integrand(z_i, z_cl=z_cl, cosmo=cosmo):
        return compute_beta(z_i, z_cl, cosmo) * z_distrib_func(z_i)
    
    if zmin==None:
        zmin = z_cl + delta_z_cut
    
    B_mean = quad(integrand, zmin, zmax)[0] / quad(z_distrib_func, zmin, zmax)[0]
    return B_mean    

def compute_beta_s_mean(z_cl, z_inf, cosmo, zmax=10.0, delta_z_cut=0.1, zmin=None, z_distrib_func=None):
    r"""Mean value of the geometric lensing efficicency ratio 
    
    .. math:: 
       \left\<beta_s\right\> =\frac{\sum_{z = z_{min}}^{z = z_{max}}\beta_s(z)p(z)}{\sum_{z = z_{min}}^{z = z_{max}}p(z)}

    Parameters
    ----------
    z_cl: float
            Galaxy cluster redshift
    z_inf: float
            Redshift at infinity
    z_distrib_func: one-parameter function
            Redshift distribution function. Default is\
            Chang et al (2013) distribution\
            function.
    zmin: float
            Minimum redshift to be set as the source of the galaxy\
            when performing the sum.
    zmax: float
            Minimum redshift to be set as the source of the galaxy\
            when performing the sum.
    delta_z_cut: float
            Redshift interval to be summed with $z_cl$ to return\
            $zmin$. This feature is not used if $z_min$ is provided by the user.
    cosmo: Cosmology
        Cosmology object
    
    Returns
    -------
    float
        Mean value of the geometric lensing efficicency ratio
    """   
    if z_distrib_func == None:
        z_distrib_func = _chang_z_distrib

    def integrand(z_i, z_cl=z_cl, z_inf=z_inf, cosmo=cosmo):
        return compute_beta_s(z_i, z_cl, z_inf, cosmo) * z_distrib_func(z_i)

    if zmin==None:
        zmin = z_cl + delta_z_cut
    Bs_mean = quad(integrand, zmin, zmax)[0] / quad(z_distrib_func, zmin, zmax)[0]
    return Bs_mean

def compute_beta_s_square_mean(z_cl, z_inf, cosmo, zmax=10.0, delta_z_cut=0.1, zmin=None, z_distrib_func=None):
    r"""Mean square value of the geometric lensing efficicency ratio 
    
    .. math:: 
       \left\<beta_s\right\>2 =\frac{\sum_{z = z_{min}}^{z = z_{max}}\beta_s^2(z)p(z)}{\sum_{z = z_{min}}^{z = z_{max}}p(z)}

    Parameters
    ----------
    z_cl: float
            Galaxy cluster redshift
    z_inf: float
            Redshift at infinity
    z_distrib_func: one-parameter function
            Redshift distribution function. Default is\
            Chang et al (2013) distribution\
            function.
    zmin: float
            Minimum redshift to be set as the source of the galaxy\
            when performing the sum.
    zmax: float
            Minimum redshift to be set as the source of the galaxy\
            when performing the sum.
    delta_z_cut: float
            Redshift interval to be summed with $z_cl$ to return\
            $zmin$. This feature is not used if $z_min$ is provided by the user.
    cosmo: Cosmology
        Cosmology object
    
    Returns
    -------
    float
        Mean square value of the geometric lensing efficicency ratio.
    """ 
    if z_distrib_func == None:
        z_distrib_func = _chang_z_distrib
    
    def integrand(z_i, z_cl=z_cl, z_inf=z_inf, cosmo=cosmo):
        return compute_beta_s(z_i, z_cl, z_inf, cosmo)**2 * z_distrib_func(z_i)
    
    if zmin==None:
        zmin = z_cl + delta_z_cut
    Bs_square_mean = quad(integrand, zmin, zmax)[0] / quad(z_distrib_func, zmin, zmax)[0]
    return Bs_square_mean

def _chang_z_distrib(redshift, is_cdf=False):
    """
    A private function that returns the Chang et al (2013) unnormalized galaxy redshift distribution
    function, with the fiducial set of parameters.

    Parameters
    ----------
    redshift : float
        Galaxy redshift
    is_cdf : bool
        If True, returns cumulative distribution function.

    Returns
    -------
    The value of the distribution at z
    """
    alpha, beta, redshift0 = 1.24, 1.01, 0.51
    if is_cdf:
        return redshift0**(alpha+1)*gammainc((alpha+1)/beta, (redshift/redshift0)**beta)/beta*gamma((alpha+1)/beta)
    else:
        return (redshift**alpha)*np.exp(-(redshift/redshift0)**beta)

def _srd_z_distrib(redshift, is_cdf=False):
    """
    A private function that returns the unnormalized galaxy redshift distribution function used in
    the LSST/DESC Science Requirement Document (arxiv:1809.01669).

    Parameters
    ----------
    redshift : float
        Galaxy redshift
    is_cdf : bool
        If True, returns cumulative distribution function.

    Returns
    -------
    The value of the distribution at z
    """
    alpha, beta, redshift0 = 2., 0.9, 0.28
    if is_cdf:
        return redshift0**(alpha+1)*gammainc((alpha+1)/beta, (redshift/redshift0)**beta)/beta*gamma((alpha+1)/beta)
    else:
        return (redshift**alpha)*np.exp(-(redshift/redshift0)**beta)
