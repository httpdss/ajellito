rm -rf dist
git clone git://github.com/friflaj/ajellito.git dist
cd dist
python agilito/install.py --install=auto --nosqldiff
python manage.py syncdb
cd ..
