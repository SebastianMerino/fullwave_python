#!/usr/bin/bash
#SBATCH --gpus-per-node=1
#SBATCH --nodes=1
#SBATCH --nodelist=worker10
#SBATCH --partition=thinkstation-p360
#SBATCH --output="slurm-%j.out"

. /etc/profile.d/modules.sh
module load msma-fullwave/1.0
export PYTHONPATH=/mnt/nfs/smerino/fullwave_python:$PYTHONPATH
srun python /mnt/nfs/smerino/fullwave_python/my_scripts/plane_wave.py

