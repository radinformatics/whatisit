#!/bin/sh

# Prepare Google Cloud/ etc instance for whatisit (mostly just Docker and cloning repo)

sudo apt-get update > /dev/null
sudo apt-get install -y --force-yes git 
sudo apt-get install -y --force-yes build-essential
sudo apt-get install -y --force-yes nginx
sudo apt-get install -y --force-yes python-dev

# Needed module for system python
wget https://bootstrap.pypa.io/get-pip.py
sudo /usr/bin/python get-pip.py
sudo pip install ipaddress
sudo pip install oauth2client


# Python 3
wget https://repo.continuum.io/archive/Anaconda3-4.2.0-Linux-x86_64.sh
bash Anaconda3-4.2.0-Linux-x86_64.sh -b
echo "PATH=\$HOME/anaconda3/bin:\$PATH" >> $HOME/.profile
echo export PATH >> $HOME/.bashrc
rm Anaconda2-4.2.0-Linux-x86_64.sh
source $HOME/.bashrc
pip install ipaddress

# Add docker key server
sudo apt-key adv --keyserver hkp://p80.pool.sks-keyservers.net:80 --recv-keys 58118E89F3A912897C070ADBF76221572C52609D

# Install Docker!
sudo apt-get update
sudo apt-get install apt-transport-https ca-certificates
sudo apt-key adv --keyserver hkp://p80.pool.sks-keyservers.net:80 --recv-keys 58118E89F3A912897C070ADBF76221572C52609D
echo "deb https://apt.dockerproject.org/repo ubuntu-xenial main" | sudo tee --append /etc/apt/sources.list.d/docker.list
sudo apt-get update
apt-cache policy docker-engine
sudo apt-get update
sudo apt-get -y install linux-image-extra-$(uname -r) linux-image-extra-virtual
sudo apt-get -y install docker-engine
sudo service docker start
#sudo docker run hello-world
sudo usermod -aG docker $USER

# Docker-compose
sudo apt -y install docker-compose

# Note that you will need to log in and out for changes to take effect

if [ ! -d $HOME/whatisit ]
then
  cd $HOME
  git clone https://github.com/radinformations/whatisit
  cd whatisit
  docker build -t vanessa/whatisit .
  docker-compose -d up
fi
