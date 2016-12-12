# Whatisit

**under development**

This will be the start of (some) collaborative annotation interface for de-identified radiologist reports.

![img/whatisit.png](img/whatisit.png)


## Development

You will want to [install Docker](https://docs.docker.com/engine/installation/) and [docker-compose](https://docs.docker.com/compose/install/) and then build the image locally:


      docker build -t vanessa/whatisit .


Then start the application:

      docker-compose up -d


### Copying Data
Here is an example of using the `gcloud` util to copy data TO LOCAL:

      gcloud compute copy-files wordfish:$HOME/whatisit/scripts/stanford_pe.tsv $PWD/scripts/stanford_pe.tsv --zone us-west1-b --project='som-xxxxxxxx'


or FROM local TO machine:

      gcloud compute copy-files $PWD/scripts/stanford_pe.tsv wordfish:$HOME/whatisit/scripts/stanford_pe.tsv --zone us-west1-b --project='som-xxxxxxxx'


### Domain Name
It's up to you to buy a domain from a registrar, and then go into your hosting account to add the A and CNAME records, and then update the DNS servers. Since every host is a little different, I'll leave this up to you, but [here is how I did it on Google Cloud](https://cloud.google.com/dns/quickstart).


### SSL
You will need to use letsencrypt (following [these instructions](scripts/generate_cred.md)) to get your initial certificate. You will need to install nginx on the server (not in the Docker image) and then start it:

      sudo apt-get install -y nginx

Then (not in the Docker image, but on the instance), start up nginx:

     sudo service nginx start

Now we are ready to ping to get credentials! Basically, follow the commands, one at a time, [here](scripts/generate_cred.sh).

I think (eventually) this can be done automatically, or better yet, with Google Cloud, but this should work in the meantime. Eg, something like:

      sudo apt-get install letsencrypt
      sudo letsencrypt certonly --webroot -w /etc/ssl/certs -d word.fish -d www.word.fish
      sudo letsencrypt renew 

or something like that!

The server isn't by default ready for ssl, you should rename [nginx.conf.https](nginx.conf.https) to [nginx.conf](nginx.conf) to make it so. This is to ensure that it works smoothly for development, with a little extra work to get it into production.


### Server Errors
The current application is setup to use [opbeat](http://www.opbeat.com) to log errors. The installed applications and middleware are configured in settings.py, and you will need to register an application and add the `OPBEAT` variable (with your application ID) to the `secrets.py`. Speaking of...


### Secrets
There should be a file called `secrets.py` in the [whatisit](whatisit) folder, in which you will store the application secret and other social login credentials. First, create this file, and add the following variables:


#### Django secret key
You can use the [secret key generator](http://www.miniwebtool.com/django-secret-key-generator/) to make a new secret key, and call it `SECRET_KEY` in your `secrets.py` file, like this:

      
          SECRET_KEY = 'xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx'


#### Lockdown
The entire site will be locked down with a password, in addition to requiring login. To set this up, you should add a `LOCKDOWN_PASSWORDS` variable to your `secrets.py`, which is a tuple (so you can have one or more):


      LOCKDOWN_PASSWORDS = ('ifIonlywereafish',)


For developers: note that the module has [substantial customization](https://github.com/Dunedan/django-lockdown) if you want to lockdown only a portion of the site. Note that if/when you want to disable lockdown, simple set the variable `LOCKDOWN_ENABLED=False` in [settings.py](whatisit/settings.py).


#### Setting up Social Logins
For users to connect to Github, you need to [register a new application](https://github.com/settings/applications/new), and add the key and secret to your `secrets.py` file like this: 


      http://psa.matiasaguirre.net/docs/backends/github.html?highlight=github
      SOCIAL_AUTH_GITHUB_KEY = ''
      SOCIAL_AUTH_GITHUB_SECRET = ''
      SOCIAL_AUTH_GITHUB_SCOPE = ["repo","user"]


Specification of the scope as 'user' and 'repo' is hugely important, because we can't make webhooks without write access to the repo! Note that the integration is commented out in the login template for twitter login, and this is done so that users authenticate with Google or Github from the getgo, since we need both for storage and repos, respectively. If you want to develop something / change this, you can add those OAUTH credentials as well, in this format:


      # http://psa.matiasaguirre.net/docs/backends/twitter.html?highlight=twitter
      SOCIAL_AUTH_TWITTER_KEY = ''
      SOCIAL_AUTH_TWITTER_SECRET = ''

Read more about the different [backend here](http://psa.matiasaguirre.net/docs/backends).


### Create a User
You will want to create a user (other than anonymous) for associating with the first collection of reports to upload. You can do this by navigating to `127.0.0.1` and clicking the button to Register. Currently supported backends (meaning we have OAuth2 tokens for them) are Twitter and Github. Once you've logged in, your user is created!


### Loading Test Data
The test dataset consists of reports and annotations for ~100K radiologist reports from Stanford Medicine, de-identified (and data is NOT available in this repo). To load the data, you should first push it to the instance, like this:

      cd whatisit/scripts
      gcloud compute copy-files data.tsv whatisit-wordfish:/home/vanessa/whatisit/scripts --zone us-west1-a


And then, after starting the application, use the script [scripts/upload_demo.py](scripts/upload_demo.py). First send the command to the instance to run the script:


      docker exec [containerID] python manage.py shell < scripts/upload_demo.py


Where `containerID` corresponds to the container ID obtained from `docker ps`. If you have any trouble with the script (errors, etc) you can connect to the container interactively via:


      docker exec -it [containerID] bash


The collection will be associated with the first user created, and you should edit the script if you want this to be different.
