#!/bin/bash

gunicorn -w 1 --threads 1 -b 0.0.0.0:8080 --timeout 600 service:app 
