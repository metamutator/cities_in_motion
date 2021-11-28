# Setup
You want to create a conda environment first with all the necessary libraries. The easiest way to do this is to executing the following at a terminal of your choice (I usually use the terminal within Visual Studio Code):
``conda env create -f cities_env.yml``

# Files to ignore
Don't bother about the Jupyter notebook files. We'll clean those up as we stabilize the code. 

# Running the app
1. Clone the repo.
2. Create a conda environment using the YML file (as stated above)
3. Activate the environment in the terminal ( ``conda activate cities_in_motion``) 
4. Hit ``streamlit run viewer.py`` (or ``streamlit.py`` for now)
