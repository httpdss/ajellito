# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Adding model 'Tables'
        db.create_table('table_tables', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=10)),
        ))
        db.send_create_signal('table', ['Tables'])


    def backwards(self, orm):
        
        # Deleting model 'Tables'
        db.delete_table('table_tables')


    models = {
        'table.tables': {
            'Meta': {'object_name': 'Tables'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '10'})
        }
    }

    complete_apps = ['table']
