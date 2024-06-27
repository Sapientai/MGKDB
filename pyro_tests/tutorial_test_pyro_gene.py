from pyrokinetics import Pyro

# Create a Pyro object from GEQDSK and SCENE files
# By setting 'gk_code' to "CGYRO", we implicitly load a CGYRO input file template
# All file types are inferred automatically
pyro = Pyro(
    gk_code="CGYRO",
    eq_file="test.geqdsk",
    kinetics_file="scene.cdf",
)

# Generate local Miller parameters at psi_n=0.5
pyro.load_local(psi_n=0.5, local_geometry="Miller")

# Write CGYRO input file using default template
# pyro.write_gk_file(file_name="test_scene.cgyro", gk_code="CGYRO")

# Write single GS2 input file
# pyro.write_gk_file(file_name="test_scene.gs2", gk_code="GS2")

# Write single GENE input file
pyro.write_gk_file(file_name="test_scene.gene", gk_code="GENE")