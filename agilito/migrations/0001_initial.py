# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Adding model 'Project'
        db.create_table('agilito_project', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=200)),
            ('description', self.gf('django.db.models.fields.TextField')(blank=True)),
            ('visibility', self.gf('django.db.models.fields.IntegerField')(default=2)),
        ))
        db.send_create_signal('agilito', ['Project'])

        # Adding M2M table for field project_members on 'Project'
        db.create_table('agilito_project_project_members', (
            ('id', models.AutoField(verbose_name='ID', primary_key=True, auto_created=True)),
            ('project', models.ForeignKey(orm['agilito.project'], null=False)),
            ('user', models.ForeignKey(orm['auth.user'], null=False))
        ))
        db.create_unique('agilito_project_project_members', ['project_id', 'user_id'])

        # Adding model 'Release'
        db.create_table('agilito_release', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=200)),
            ('description', self.gf('django.db.models.fields.TextField')(blank=True)),
            ('project', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['agilito.Project'])),
            ('rank', self.gf('django.db.models.fields.IntegerField')(null=True, blank=True)),
            ('deadline', self.gf('django.db.models.fields.DateField')(null=True, blank=True)),
        ))
        db.send_create_signal('agilito', ['Release'])

        # Adding model 'Iteration'
        db.create_table('agilito_iteration', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=200)),
            ('description', self.gf('django.db.models.fields.TextField')(blank=True)),
            ('start_date', self.gf('django.db.models.fields.DateField')()),
            ('end_date', self.gf('django.db.models.fields.DateField')()),
            ('release', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['agilito.Release'], null=True, blank=True)),
            ('project', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['agilito.Project'])),
        ))
        db.send_create_signal('agilito', ['Iteration'])

        # Adding model 'UserStoryAttachment'
        db.create_table('agilito_userstoryattachment', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=200)),
            ('description', self.gf('django.db.models.fields.TextField')(blank=True)),
            ('attachment', self.gf('django.db.models.fields.files.FileField')(max_length=100)),
            ('original_name', self.gf('django.db.models.fields.CharField')(max_length=200)),
            ('user_story', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['agilito.UserStory'])),
        ))
        db.send_create_signal('agilito', ['UserStoryAttachment'])

        # Adding model 'UserStory'
        db.create_table('agilito_userstory', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=200)),
            ('description', self.gf('django.db.models.fields.TextField')(blank=True)),
            ('project', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['agilito.Project'])),
            ('iteration', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['agilito.Iteration'], null=True, blank=True)),
            ('rank', self.gf('django.db.models.fields.IntegerField')(null=True, blank=True)),
            ('state', self.gf('django.db.models.fields.SmallIntegerField')(default=10)),
            ('size', self.gf('django.db.models.fields.SmallIntegerField')(null=True)),
            ('created', self.gf('django.db.models.fields.DateField')(default=datetime.datetime.now)),
            ('closed', self.gf('django.db.models.fields.DateField')(null=True)),
            ('tags', self.gf('tagging.fields.TagField')()),
            ('copied_from', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['agilito.UserStory'], null=True)),
        ))
        db.send_create_signal('agilito', ['UserStory'])

        # Adding model 'UserProfile'
        db.create_table('agilito_userprofile', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('hours_per_week', self.gf('django.db.models.fields.SmallIntegerField')()),
            ('category', self.gf('django.db.models.fields.SmallIntegerField')()),
            ('user', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['auth.User'], unique=True)),
        ))
        db.send_create_signal('agilito', ['UserProfile'])

        # Adding model 'Task'
        db.create_table('agilito_task', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=200)),
            ('description', self.gf('django.db.models.fields.TextField')(blank=True)),
            ('estimate', self.gf('django.db.models.fields.FloatField')(null=True, blank=True)),
            ('remaining', self.gf('django.db.models.fields.FloatField')(null=True, blank=True)),
            ('state', self.gf('django.db.models.fields.SmallIntegerField')(default=10)),
            ('category', self.gf('django.db.models.fields.SmallIntegerField')(default=0)),
            ('owner', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['auth.User'], null=True, blank=True)),
            ('user_story', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['agilito.UserStory'])),
            ('tags', self.gf('tagging.fields.TagField')()),
        ))
        db.send_create_signal('agilito', ['Task'])

        # Adding model 'TestCase'
        db.create_table('agilito_testcase', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=200)),
            ('description', self.gf('django.db.models.fields.TextField')(blank=True)),
            ('user_story', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['agilito.UserStory'])),
            ('priority', self.gf('django.db.models.fields.SmallIntegerField')(default=20, null=True, blank=True)),
            ('precondition', self.gf('django.db.models.fields.TextField')(blank=True)),
            ('steps', self.gf('django.db.models.fields.TextField')(blank=True)),
            ('postcondition', self.gf('django.db.models.fields.TextField')(blank=True)),
        ))
        db.send_create_signal('agilito', ['TestCase'])

        # Adding model 'TestResult'
        db.create_table('agilito_testresult', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('result', self.gf('django.db.models.fields.SmallIntegerField')()),
            ('comments', self.gf('django.db.models.fields.TextField')(blank=True)),
            ('date', self.gf('django.db.models.fields.DateTimeField')()),
            ('tester', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['auth.User'])),
            ('test_case', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['agilito.TestCase'])),
        ))
        db.send_create_signal('agilito', ['TestResult'])

        # Adding model 'Impediment'
        db.create_table('agilito_impediment', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=200)),
            ('description', self.gf('django.db.models.fields.TextField')(blank=True)),
            ('opened', self.gf('django.db.models.fields.DateField')(default=datetime.datetime.now)),
            ('resolved', self.gf('django.db.models.fields.DateTimeField')(null=True)),
        ))
        db.send_create_signal('agilito', ['Impediment'])

        # Adding M2M table for field tasks on 'Impediment'
        db.create_table('agilito_impediment_tasks', (
            ('id', models.AutoField(verbose_name='ID', primary_key=True, auto_created=True)),
            ('impediment', models.ForeignKey(orm['agilito.impediment'], null=False)),
            ('task', models.ForeignKey(orm['agilito.task'], null=False))
        ))
        db.create_unique('agilito_impediment_tasks', ['impediment_id', 'task_id'])

        # Adding model 'TaskLog'
        db.create_table('agilito_tasklog', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('task', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['agilito.Task'])),
            ('time_on_task', self.gf('django.db.models.fields.FloatField')()),
            ('summary', self.gf('django.db.models.fields.TextField')()),
            ('date', self.gf('django.db.models.fields.DateTimeField')()),
            ('iteration', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['agilito.Iteration'], null=True)),
            ('owner', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['auth.User'])),
            ('old_remaining', self.gf('django.db.models.fields.FloatField')(null=True, blank=True)),
        ))
        db.send_create_signal('agilito', ['TaskLog'])

        # Adding model 'ArchivedBacklog'
        db.create_table('agilito_archivedbacklog', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('stamp', self.gf('django.db.models.fields.DateTimeField')()),
            ('project', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['agilito.Project'])),
            ('commit', self.gf('django.db.models.fields.TextField')()),
        ))
        db.send_create_signal('agilito', ['ArchivedBacklog'])


    def backwards(self, orm):
        
        # Deleting model 'Project'
        db.delete_table('agilito_project')

        # Removing M2M table for field project_members on 'Project'
        db.delete_table('agilito_project_project_members')

        # Deleting model 'Release'
        db.delete_table('agilito_release')

        # Deleting model 'Iteration'
        db.delete_table('agilito_iteration')

        # Deleting model 'UserStoryAttachment'
        db.delete_table('agilito_userstoryattachment')

        # Deleting model 'UserStory'
        db.delete_table('agilito_userstory')

        # Deleting model 'UserProfile'
        db.delete_table('agilito_userprofile')

        # Deleting model 'Task'
        db.delete_table('agilito_task')

        # Deleting model 'TestCase'
        db.delete_table('agilito_testcase')

        # Deleting model 'TestResult'
        db.delete_table('agilito_testresult')

        # Deleting model 'Impediment'
        db.delete_table('agilito_impediment')

        # Removing M2M table for field tasks on 'Impediment'
        db.delete_table('agilito_impediment_tasks')

        # Deleting model 'TaskLog'
        db.delete_table('agilito_tasklog')

        # Deleting model 'ArchivedBacklog'
        db.delete_table('agilito_archivedbacklog')


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
