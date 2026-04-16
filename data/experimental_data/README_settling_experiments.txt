1. Title of Dataset: Settling_experiments

2. Folder List: 

Folder Settling_experiments contains 11 sub-folders (NameOfExpSet) with data for each experimental set.

NaCl_0.1_XG
NaCl_0.3_XG
NaCl_0.4_XG
NaCl_0.5_XG
NaCl_0.7_XG
NaCl_0_XG_2019
XG_NaCl_0.1
XG_NaCl_0.3
XG_NaCl_0.5
XG_NaCl_0.7
XG_NaCl_0.9

Dataset NaCl_0_XG_2019 comes from previous study published in Mrokowska and Krztoń-Maziopa, 2019: Viscoelastic and shear-thinning effects of aqueous exopolymer solution on disk and sphere settling. Scientific Reports, 9: 7897, DOI: 10.1038/s41598-019-44233-z

3. Additional related data collected that was not included in the current data package: 
Data on rheological properties of solutions stored in Rheological_data folder
	
4. Methodological information:

Description of methods used for collection/generation of data: 
Presented in a paper linked to this dataset.
Analysis of data presented in a research paper linked to this dataset.

5. Data-specific information [sub-folders: NameOfExpSet]
 
Each sub-folder contains the following files:
- NameOfExpSet_conditions.csv file with 4 columns: run, run_particle, frame_rate [fps], particle_type, where run column includes the number of experimental run, run_particle indicates the number of run for a particular type of particle,  particle_type includes information on the particle type in the following format: P_d where P indicates type of particle (S – sphere, D – disk) and d indicates the particle diameter in millimetres.
- several .csv files (equal to the number of all runs in the experimental set) called NameOfExpSet_ParticleType_run_RunParticle.csv, where ParticleType is in  the following format Pd where P indicates type of particle (S – sphere, D – disk) and d indicates the particle diameter in millimetres, RunParticle indicates the number of run for the particular type of particle. 
Files contain data on the position of particle centroid in time in three columns: x [pix], z [pix], t[s], where x, z are horizontal and vertical coordinates, t - time instant. 









