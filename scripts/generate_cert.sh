#! /bin/bash
# taken and slightly modified from https://www.metachris.com/2015/12/comparison-of-10-acme-lets-encrypt-clients/

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

# Generate a domain private key (if you haven't already)
openssl genrsa 4096 > domain.key

# Add extra security
openssl dhparam -out dhparam.pem 4096

# Create a CSR for $DOMAIN
sudo openssl req -new -sha256 -key /etc/ssl/private/domain.key -subj "/CN=$DOMAIN" > domain.csr

# Create the challenge folder in the webroot
mkdir -p /var/www/html/.well-known/acme-challenge/

# Get a signed certificate with acme-tiny
python /opt/acme-tiny/acme_tiny.py --account-key /etc/ssl/certs/account.key --csr /etc/ssl/certs/domain.csr --acme-dir /var/www/html/.well-known/acme-challenge/ > ./signed.crt

wget -O - https://letsencrypt.org/certs/lets-encrypt-x3-cross-signed.pem > intermediate.pem
cat signed.crt intermediate.pem > chained.pem

# Restart nginx container
sudo service nginx stop
cd /home/vanessa/word-fish
docker-compose restart nginx
