#!/bin/bash
source '../../web_venv/bin/activate';
export FLASK_APP=web;
flask run --with-threads -p 5000 -h 127.0.0.1;
