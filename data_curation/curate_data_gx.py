import os
import glob 
import shutil

parent_dir = '/Users/venkitesh_work/Documents/work/Sapient_AI/Data/mgkdb_data/pyro_tests_data/data/'
source_dir = parent_dir+'test_gx/6_more_runs'
target_dir = parent_dir+'test_gx/7_test_curation/'

# Get list of sub directories
lst = sorted(glob.glob(source_dir+'/sim00*'))
print(lst)

for fldr in lst:
    ## Create subdirectories in new location
    os.makedirs(os.path.join(target_dir,os.path.basename(fldr)),exist_ok=True)
    for file in os.listdir(fldr):
        # print(file)
        prefix = 'cyclone'
        dict1 = {f'{prefix}.in': 'gx.in',f'{prefix}.out.nc':'gx.out.nc',f'{prefix}.big.nc':'gx.big.nc'}
        if file not in dict1.keys():
            continue
        else:
            new_fname = dict1[file]

        source_path = os.path.join(fldr,file)
        dest_path   = os.path.join(target_dir,os.path.basename(fldr),new_fname)
        
        print(source_path,dest_path)

        shutil.copy2(source_path,dest_path)