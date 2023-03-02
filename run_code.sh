#!/bin/bash

#SBATCH --partition=gpu
#SBATCH --gres=gpu:1
#SBATCH --job-name=TestTraining_1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=3
#SBATCH --time=02:00:00
#SBATCH --mem=32000M
#SBATCH --output=test%A.out

module purge
module load 2021
module load Anaconda3/2021.05

cd $HOME/CBIM-Medical-Image-Segmentation/

source activate anne

python training_pipeline.py