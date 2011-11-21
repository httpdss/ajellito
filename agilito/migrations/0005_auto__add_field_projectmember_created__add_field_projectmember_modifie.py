# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Adding field 'ProjectMember.created'
        db.add_column('agilito_projectmember', 'created', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, null=True, blank=True), keep_default=False)

        # Adding field 'ProjectMember.modified'
        db.add_column('agilito_projectmember', 'modified', self.gf('django.db.models.fields.DateTimeField')(auto_now=True, null=True, blank=True), keep_default=False)


    def backwards(self, orm):
        
        # Deleting field 'ProjectMember.created'
        db.delete_column('agilito_projectmember', 'created')

        # Deleting field 'ProjectMember.modified'
        db.delete_column('agilito_projectmember', 'modified')


    models = {
        'agilito.archivedbacklog': {
            'Meta': {'ordering': "('-stamp',)", 'object_name': 'ArchivedBacklog'},
            'commit': ('django.db.models.fields.TextField', [], {}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'project': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['agilito.Project']"}),
            'stamp': ('django.db.models.fields.DateTimeField', [], {})
        },
        'agilito.impediment': {
            'Meta': {'ordering': "('-opened',)", 'object_name': 'Impediment'},
            'description': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'opened': ('django.db.models.fields.DateField', [], {'default': 'datetime.datetime.now'}),
            'resolved': ('django.db.models.fields.DateTimeField', [], {'null': 'True'}),
            'tasks': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['agilito.Task']", 'symmetrical': 'False'})
        },
        'agilito.iteration': {
            'Meta': {'ordering': "('start_date',)", 'object_name': 'Iteration'},
            'description': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'end_date': ('django.db.models.fields.DateField', [], {}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'project': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['agilito.Project']"}),
            'release': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['agilito.Release']", 'null': 'True', 'blank': 'True'}),
            'start_date': ('django.db.models.fields.DateField', [], {})
        },
        'agilito.project': {
            'Meta': {'ordering': "('id',)", 'object_name': 'Project'},
            'description': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'project_members': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'to': "orm['auth.User']", 'null': 'True', 'blank': 'True'}),
            'visibility': ('django.db.models.fields.IntegerField', [], {'default': '2'})
        },
        'agilito.projectmember': {
            'Meta': {'unique_together': "(('user', 'project', 'role'),)", 'object_name': 'ProjectMember'},
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'null': 'True', 'blank': 'True'}),
            'project': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['agilito.Project']"}),
            'role': ('django.db.models.fields.SmallIntegerField', [], {'default': '99'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']"})
        },
        'agilito.release': {
            'Meta': {'ordering': "('rank',)", 'object_name': 'Release'},
            'deadline': ('django.db.models.fields.DateField', [], {'null': 'True', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'project': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['agilito.Project']"}),
            'rank': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'})
        },
        'agilito.task': {
            'Meta': {'ordering': "('user_story__rank', 'user_story__id', 'id')", 'object_name': 'Task'},
            'category': ('django.db.models.fields.SmallIntegerField', [], {'default': '0'}),
            'description': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'estimate': ('django.db.models.fields.FloatField', [], {'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'owner': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']", 'null': 'True', 'blank': 'True'}),
            'remaining': ('django.db.models.fields.FloatField', [], {'null': 'True', 'blank': 'True'}),
            'state': ('django.db.models.fields.SmallIntegerField', [], {'default': '10'}),
            'tags': ('tagging.fields.TagField', [], {}),
            'user_story': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['agilito.UserStory']"})
        },
        'agilito.tasklog': {
            'Meta': {'object_name': 'TaskLog'},
            'date': ('django.db.models.fields.DateTimeField', [], {}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'iteration': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['agilito.Iteration']", 'null': 'True'}),
            'old_remaining': ('django.db.models.fields.FloatField', [], {'null': 'True', 'blank': 'True'}),
            'owner': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']"}),
            'summary': ('django.db.models.fields.TextField', [], {}),
            'task': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['agilito.Task']"}),
            'time_on_task': ('django.db.models.fields.FloatField', [], {})
        },
        'agilito.testcase': {
            'Meta': {'ordering': "('-priority',)", 'object_name': 'TestCase'},
            'description': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'postcondition': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'precondition': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'priority': ('django.db.models.fields.SmallIntegerField', [], {'default': '20', 'null': 'True', 'blank': 'True'}),
            'steps': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'user_story': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['agilito.UserStory']"})
        },
        'agilito.testresult': {
            'Meta': {'ordering': "('-date',)", 'object_name': 'TestResult'},
            'comments': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'date': ('django.db.models.fields.DateTimeField', [], {}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'result': ('django.db.models.fields.SmallIntegerField', [], {}),
            'test_case': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['agilito.TestCase']"}),
            'tester': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']"})
        },
        'agilito.userprofile': {
            'Meta': {'object_name': 'UserProfile'},
            'category': ('django.db.models.fields.SmallIntegerField', [], {}),
            'hours_per_week': ('django.db.models.fields.SmallIntegerField', [], {}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']", 'unique': 'True'})
        },
        'agilito.userstory': {
            'Meta': {'ordering': "('rank', 'id')", 'object_name': 'UserStory'},
            'closed': ('django.db.models.fields.DateField', [], {'null': 'True'}),
            'copied_from': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['agilito.UserStory']", 'null': 'True'}),
            'created': ('django.db.models.fields.DateField', [], {'default': 'datetime.datetime.now'}),
            'description': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'iteration': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['agilito.Iteration']", 'null': 'True', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'project': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['agilito.Project']"}),
            'rank': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'size': ('django.db.models.fields.SmallIntegerField', [], {'null': 'True'}),
            'state': ('django.db.models.fields.SmallIntegerField', [], {'default': '10'}),
            'tags': ('tagging.fields.TagField', [], {})
        },
        'agilito.userstoryattachment': {
            'Meta': {'object_name': 'UserStoryAttachment'},
            'attachment': ('django.db.models.fields.files.FileField', [], {'max_length': '100'}),
            'description': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'original_name': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'user_story': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['agilito.UserStory']"})
        },
        'auth.group': {
            'Meta': {'object_name': 'Group'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        'auth.permission': {
            'Meta': {'ordering': "('content_type__app_label', 'content_type__model', 'codename')", 'unique_together': "(('content_type', 'codename'),)", 'object_name': 'Permission'},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'auth.user': {
            'Meta': {'object_name': 'User'},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Group']", 'symmetrical': 'False', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        }
    }

    complete_apps = ['agilito']
