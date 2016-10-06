# topfree

requirement:
1. sudo service mongod start
2. sudo pip install lxml.html
3. sudo pip install pymongo

enter the small-googleplay directory and type

python Bootstrapper.py Input/bootstrapping_terms.xml2
python Worker.py

wait until it finished, then type

cd .. /n
python print2json.py

It will generate a file called topfree.json, and it's what we want
If necessary, modify the Input/bootstrapping_terms.xml2 to change the strapping rank list
