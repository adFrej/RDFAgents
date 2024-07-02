/home/ejabberd/bin/ejabberdctl start

sleep 5

/home/ejabberd/bin/ejabberdctl register admin localhost password

sleep 1

cd /app
python3 main.py
