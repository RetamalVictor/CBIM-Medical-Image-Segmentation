#!/bin/bash

#SBATCH --partition=gpu
#SBATCH --gres=gpu:1
#SBATCH --job-name=TestTraining_2
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=3
#SBATCH --time=00:30:00
#SBATCH --mem=32000M
#SBATCH --output=/home/vretamal/CBIM-Medical-Image-Segmentation/AImed/Slurm_results/test%A.out

module purge
module load 2021
module load Anaconda3/2021.05

cd $HOME/CBIM-Medical-Image-Segmentation/

source activate anne

python training_pipeline.py