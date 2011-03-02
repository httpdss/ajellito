from tastypie.resources import ModelResource
from agilito.models import Project


class ProjectResource(ModelResource):
    class Meta:
        queryset = Project.objects.all()
