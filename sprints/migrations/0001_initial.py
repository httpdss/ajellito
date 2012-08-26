# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Adding model 'Sprints'
        db.create_table('sprints_sprints', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('date_from', self.gf('django.db.models.fields.DateTimeField')()),
            ('date_to', self.gf('django.db.models.fields.DateTimeField')()),
            ('max_develop', self.gf('django.db.models.fields.IntegerField')()),
        ))
        db.send_create_signal('sprints', ['Sprints'])


    def backwards(self, orm):
        
        # Deleting model 'Sprints'
        db.delete_table('sprints_sprints')


    models = {
        'sprints.sprints': {
            'Meta': {'object_name': 'Sprints'},
            'date_from': ('django.db.models.fields.DateTimeField', [], {}),
            'date_to': ('django.db.models.fields.DateTimeField', [], {}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'max_develop': ('django.db.models.fields.IntegerField', [], {})
        }
    }

    complete_apps = ['sprints']
