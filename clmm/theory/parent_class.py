"""@file parent_class.py
CLMModeling abstract class
"""
import numpy as np
import warnings
from .generic import compute_reduced_shear_from_convergence, compute_magnification_bias_from_magnification
from ..utils import validate_argument


class CLMModeling:
    r"""Object with functions for halo mass modeling

    Attributes
    ----------
    backend: str
        Name of the backend being used
    massdef : str
        Profile mass definition (`mean`, `critical`, `virial` - letter case independent)
    delta_mdef : int
        Mass overdensity definition.
    halo_profile_model : str
        Profile model parameterization (`nfw`, `einasto`, `hernquist` - letter case independent)
    cosmo: Cosmology
        Cosmology object
    hdpm: Object
        Backend object with halo profiles
    mdef_dict: dict
        Dictionary with the definitions for mass
    hdpm_dict: dict
        Dictionary with the definitions for profile
    validate_input: bool
        Validade each input argument
    cosmo_class: type
        Type of used cosmology objects
    """
    # pylint: disable=too-many-instance-attributes

    def __init__(self, validate_input=True):
        self.backend = None

        self.massdef = ''
        self.delta_mdef = 0
        self.halo_profile_model = ''

        self.cosmo = None

        self.hdpm = None
        self.mdef_dict = {}
        self.hdpm_dict = {}

        self.validate_input = validate_input
        self.cosmo_class = None


    def set_cosmo(self, cosmo):
        r""" Sets the cosmology to the internal cosmology object

        Parameters
        ----------
        cosmo: clmm.Comology object, None
            CLMM Cosmology object. If is None, creates a new instance of self.cosmo_class().
        """
        if self.validate_input:
            if self.cosmo_class is None:
                raise NotImplementedError
            validate_argument(locals(), 'cosmo', self.cosmo_class, none_ok=True)
        self._set_cosmo(cosmo)
        self.cosmo.validate_input = self.validate_input

    def _set_cosmo(self, cosmo):
        r""" Sets the cosmology to the internal cosmology object"""
        self.cosmo = cosmo if cosmo is not None else self.cosmo_class()

    def set_halo_density_profile(self, halo_profile_model='nfw', massdef='mean', delta_mdef=200):
        r""" Sets the definitios for the halo profile

        Parameters
        ----------
        halo_profile_model: str
            Halo mass profile, current options are 'nfw' (letter case independent)
        massdef: str
            Mass definition, current options are 'mean' (letter case independent)
        delta_mdef: int
            Overdensity number
        """
        # make case independent
        massdef, halo_profile_model = massdef.lower(), halo_profile_model.lower()
        if self.validate_input:
            validate_argument(locals(), 'massdef', str)
            validate_argument(locals(), 'halo_profile_model', str)
            validate_argument(locals(), 'delta_mdef', int, argmin=0)
            if not massdef in self.mdef_dict:
                raise ValueError(
                    f"Halo density profile mass definition {massdef} not currently supported")
            if not halo_profile_model in self.hdpm_dict:
                raise ValueError(
                    f"Halo density profile model {halo_profile_model} not currently supported")
        return self._set_halo_density_profile(halo_profile_model=halo_profile_model,
                                              massdef=massdef, delta_mdef=delta_mdef)

    def _set_halo_density_profile(self, halo_profile_model='nfw', massdef='mean', delta_mdef=200):
        raise NotImplementedError

    def set_mass(self, mdelta):
        r""" Sets the value of the :math:`M_\Delta`

        Parameters
        ----------
        mdelta : float
            Galaxy cluster mass :math:`M_\Delta` in units of :math:`M_\odot`
        """
        if self.validate_input:
            validate_argument(locals(), 'mdelta', float, argmin=0)
        self._set_mass(mdelta)

    def _set_mass(self, mdelta):
        r""" Actually sets the value of the :math:`M_\Delta` (without value check)"""
        raise NotImplementedError

    def set_concentration(self, cdelta):
        r""" Sets the concentration

        Parameters
        ----------
        cdelta: float
            Concentration
        """
        if self.validate_input:
            validate_argument(locals(), 'cdelta', float, argmin=0)
        self._set_concentration(cdelta)

    def _set_concentration(self, cdelta):
        r""" Actuall sets the value of the concentration (without value check)"""
        raise NotImplementedError

    def eval_3d_density(self, r3d, z_cl):
        r"""Retrieve the 3d density :math:`\rho(r)`.

        Parameters
        ----------
        r3d : array_like, float
            Radial position from the cluster center in :math:`M\!pc`.
        z_cl: float
            Redshift of the cluster

        Returns
        -------
        array_like, float
            3-dimensional mass density in units of :math:`M_\odot\ Mpc^{-3}`
        """
        if self.validate_input:
            validate_argument(locals(), 'r3d', 'float_array', argmin=0)
            validate_argument(locals(), 'z_cl', 'float_array', argmin=0)
        return self._eval_3d_density(r3d=r3d, z_cl=z_cl)

    def _eval_3d_density(self, r3d, z_cl):
        raise NotImplementedError

    def eval_critical_surface_density(self, z_len, z_src):
        r"""Computes the critical surface density

        Parameters
        ----------
        z_len : float
            Lens redshift
        z_src : array_like, float
            Background source galaxy redshift(s)

        Returns
        -------
        float
            Cosmology-dependent critical surface density in units of :math:`M_\odot\ Mpc^{-2}`
        """
        if self.validate_input:
            validate_argument(locals(), 'z_len', float, argmin=0)
            validate_argument(locals(), 'z_src', 'float_array', argmin=0)
        return self._eval_critical_surface_density(z_len=z_len, z_src=z_src)

    def _eval_critical_surface_density(self, z_len, z_src):
        return self.cosmo.eval_sigma_crit(z_len, z_src)

    def eval_surface_density(self, r_proj, z_cl):
        r""" Computes the surface mass density

        Parameters
        ----------
        r_proj : array_like
            Projected radial position from the cluster center in :math:`M\!pc`.
        z_cl: float
            Redshift of the cluster

        Returns
        -------
        array_like, float
            2D projected surface density in units of :math:`M_\odot\ Mpc^{-2}`
        """
        if self.validate_input:
            validate_argument(locals(), 'r_proj', 'float_array', argmin=0)
            validate_argument(locals(), 'z_cl', float, argmin=0)
        return self._eval_surface_density(r_proj=r_proj, z_cl=z_cl)

    def _eval_surface_density(self, r_proj, z_cl):
        raise NotImplementedError

    def eval_mean_surface_density(self, r_proj, z_cl):
        r""" Computes the mean value of surface density inside radius r_proj

        Parameters
        ----------
        r_proj : array_like
            Projected radial position from the cluster center in :math:`M\!pc`.
        z_cl: float
            Redshift of the cluster

        Returns
        -------
        array_like, float
            Excess surface density in units of :math:`M_\odot\ Mpc^{-2}`.
        """
        if self.validate_input:
            validate_argument(locals(), 'r_proj', 'float_array', argmin=0)
            validate_argument(locals(), 'z_cl', float, argmin=0)
        return self._eval_mean_surface_density(r_proj=r_proj, z_cl=z_cl)

    def _eval_mean_surface_density(self, r_proj, z_cl):
        raise NotImplementedError

    def eval_excess_surface_density(self, r_proj, z_cl):
        r""" Computes the excess surface density

        Parameters
        ----------
        r_proj : array_like
            Projected radial position from the cluster center in :math:`M\!pc`.
        z_cl: float
            Redshift of the cluster

        Returns
        -------
        array_like, float
            Excess surface density in units of :math:`M_\odot\ Mpc^{-2}`.
        """
        if self.validate_input:
            validate_argument(locals(), 'r_proj', 'float_array', argmin=0)
            validate_argument(locals(), 'z_cl', float, argmin=0)
        return self._eval_excess_surface_density(r_proj=r_proj, z_cl=z_cl)

    def _eval_excess_surface_density(self, r_proj, z_cl):
        raise NotImplementedError

    def eval_tangential_shear(self, r_proj, z_cl, z_src):
        r"""Computes the tangential shear

        Parameters
        ----------
        r_proj : array_like
            The projected radial positions in :math:`M\!pc`.
        z_cl : float
            Galaxy cluster redshift
        z_src : array_like, float
            Background source galaxy redshift(s)

        Returns
        -------
        array_like, float
            tangential shear
        """
        if self.validate_input:
            validate_argument(locals(), 'r_proj', 'float_array', argmin=0)
            validate_argument(locals(), 'z_cl', float, argmin=0)
            validate_argument(locals(), 'z_src', 'float_array', argmin=0)
        return self._eval_tangential_shear(r_proj=r_proj, z_cl=z_cl, z_src=z_src)

    def _eval_tangential_shear(self, r_proj, z_cl, z_src):
        delta_sigma = self.eval_excess_surface_density(r_proj, z_cl)
        sigma_c = self.eval_critical_surface_density(z_cl, z_src)
        return delta_sigma/sigma_c

    def eval_convergence(self, r_proj, z_cl, z_src):
        r"""Computes the mass convergence

        .. math::
            \kappa = \frac{\Sigma}{\Sigma_{crit}}

        or

        .. math::
            \kappa = \kappa_\infty \times \beta_s

        Parameters
        ----------
        r_proj : array_like
            The projected radial positions in :math:`M\!pc`.
        z_cl : float
            Galaxy cluster redshift
        z_src : array_like, float
            Background source galaxy redshift(s)

        Returns
        -------
        array_like, float
            Mass convergence, kappa.
        """
        if self.validate_input:
            validate_argument(locals(), 'r_proj', 'float_array', argmin=0)
            validate_argument(locals(), 'z_cl', float, argmin=0)
            validate_argument(locals(), 'z_src', 'float_array', argmin=0)
        return self._eval_convergence(r_proj=r_proj, z_cl=z_cl, z_src=z_src)

    def _eval_convergence(self, r_proj, z_cl, z_src):
        sigma = self.eval_surface_density(r_proj, z_cl)
        sigma_c = self.eval_critical_surface_density(z_cl, z_src)
        return sigma/sigma_c

    def eval_reduced_tangential_shear(self, r_proj, z_cl, z_src, z_src_model='single_plane',
                                      beta_s_mean=None, beta_s_square_mean=None):
        r"""Computes the reduced tangential shear :math:`g_t = \frac{\gamma_t}{1-\kappa}`.

        Parameters
        ----------
        r_proj : array_like
            The projected radial positions in :math:`M\!pc`.
        z_cl : float
            Galaxy cluster redshift
        z_src : array_like, float
            Background source galaxy redshift(s)
        z_src_model : str, optional
            Source redshift model, with the following supported options:

                * `single_plane` (default): all sources at one redshift (if `z_source` is a float) \
                    or known individual source galaxy redshifts (if `z_source` is an array and \
                    `r_proj` is a float);
                * `applegate14`: use the equation (6) in Weighing the Giants - III \
                    (Applegate et al. 2014; https://arxiv.org/abs/1208.0605) to evaluate tangential reduced shear;

        beta_s_mean: array_like, float
            Lensing efficiency averaged over the galaxy redshift distribution   

                .. math::
                    \langle \beta_s \rangle = \left\langle \frac{D_{LS}}{D_S}\frac{D_\infty}{D_{L,\infty}}\right\rangle
    
        beta_s_square_mean: array_like, float
            Square of the lensing efficiency averaged over the galaxy redshift distribution    

                .. math::
                    \langle \beta_s^2 \rangle = \left\langle \left(\frac{D_{LS}}{D_S}\frac{D_\infty}{D_{L,\infty}}\right)^2 \right\rangle

        Returns
        -------
        gt : array_like, float
            Reduced tangential shear

        Notes
        -----
        Need to figure out if we want to raise exceptions rather than errors here?
        """
        if self.validate_input:
            validate_argument(locals(), 'r_proj', 'float_array', argmin=0)
            validate_argument(locals(), 'z_cl', float, argmin=0)
            validate_argument(locals(), 'z_src', 'float_array', argmin=0)

        if z_src_model == 'single_plane':
            gt = self._eval_reduced_tangential_shear_sp(r_proj, z_cl, z_src)
        # elif z_src_model == 'known_z_src': # Discrete case
        #     raise NotImplementedError('Need to implemnt Beta_s functionality, or average'+
        #                               'sigma/sigma_c kappa_t = Beta_s*kappa_inf')
        # elif z_src_model == 'z_src_distribution': # Continuous ( from a distribution) case
        #     raise NotImplementedError('Need to implement Beta_s and Beta_s2 calculation from'+
        #                               'integrating distribution of redshifts in each radial bin')
        elif z_src_model == 'applegate14':
            if beta_s_mean is None or beta_s_square_mean is None:
                raise ValueError("beta_s_mean or beta_s_square_mean is not given.")
            else:
                z_source = 1000. #np.inf # INF or a very large number
                gammat = self._eval_tangential_shear(r_proj, z_cl, z_source)
                kappa = self._eval_convergence(r_proj, z_cl, z_source)
                gt = beta_s_mean * gammat / (1. - beta_s_square_mean / beta_s_mean * kappa)
        else:
            raise ValueError("Unsupported z_src_model")
        return gt

    def _eval_reduced_tangential_shear_sp(self, r_proj, z_cl, z_src):
        kappa = self.eval_convergence(r_proj, z_cl, z_src)
        gamma_t = self.eval_tangential_shear(r_proj, z_cl, z_src)
        return compute_reduced_shear_from_convergence(gamma_t, kappa)

    def eval_magnification(self, r_proj, z_cl, z_src):
        r"""Computes the magnification

        .. math::
            \mu = \frac{1}{(1-\kappa)^2-|\gamma_t|^2}

        Parameters
        ----------
        r_proj : array_like
            The projected radial positions in :math:`M\!pc`.
        z_cl : float
            Galaxy cluster redshift
        z_src : array_like, float
            Background source galaxy redshift(s)

        Returns
        -------
        mu : array_like, float
            magnification, mu.

        Notes
        -----
        The magnification is computed taking into account just the tangential
        shear. This is valid for spherically averaged profiles, e.g., NFW and
        Einasto (by construction the cross shear is zero).
        """
        if self.validate_input:
            validate_argument(locals(), 'r_proj', 'float_array', argmin=0)
            validate_argument(locals(), 'z_cl', float, argmin=0)
            validate_argument(locals(), 'z_src', 'float_array', argmin=0)
        return self._eval_magnification(r_proj=r_proj, z_cl=z_cl, z_src=z_src)

    def _eval_magnification(self, r_proj, z_cl, z_src):
        kappa = self.eval_convergence(r_proj, z_cl, z_src)
        gamma_t = self.eval_tangential_shear(r_proj, z_cl, z_src)
        return 1./((1-kappa)**2-abs(gamma_t)**2)
    
    def eval_magnification_bias(self, r_proj, z_cl, z_src, alpha):
        r"""Computes the magnification bias

        .. math::
            \mu^{\alpha - 1}

        Parameters
        ----------
        r_proj : array_like
            The projected radial positions in :math:`M\!pc`.
        z_cl : float
            Galaxy cluster redshift
        z_src : array_like, float
            Background source galaxy redshift(s)
        alpha : float
            Slope of the cummulative number count of background sources at a given magnitude

        Returns
        -------
        mu_bias : array_like, float
            magnification bias.

        Notes
        -----
        The magnification is computed taking into account just the tangential
        shear. This is valid for spherically averaged profiles, e.g., NFW and
        Einasto (by construction the cross shear is zero).
        """
        if self.validate_input:
            validate_argument(locals(), 'r_proj', 'float_array', argmin=0)
            validate_argument(locals(), 'z_cl', float, argmin=0)
            validate_argument(locals(), 'z_src', 'float_array', argmin=0)
            validate_argument(locals(), 'alpha', 'float_array')
        return self._eval_magnification_bias(r_proj=r_proj, z_cl=z_cl, z_src=z_src, alpha=alpha)

    def _eval_magnification_bias(self, r_proj, z_cl, z_src, alpha):
        magnification = self.eval_magnification(r_proj, z_cl, z_src)
        return compute_magnification_bias_from_magnification(magnification, alpha)
