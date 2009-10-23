agilito\install\windows\dbuilder.py -jp -f agilito\install\windows\dbuilder.conf .
cd dist
del settings.py
python\python.exe agilito\install.py --install=auto --nosqldiff
python\python.exe manage.py syncdb
cd ..
