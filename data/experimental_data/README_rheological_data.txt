1. Title of Dataset: Rheological_data

2. Folder List: 

Folder Rheological_data contains 13 sub-folders (NameOfExpSet) with data for each experimental set.

NaCl_0.1_XG
NaCl_0.3_XG
NaCl_0.4_XG
NaCl_0.5_XG
NaCl_0.7_XG
NaCl_0_XG
NaCl_0_XG_2019
XG_NaCl_0.1
XG_NaCl_0.3
XG_NaCl_0.05
XG_NaCl_0.5
XG_NaCl_0.7
XG_NaCl_0.9

Dataset NaCl_0_XG_2019 originates from previous study published in Mrokowska and Krztoń-Maziopa, 2019: Viscoelastic and shear-thinning effects of aqueous exopolymer solution on disk and sphere settling. Scientific Reports, 9: 7897, DOI: 10.1038/s41598-019-44233-z

3. Additional related data collected that was not included in the current data package: 
Data on settling of partices in solutions stored in Settling_experiments folder
	
4. Methodological information:
Description of methods used for collection/generation of data: 
Presented in data paper linked to this dataset.
Analysis of data presented in a research paper linked to this dataset. 

5. Data-specific information for [sub-folders: NameOfExpSet]

Each sub-folder (NameOfExpSet) contains four *.csv files: 
- flow properties: flow_data_NameOfExpSet.csv 
variables stored in three columns: shear rate [1/s], shear stress [Pa], viscosity [Pa s], torque [µN m].
- amplitude sweeps: ampl_sweeps_NameOfExpSet.csv 
variables stored in four columns: strain [%], shear stress [Pa], storage modulus [Pa], loss modulus [Pa]. 
- frequency sweeps: frequency_sweep_NameOfExpSet.csv 
variables stored in three columns: frequency [Hz], storage modulus [Pa], loss modulus [Pa]. 
- first normal stress difference: normal_stress_NameOfExpSet.csv 
variables stored in three columns: strain [%], 1st Norm. Str. Diff. (Lodge-Meissner) [Pa], shear stress [Pa].








