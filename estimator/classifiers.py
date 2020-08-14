import numpy as np
import stella.lib.rust_stella as rust
from sklearn.discriminant_analysis import LinearDiscriminantAnalysis as LDA
from stella.estimator.discriminant_analysis import LinearDiscriminantAnalysis as LDA_stella
import scipy.stats 

class MultivariateGaussianClassifier():
    def __init__(self,Nc,means,covs,priors=None,dim_reduce=None):
        """
            Performs a Ns-multivariate classification on Nc classes.
            Each class is given with a mean and a covirance matrix. The function
            predict_proba is used to return the probality given leakage
            samples and the fitted model.

            Nc: number of classes
            means: (Nc,Ns) the means of each class
            covs: (Nc,Ns,Ns) the covariance of each class
            priors: (Nc) priors of each of the classes
            dim_reduce: an object that implements transform(). It is apply
                to fresh traces to reduce their dimensions.
        """
        #input checks
        if means.ndim != 2:
            raise Exception("Waiting 2 dim array for means")
        mx,my = means.shape

        if covs.ndim != 3:
            raise Exception("Waiting 3 dim array for covs")
        cx,cy,cz = covs.shape
        if cy != cz:
            raise Exception("Covariance matrices are not square")
        if cy != my:
            raise Exception("Missmatch cov and mean size {} vs {}".format(cy,my))
        if cx != Nc or mx != Nc:
            raise Exception("Number of class does not match the templates size")
        if priors is not None:
            if priors.ndim != 1:
                raise Exception("Waiting 1 dim array for priors")
        else:
            priors = np.ones(Nc)


        self._priors = priors
        self._means = means
        self._covs = covs
        self._Nc = Nc
        self._dim_reduce = dim_reduce
        self._Ns = my
        self._n_components = cz
        self._cov = covs

        self._psd = _PSD(covs[0], allow_singular=True)

    def predict_proba(self,X,use_rust=True,n_components=None):
        """
            Returns the probability of each classes by applying 
            Bayes law.

            X (n_traces,Ns): n_traces traces to evaluate

            returns a (n_traces,Nc) array
        """
        if n_components is None:
            n_components = self._n_components

        if X.ndim != 2:
            raise Exception("Waiting a 2 dim array as X")
        if self._dim_reduce is not None:
            X = self._dim_reduce.transform(X)

        n_samples,Ns = X.shape

        prs = np.zeros((n_samples,self._Nc))
        
        # This si inspired by the Scipy Implementation of multivariate Gaussian 
        # pdf
        if not use_rust:
            for i in range(self._Nc):
                u = self._means[i][:n_components]
                dev = u - X
                prs[:,i] = np.exp(-0.5*np.sum(np.square(np.dot(dev, self._psd.U)), axis=-1))
        else:
            means = np.array(self._means)
            rust.multivariate_pooled(self._psd.U,
               means,
               X,
               prs);

        I = np.where(np.sum(prs,axis=1)==0)[0]
        prs[I] = 1
        return (prs.T/np.sum(prs,axis=1)).T

class LDAClassifier():
    def __init__(self,traces,labels,solver="eigen",dim_projection=4,priors=None,Nc=None,duplicate=True,opt=True):
        Ns = traces[0,:]
        if Nc is None:
            Nk = Nc = len(np.unique(labels))
        else:
            Nk = Nc
        C_i = labels
        
        if opt:
            dim_reduce = LDA_stella(n_components=min(dim_projection,Nk-1),solver=solver,priors=priors,duplicate=duplicate)
        else:
            dim_reduce = LDA(n_components=min(dim_projection,Nk-1),solver=solver,priors=priors)
        traces_i = dim_reduce.fit_transform(traces,C_i)
        lx,ly = traces_i.shape
        model = np.zeros((Nk,ly))

        #noise = np.zeros((Nk,ly,ly))
        for k in range(Nk):
            I = np.where(C_i==k)[0]
            model[k] = np.mean(traces_i[I,:],axis=0)
        noise = traces_i-model[C_i]
        cov = np.cov(noise.T)
        covs = np.tile(cov,(Nc,1,1))

        self._trained_on = len(labels)
        self._mvGC = MultivariateGaussianClassifier(Nk,model,covs,dim_reduce=dim_reduce,priors=priors)
        self._dim_reduce = dim_reduce
    def predict_proba_opt(self,X,n_components=None):
        """
            Returns the probability of each classes by applying 
            Bayes law.

            X (n_traces,Ns): n_traces traces to evaluate

            returns a (n_traces,Nc) array
        """
        return self._mvGC.predict_proba_opt(X,n_components)


    def predict_proba(self,X,n_components=None):
        """
            Returns the probability of each classes by applying 
            Bayes law.

            X (n_traces,Ns): n_traces traces to evaluate

            returns a (n_traces,Nc) array
        """
        return self._mvGC.predict_proba(X,n_components)


#####################
#####################
# This comes from SciPy
#####################
#####################
def _eigvalsh_to_eps(spectrum, cond=None, rcond=None):
    """
    Determine which eigenvalues are "small" given the spectrum.
    This is for compatibility across various linear algebra functions
    that should agree about whether or not a Hermitian matrix is numerically
    singular and what is its numerical matrix rank.
    This is designed to be compatible with scipy.linalg.pinvh.
    Parameters
    ----------
    spectrum : 1d ndarray
        Array of eigenvalues of a Hermitian matrix.
    cond, rcond : float, optional
        Cutoff for small eigenvalues.
        Singular values smaller than rcond * largest_eigenvalue are
        considered zero.
        If None or -1, suitable machine precision is used.
    Returns
    -------
    eps : float
        Magnitude cutoff for numerical negligibility.
    """
    if rcond is not None:
        cond = rcond
    if cond in [None, -1]:
        t = spectrum.dtype.char.lower()
        factor = {'f': 1E3, 'd': 1E6}
        cond = factor[t] * np.finfo(t).eps
    eps = cond * np.max(abs(spectrum))
    return eps


def _pinv_1d(v, eps=1e-5):
    """
    A helper function for computing the pseudoinverse.
    Parameters
    ----------
    v : iterable of numbers
        This may be thought of as a vector of eigenvalues or singular values.
    eps : float
        Values with magnitude no greater than eps are considered negligible.
    Returns
    -------
    v_pinv : 1d float ndarray
        A vector of pseudo-inverted numbers.
    """
    return np.array([0 if abs(x) <= eps else 1/x for x in v], dtype=float)


class _PSD(object):
    """
    Compute coordinated functions of a symmetric positive semidefinite matrix.
    This class addresses two issues.  Firstly it allows the pseudoinverse,
    the logarithm of the pseudo-determinant, and the rank of the matrix
    to be computed using one call to eigh instead of three.
    Secondly it allows these functions to be computed in a way
    that gives mutually compatible results.
    All of the functions are computed with a common understanding as to
    which of the eigenvalues are to be considered negligibly small.
    The functions are designed to coordinate with scipy.linalg.pinvh()
    but not necessarily with np.linalg.det() or with np.linalg.matrix_rank().
    Parameters
    ----------
    M : array_like
        Symmetric positive semidefinite matrix (2-D).
    cond, rcond : float, optional
        Cutoff for small eigenvalues.
        Singular values smaller than rcond * largest_eigenvalue are
        considered zero.
        If None or -1, suitable machine precision is used.
    lower : bool, optional
        Whether the pertinent array data is taken from the lower
        or upper triangle of M. (Default: lower)
    check_finite : bool, optional
        Whether to check that the input matrices contain only finite
        numbers. Disabling may give a performance gain, but may result
        in problems (crashes, non-termination) if the inputs do contain
        infinities or NaNs.
    allow_singular : bool, optional
        Whether to allow a singular matrix.  (Default: True)
    Notes
    -----
    The arguments are similar to those of scipy.linalg.pinvh().
    """

    def __init__(self, M, cond=None, rcond=None, lower=True,
                 check_finite=True, allow_singular=True):
        # Compute the symmetric eigendecomposition.
        # Note that eigh takes care of array conversion, chkfinite,
        # and assertion that the matrix is square.
        s, u = scipy.linalg.eigh(M, lower=lower, check_finite=check_finite)

        eps = _eigvalsh_to_eps(s, cond, rcond)
        if np.min(s) < -eps:
            raise ValueError('the input matrix must be positive semidefinite')
        d = s[s > eps]
        if len(d) < len(s) and not allow_singular:
            raise np.linalg.LinAlgError('singular matrix')
        s_pinv = _pinv_1d(s, eps)
        U = np.multiply(u, np.sqrt(s_pinv))

        # Initialize the eagerly precomputed attributes.
        self.rank = len(d)
        self.U = U
        self.log_pdet = np.sum(np.log(d))

        # Initialize an attribute to be lazily computed.
        self._pinv = None

    @property
    def pinv(self):
        if self._pinv is None:
            self._pinv = np.dot(self.U, self.U.T)
        return self._pinv

