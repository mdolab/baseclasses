import warnings


class FluidProperties:
    """
    Parameters
    ----------

    gamma : float (default = 1.4)
        Set the ratio of the specific heats.

    Pr : float (default = 0.72)
        Set the Prandtl number.

    R : float (default = 287.055 J / kg / K)
        The specific gas constant. By default we use air.

    SSuthDim : float (default = 110.55)

    muSuthDim : float (default = 1.716e-5)

    TSuthDim : float (default = 273.15)
    """

    def __init__(self, **kwargs):

        # Check if we have english units:
        self.englishUnits = False
        if "englishUnits" in kwargs:
            self.englishUnits = kwargs["englishUnits"]

        # Check if 'R' is given....if not we assume air
        if "R" in kwargs:
            self.R = kwargs["R"]
        else:
            # Universal gas constant
            # (https://physics.nist.gov/cuu/Constants/)
            R_universal = 8.3144598  # J / mol / K

            # Molecular mass of air
            # (https://www.engineeringtoolbox.com/molecular-mass-air-d_679.html)
            M_air = 28.9647  # g / mol

            # Specific gas constant of air in S.I. units
            R_air = R_universal / M_air * 1000.0  # J / kg / K

            # Conversion from S.I. to english. Basically the S.I. units are
            # m^2 / s^2 / K so we need to convert meters to feet and Kelvin to
            # Rankine
            m2ft = 0.3048  # official conversion from meters to feet
            Ra2K = 1.8  # official conversion from Rankine to Kelvin

            if self.englishUnits:
                self.R = R_air / Ra2K / m2ft ** 2  # 1716.574 ft-lbf / slug / R
            else:
                self.R = R_air  # 287.055 J / kg / K

        # Check if 'gamma' is given....if not we assume air
        if "gamma" in kwargs:
            self.gamma = kwargs["gamma"]
        else:
            self.gamma = 1.4

        # Check if 'Pr' is given....if not we assume air
        if "Pr" in kwargs:
            self.Pr = kwargs["Pr"]
        else:
            self.Pr = 0.72

        # Sutherland's Law Constants
        # (https://www.cfd-online.com/Wiki/Sutherland's_law)
        if "SSuthDim" in kwargs or "muSuthDim" in kwargs or "TSuthDim" in kwargs:
            if not all(name in kwargs for name in ("muSuthDim", "muSuthDim", "TSuthDim")):
                warnings.warn(
                    "One or more constant for Sutherlands law might be missing!\
                Make sure to provide all three!"
                )

        if "SSuthDim" in kwargs:
            self.SSuthDim = kwargs["SSuthDim"]
        else:
            self.SSuthDim = 110.55

        if "muSuthDim" in kwargs:
            self.muSuthDim = kwargs["muSuthDim"]
        else:
            self.muSuthDim = 1.716e-5

        if "TSuthDim" in kwargs:
            self.TSuthDim = kwargs["TSuthDim"]
        else:
            self.TSuthDim = 273.15

    def updateViscosity(self, T):
        """
        Compute the dynamic viscosity using Sutherland's Law
        """

        # calculate the dynamic viscosity
        if self.englishUnits:
            T /= 1.8

        self.mu = self.muSuthDim * (T / self.TSuthDim) ** 1.5 * (self.TSuthDim + self.SSuthDim) / (T + self.SSuthDim)

        if self.englishUnits:
            self.mu /= 47.9
