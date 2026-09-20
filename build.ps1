# build.ps1
.\venv\Scripts\Activate.ps1
pyinstaller --noconfirm --onedir --windowed --add-data "nifty200_symbols.csv;." --add-data "ai_brain.pkl.gz;." --hidden-import sklearn --hidden-import sklearn.ensemble --hidden-import sklearn.tree --hidden-import sklearn.metrics --hidden-import scipy main.py

