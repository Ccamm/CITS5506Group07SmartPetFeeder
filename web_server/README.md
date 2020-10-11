# Web Server

The Web Server is the frontend resource that pet owners interactive with to view the collected data from their pet feeders, update schedules or schedule an immediate drop.

The web framework that is used is [Python Flask](https://palletsprojects.com/p/flask/) and the design is built on top of the [HTML5 Up template called Massively](https://html5up.net/massively). [Chart.js](https://www.chartjs.org/) was the JavaScript library used to render the graphs of the consumed food amounts for each pet feeder.

## Installation and Running the Web Server

First create a new Python 3.6 virtual environment to install the dependencies too. When the virtual environment is created, activate the virtual env and install the dependencies using the following command.

```pip install -r requirements.txt```

The Database API also has to be installed in the virtual env, which can be done by navigating to [the database_api folder](../database_api) and running the following command with the virtual env activated.

```python setup.py install```

You can start the web server running on your local machine by runnning the command `./start_testserver.sh` and view the website in your browser at `http://127.0.0.1:5000`.

To deploy in the cloud, create a Unix virtual machine (we used a Debian virtual machine on Google Cloud for this project). We used `NGINX` as the reverse proxy to access the website. Move the files to `/var/www/web_server/` (you can change this location if you want to).

#### Deployment Files

/etc/systemd/system/web.service
```
[Unit]
Description=Pet Feeder Web Server
After=network.service


[Service]
User=www-data
Group=www-data
WorkingDirectory=/var/www/web_server
Environment="PATH=/var/www/web_server/web_venv/bin"
ExecStart=/var/www/web_server/web_venv/bin/gunicorn --bind unix:web.sock -m 007 wsgi:app
Restart=always

[Install]
WantedBy=multi-user.target
```

NGINX files in `sites-available` and `site-enabled`
```
server {
	listen 80;
	server_name <ip address or domain of your server>;

	location / {
		include proxy_params;
		proxy_pass http://unix:/var/www/web_server/web.sock;
	}
}
```
