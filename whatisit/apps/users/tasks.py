from celery import shared_task, Celery

from django.conf import settings
from django.core.mail import EmailMessage
from django.utils import timezone

from whatisit.settings import DOMAIN_NAME
from whatisit.apps.users.models import Team
from whatisit.apps.wordfish.utils import summarize_teams_annotations

from datetime import datetime
import os

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'whatisit.settings')
app = Celery('whatisit')
app.config_from_object('django.conf:settings')
app.autodiscover_tasks(lambda: settings.INSTALLED_APPS)


@app.on_after_configure.connect
def setup_periodic_tasks(sender, **kwargs):
    # Calls test('hello') every 10 seconds.
    #sender.add_periodic_task(10.0, test.s('hello'), name='add every 10')

    # Calls test('world') every 30 seconds
    #sender.add_periodic_task(30.0, test.s('world'), expires=10)

    # Executes every day at 1:30 a.m.
    sender.add_periodic_task(
        crontab(hour=1, minute=30, day_of_week=1),
        update_team_rankings.s(),
    )

@app.task
def update_team_rankings():
    '''update team rankings will calculate ordered rank for all current teams, count annotations,
    and update these fields (with the update date) once a day at 1:30 am (see above)
    '''
    teams = Team.objects.all()
    rankings = summarize_teams_annotations(teams) # sorted list with [(teamid,count)]

    # Iterate through rankings, get team and annotation count
    for g in range(rankings):

        group = rankings[g]
        team_id = group[0]
        rank = g+1 # index starts at 0

        try:
            team = Team.objects.get(id=team_id)
        except:
            # A team not obtainable will be skipped
            continue

        team.annotation_count = group[1]
        team.ranking = rank
        team.metrics_updated_at = datetime.now()        
        team.save()
    

@shared_task
def send_result(eid,wid,data):
    '''send_result is an idea to send data somewhere, not sure if going to use.
    '''
    try:
        # Generate email and send with sendgrid
        email = generate_email(battery,experiment,worker,data)
        sg = SendGridAPIClient(apikey=battery.sendgrid)
        response = sg.client.mail.send.post(request_body=email)
        if response.status_code != 202:
            email_send()
    except:
        email_send()


def email_send():
    '''Might need this to send messages, but will require sendgrid (not set up)
    '''
    subject = "[WORDFISH] Update"
    body = """Hello from WordFish!"""
    to_email = []
    message = EmailMessage(subject=subject,
                           body=body,
                           from_email="",
                           to=to_email)
    message.send()
