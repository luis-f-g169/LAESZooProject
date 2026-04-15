# LAESZooProject

Repo for storing our LAES Zoo 1 project.

# Description

This app is designed to be run locally and then used. via the browser of another device.

# build app

docker build -t animal-app .

# Run app

docker run -p 8443:8443 animal-app

# Access the app via your browser on your phone (MUST BE ON SAME WIFI)

https://<YOUR-IP>:8443

# To get ur IP

ifconfig | grep inet
