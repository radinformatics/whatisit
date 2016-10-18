# Whatisit

**under development**

This will be the start of (some) collaborative annotation interface for de-identified radiologist reports.

![img/whatisit.png](img/whatisit.png)


## Development

You will want to [install Docker](https://docs.docker.com/engine/installation/) and [docker-compose](https://docs.docker.com/compose/install/) and then build the image locally:


      docker build -t vanessa/whatisit .


Then start the application:

      docker-compose up -d


### Loading Test Data
The test dataset consists of reports and annotations for ~100K radiologist reports from Stanford Medicine, de-identified (and data is NOT available in this repo). To load the data, you should use the script [scripts/upload_demo.py](scripts/upload_demo.py). First send the command to the instance to run the script:


      docker exec [containerID] python manage.py shell < scripts/upload_demo.py


Where `containerID` corresponds to the container ID obtained from `docker ps`. If you have any trouble with the script (errors, etc) you can connect to the container interactively via:


      docker exec -it [containerID] bash


