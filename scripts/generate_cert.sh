#! /bin/bash
# taken and slightly modified from https://www.metachris.com/2015/12/comparison-of-10-acme-lets-encrypt-clients/

cd $HOME
sudo mkdir /opt/acme_tiny
git clone https://github.com/diafygi/acme-tiny
sudo mv acme-tiny /opt/acme-tiny/
sudo chown $USER -R /opt/acme-tiny

# Create a directory for the keys and cert
cd $HOME/whatisit
docker-compose stop nginx
sudo service nginx start
DOMAIN=word.fish
cd /etc/ssl/certs

# backup old key and cert
cp /etc/ssl/private/domain.key{,.bak.$(date +%s)}
cp chained.pem{,.bak.$(date +%s)}

# Generate a private key
openssl genrsa 4096 > account.key
sudo mv account.key /etc/ssl/certs

# Generate a domain private key (if you haven't already)
openssl genrsa 4096 > domain.key
sudo mv domain.key /etc/ssl/private

# Add extra security
openssl dhparam -out dhparam.pem 4096
sudo mv dhparam.pem /etc/ssl/certs

# Create a CSR for $DOMAIN
sudo openssl req -new -sha256 -key /etc/ssl/private/domain.key -subj "/CN=$DOMAIN" > domain.csr
sudo mv domain.csr /etc/ssl/certs/domain.csr

# Create the challenge folder in the webroot
sudo mkdir -p /var/www/html/.well-known/acme-challenge/
sudo chown $USER -R /var/www/html/

# Get a signed certificate with acme-tiny
python /opt/acme-tiny/acme_tiny.py --account-key /etc/ssl/certs/account.key --csr /etc/ssl/certs/domain.csr --acme-dir /var/www/html/.well-known/acme-challenge/ > ./signed.crt

wget -O - https://letsencrypt.org/certs/lets-encrypt-x3-cross-signed.pem > intermediate.pem
cat signed.crt intermediate.pem > chained.pem
sudo mv chained.pem /etc/ssl/certs/

# You will also need to use the https nginx conf
# cd $HOME/whatisit
# mv nginx.conf nginx.conf.http
# mv nginx.conf.https nginx.conf

# Restart nginx container
sudo service nginx stop
cd $HOME/whatisit
docker-compose restart nginx

