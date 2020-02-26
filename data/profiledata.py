""" profiledata.py: handles background profile information"""
import numpy as np
import h5py


class ProfileData:
    """Class handling the profile files of a run (i.e. one per species)

    :param common: CommonData object of the run
    """

    def __init__(self, pnt, is_h5, specnames, fileextension, folder):
        """ Read parameter file and create empty arrays for profile data """
        self.pnt = pnt
        self.is_h5 = is_h5
        self.specnames = specnames
        self.fileextension = fileextension
        self.folder = folder

        self.xs = np.empty(pnt.nx0)
        self.x_a = np.empty(pnt.nx0)
        self.T0s = np.empty((pnt.nx0, pnt.n_spec))
        self.n0s = np.empty((pnt.nx0, pnt.n_spec))
        self.omt0s = np.empty((pnt.nx0, pnt.n_spec))
        self.omn0s = np.empty((pnt.nx0, pnt.n_spec))
        self._read_zero_prof()

    def _read_zero_prof(self):
        """Get the initial profiles from profiles_spec_fileextension"""
        if self.is_h5:
            for n, spec in enumerate(self.specnames):
                proffile = self.folder / 'profiles_{}{}'.format(spec, self.fileextension)
                prof = h5py.File(proffile, 'r')
                self.x_a = prof.get("/position/x_o_a")[()]
                self.xs = prof.get("/position/x_o_rho_ref")[()]
                self.T0s[:, n] = prof.get('/temp/T')[()]
                self.omt0s[:, n] = prof.get('/temp/omt')[()]
                self.n0s[:, n] = prof.get('/density/n')[()]
                self.omn0s[:, n] = prof.get('/density/omn')[()]
                prof.close()
        else:
            for n, spec in enumerate(self.specnames):

                prof0file = open(self.folder / 'profiles_{}{}'.format(spec, self.fileextension))
                lines = prof0file.readlines()
                for i in range(0, self.pnt.nx0):
                    j = 2 + i
                    self.xs[i] = lines[j].split()[0]
                    self.x_a[i] = lines[j].split()[1]
                    self.T0s[i, n] = float(lines[j].split()[2])
                    self.n0s[i, n] = float(lines[j].split()[3])
                    self.omt0s[i, n] = lines[j].split()[4]
                    self.omn0s[i, n] = lines[j].split()[5]
                prof0file.close()
