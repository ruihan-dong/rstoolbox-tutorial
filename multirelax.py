# Relax n design outputs via multiprocess running
# 22/05/25

import matplotlib
matplotlib.use("Agg")

import os
import rstoolbox as rs

from pyrosetta import *
from pyrosetta.rosetta import *
from pyrosetta.teaching import *
from pyrosetta.rosetta.protocols.relax import FastRelax


# define multiprocessing firstly
use_multiprocessing = True
if use_multiprocessing:
    import multiprocessing
    max_cpus = 4 # We might want to not run on the full number of cores, as Rosetta take about 2 Gb of memory per instance


# FastRelax
def relax(input_tag):
    pose = pose_from_pdb(input_tag + '.pdb')
    original_pose = pose.clone()
    scorefxn = get_score_function()

    fr = FastRelax(standard_repeats=10)
    fr.set_scorefxn(scorefxn)

    if not os.getenv("DEBUG"):
       fr.apply(pose)
   
    score_before = scorefxn(original_pose)
    score_after = scorefxn(pose)

    output_pdb = input_tag + '_relaxed.pdb'
    pose.dump_pdb(output_pdb)
    print('save ', output_pdb)

    log_path = os.path.join('relaxed_score.out')
    with open(log_path, 'a') as log_file:
        log_file.writelines([input_tag, ' ', str(score_before), ' ', str(score_after), '\n'])


# Filter structs with lowest n scores
def filter_pdbs(silent_file, n):
    score_def = {'scores':['score', 'finalRMSD','packstat', 'description'],'naming': ['', 'bb']}
    df = rs.io.parse_rosetta_file(silent_file, score_def)
    pck = df[(df["finalRMSD"] < 3) & (df["packstat"] > 0.6)]
    lowestN = pck.sort_values('score').head(n)
    tag_list = lowestN['description']
    return tag_list


# extract pdbs
def extract_pdbs(silent_file, tag_list):
    pdb_path = '/opt/software/rosetta.source.release-296/main/source/bin/extract_pdbs.mpi.linuxgccrelease '
    pdb_flags = '-in:file:silent ' + silent_file +' -in:file:silent_struct_type binary -in:file:tags '
    for tag in tag_list:
        os.system(pdb_path + pdb_flags + tag)
        print("save "+ tag + '.pdb')


if __name__ == '__main__':
    # define the input silent file
    silent_file = '3H_B2H_A1H_B1H'
    tag_list = filter_pdbs(silent_file, 10)
    extract_pdbs(silent_file, tag_list)

    init('-ignore_unrecognized_res -ignore_zero_occupancy false -load_PDB_components false -relax:default_repeats 5  -ex1 -ex2aro')
    
    if use_multiprocessing:
        pool = multiprocessing.Pool(processes = min(max_cpus, multiprocessing.cpu_count()))
        for tag in tag_list:
            pool.apply_async(relax, args=(tag,))
        pool.close()
        pool.join()
    else:
        for tag in tag_list:
            relax(tag)
        


