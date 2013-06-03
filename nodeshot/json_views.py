# -*- coding: utf-8 -*-
from django.http import HttpResponse, Http404
from django.db.models import Q
from django.utils import simplejson
from django.core.exceptions import ObjectDoesNotExist

from nodeshot.json_serializer import JSONSerializer
from nodeshot.models import *
from nodeshot.forms import *
from nodeshot.utils import jslugify



def nodes(request):
    """
    Returns a json list with all the nodes divided in active, potential and hostspot
    Populates javascript object nodeshot.nodes
    """
    # retrieve nodes in 3 different objects depending on the status
    active = Node.objects.filter(status='a').values('name', 'slug', 'id', 'lng', 'lat', 'status')
    # status ah (active & hotspot) will fall in the hotspot group, having the hotspot icon
    hotspot = Node.objects.filter(Q(status='h') | Q(status='ah')).values('name', 'slug', 'id', 'lng', 'lat', 'status')
    potential = Node.objects.filter(status='p').values('name', 'slug', 'id', 'lng', 'lat', 'status')

    # retrieve links, select_related() reduces the number of queries,
    # only() selects only the fields we need
    # double underscore __ indicates that we are following a foreign key
    link_queryset = Link.objects.all().exclude(hide=True).select_related().only(
        'from_interface__device__node__lat', 'from_interface__device__node__lng',
        'to_interface__device__node__lat', 'to_interface__device__node__lng',
        'to_interface__device__node__name', 'to_interface__device__node__name',
        'etx', 'dbm'
    )
    # evaluate queryset

    # prepare empty list
    links = []
    # loop over queryset (remember: evaluating queryset makes query to the db)
    for l in link_queryset:
        # determining link colour (depending on link quality)
        etx = l.get_quality('etx')
        dbm = l.get_quality('dbm')
        # prepare result
        entry = {
            'from_lng': l.from_interface.device.node.lng,
            'from_lat': l.from_interface.device.node.lat,
            'to_lng': l.to_interface.device.node.lng,
            'to_lat': l.to_interface.device.node.lat,
            # raw values
            'retx': l.etx,
            'rdbm': l.dbm,
            # interpreted values (link quality, can be 1, 2 or 3)
            'etx': etx,
            'dbm': dbm
        }
        # append/push result into list
        links.append(entry)

    #prepare data for json serialization
    active_nodes, hotspot_nodes, potential_nodes = {}, {}, {}
    for node in active:
        node['jslug'] = jslugify(node['slug'])
        active_nodes[jslugify(node['slug'])] = node
    for node in hotspot:
        node['jslug'] = jslugify(node['slug'])
        hotspot_nodes[jslugify(node['slug'])] = node
    for node in potential:
        node['jslug'] = jslugify(node['slug'])
        potential_nodes[jslugify(node['slug'])] = node
    data = {
        'active': active_nodes,
        'hotspot': hotspot_nodes,
        'potential': potential_nodes,
        'links': links
    }
    # return json
    return HttpResponse(simplejson.dumps(data), mimetype='application/json')


def json(request, slug):
    """
    Returns a json description of a node
    """

    # retrieve object or return 404 error
    try:
        node = Node.objects.exclude(status='u')\
            .values('name', 'slug', 'id', 'lng', 'lat', 'status', 'notes')\
            .defer(None)\
            .get(slug=slug)
        node_id = node['id']
    except ObjectDoesNotExist:
        raise Http404

    node['devices'] = []

    devices = Device.objects.filter(node=node_id)\
        .values('name', 'description', 'id', 'type', 'routing_protocol', 'routing_protocol_version')
    for device in devices:
        interfaces = Interface.objects.filter(device=device['id'])\
            .values('ipv4_address', 'ipv6_address', 'type', 'wireless_mode', 'wireless_channel', 'wireless_polarity',
                    'mac_address', 'essid', 'status', 'bssid')
        hnas = Hna.objects.filter(device=device['id']).values('route')
        del device['id']
        device['interfaces'] = list(interfaces)
        device['hna'] = list(hnas)
        node['devices'].append(device)

    # return json
    return HttpResponse(simplejson.dumps(node), mimetype='application/json')

# This will dump the whole node (password and email included)
# def dump(request, node_id):
#     """
#     Returns a json description of a node
#     """
#
#     # retrieve object or return 404 error
#     try:
#         node = Node.objects.exclude(status='u').get(pk=node_id)
#     except ObjectDoesNotExist:
#         raise Http404
#
#     node_with_devices = {
#         'node': node,
#         'devices': []
#     }
#     devices = Device.objects.filter(node=node_id)
#     for device in devices:
#         interfaces = Interface.objects.filter(device=device.id)
#         hnas = Hna.objects.filter(device=device.id)
#         node_with_devices['devices'].append({
#             'device': device,
#             'interfaces': list(interfaces),
#             'hna': list(hnas)
#         })
#
#     # return json
#     return __json_response_from(node_with_devices)
#
# def __json_response_from(response):
#     jsonSerializer = JSONSerializer()
#     return HttpResponse(jsonSerializer.serialize(response, use_natural_keys=True), mimetype='application/json')
