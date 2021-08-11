import numpy


class ICAOAtmosphere:
    def __init__(self, **kwargs):

        # Check if we have english units:
        self.englishUnits = False
        if "englishUnits" in kwargs:
            self.englishUnits = kwargs["englishUnits"]

    def __call__(self, altitude):
        """
        Compute the atmospheric properties at altitude, 'altitude' in meters
        """
        if altitude is None:
            return None, None
        # Convert altitude to km since this is what the ICAO
        # atmosphere uses:
        if self.englishUnits:
            altitude = altitude * 0.3048 / 1000.0
        else:
            altitude = altitude / 1000.0

        K = 34.163195
        R0 = 6356.766  # Radius of Earth
        H = altitude / (1.0 + altitude / R0)

        # Smoothing region on either side. 0.1 is 100m, seems to work
        # well. Please don't change.
        dH_smooth = 0.1

        # Sea Level Values
        P0 = 101325  # Pressure

        # The set of break-points in the altitude (in km)
        H_break = numpy.array([11, 20, 32, 47, 51, 71, 84.852])

        def hermite(t, p0, m0, p1, m1):
            """Compute a standard cubic hermite interpolant"""
            return (
                p0 * (2 * t ** 3 - 3 * t ** 2 + 1)
                + m0 * (t ** 3 - 2 * t ** 2 + t)
                + p1 * (-2 * t ** 3 + 3 * t ** 2)
                + m1 * (t ** 3 - t ** 2)
            )

        def getTP(H, index):
            """Compute temperature and pressure"""
            if index == 0:
                T = 288.15 - 6.5 * H
                PP = (288.15 / T) ** (-K / 6.5)
            elif index == 1:
                T = 216.65
                PP = 0.22336 * numpy.exp(-K * (H - 11) / 216.65)
            elif index == 2:
                T = 216.65 + (H - 20)
                PP = 0.054032 * (216.65 / T) ** K
            elif index == 3:
                T = 228.65 + 2.8 * (H - 32)
                PP = 0.0085666 * (228.65 / T) ** (K / 2.8)
            elif index == 4:
                T = 270.65
                PP = 0.0010945 * numpy.exp(-K * (H - 47) / 270.65)
            elif index == 5:
                T = 270.65 - 2.8 * (H - 51)
                PP = 0.00066063 * (270.65 / T) ** (-K / 2.8)
            elif index == 6:
                T = 214.65 - 2 * (H - 71)
                PP = 0.000039046 * (214.65 / T) ** (-K / 2)

            return T, PP

        # Determine if we need to do smoothing or not:
        smooth = False
        for index in range(len(H_break)):
            if numpy.real(H) > H_break[index] - dH_smooth and numpy.real(H) < H_break[index] + dH_smooth:
                smooth = True
                break

        if not smooth:
            index = H_break.searchsorted(H, side="left")

            # Get the nominal values we need
            T, PP = getTP(H, index)
        else:
            H0 = H_break[index]
            # Parametric distance along smoothing region
            H_left = H0 - dH_smooth
            H_right = H0 + dH_smooth

            t = (H - H_left) / (H_right - H_left)  # Parametric value from 0 to 1

            # set an FD step to compute the derivs

            dh_FD = 1.0e-4  # confirmed with stepsize study do not change from 1e-4

            # Compute slope and values at the left boundary
            TL, PPL = getTP(H_left, index)
            Tph, PPph = getTP(H_left + dh_FD, index)
            Tmh, PPmh = getTP(H_left - dh_FD, index)

            T_left = TL
            PP_left = PPL

            T_slope_left = (Tph - Tmh) / (2 * dh_FD) * (dH_smooth * 2)
            PP_slope_left = (PPph - PPmh) / (2 * dh_FD) * (dH_smooth * 2)

            # Compute slope and values at the right boundary
            TR, PPR = getTP(H_right, index + 1)
            Tph, PPph = getTP(H_right + dh_FD, index + 1)
            Tmh, PPmh = getTP(H_right - dh_FD, index + 1)

            T_right = TR
            PP_right = PPR

            T_slope_right = (Tph - Tmh) / (2 * dh_FD) * (dH_smooth * 2)
            PP_slope_right = (PPph - PPmh) / (2 * dh_FD) * (dH_smooth * 2)

            # Standard cubic hermite spline interpolation
            T = hermite(t, T_left, T_slope_left, T_right, T_slope_right)
            PP = hermite(t, PP_left, PP_slope_left, PP_right, PP_slope_right)
        # end if

        P = P0 * PP  # Pressure

        if self.englishUnits:
            P /= 47.88020833333
            T *= 1.8

        return P, T


# ==============================================================================
# Analysis Test
# ==============================================================================
if __name__ == "__main__":
    print("Testing ...")

    Atm = ICAOAtmosphere()

    print(Atm(11000.001))
    R = 287.870
    P, T = Atm(457.2)
    rho = P / (R * T)
    print(P, T, rho)
