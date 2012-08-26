from django.conf.urls.defaults import *

urlpatterns = patterns('',
    url(r'^$', 'tickets.views.index', name="tickets-index"),
    url(r'^tododevel/(?P<ticket_id>\d+)/$', 'tickets.views.movetododevel', name="tickets-movetododevel"),
    url(r'^develdone/(?P<ticket_id>\d+)/$', 'tickets.views.movedeveldone', name="tickets-movedeveldone"),
    url(r'^addticket/$', 'tickets.views.addticket', name="tickets-addticket"),
    url(r'^ticketdetail/(?P<ticket_id>\d+)/$', 'tickets.views.detail', name="tickets-detail"),
    url(r'^ticketedit/$', 'tickets.views.edit', name="tickets-edit"),
    url(r'^ticketremove/(?P<ticket_id>\d+)/$', 'tickets.views.delete', name="tickets-delete"),
)
