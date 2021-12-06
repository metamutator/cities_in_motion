# Live App
The app is live at [this location](https://share.streamlit.io/metamutator/cities_in_motion/main/streamlit.py) and is being supported currently.


# Running the code locally
Alternatively, you may choose to clone the code and execute it locally. To do so, 
1. Clone / download the repo.
2. Next, you want to create a conda environment with all the necessary libraries. The easiest way to do this is to execute the following at a terminal of your choice (for instance, the terminal within Visual Studio Code) ``conda env create -f cities_env.yml`` 
2. Activate the environment in the terminal ( ``conda activate cities_in_motion``) 
3. Install further python dependencies that conda may not have picked up ( ``pip install -r requirements.txt`` )
4. Hit ``streamlit run streamlit.py`` This should open up the app in your browser.

If you still have trouble with dependencies, try running ``pip3 install -r requirements.txt``. This is so especially if you have a parallel Python 2 installation.
