from django.db import models
import datetime
#from users.models import Users
from django.contrib.auth.models import User
from table.models import Tables

class Tickets(models.Model):
    tables = models.ManyToManyField(Tables)
    users = models.ManyToManyField(User)
    service = models.CharField(max_length=99)
    cmlurl = models.URLField(max_length=200, null=True, blank=True,)
    difficulty = models.IntegerField()
    description = models.TextField()
    pub_date = models.DateTimeField('date_published', auto_now_add=True)
    devel_date = models.DateTimeField('date_devel', auto_now=False, auto_now_add=False, null=True, blank=True)
    done_date = models.DateTimeField('date_done', auto_now=False, auto_now_add=False, null=True, blank=True)

    def was_published_today(self):
        return self.pub_date.date() == datetime.time.today()

    was_published_today.short_description = 'Posted today?'

    def __unicode__(self):
        return self.service
