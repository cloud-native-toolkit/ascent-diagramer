import json
import re

from diagrams import *

from crypt import methods
from curses.ascii import ETB
from doctest import master
from hashlib import new
from itertools import count
from re import I
from telnetlib import EC
from urllib.request import urlretrieve
from flask import send_file
from server import app


from diagrams.aws.analytics import Redshift
from diagrams.aws.compute import EC2
from diagrams.aws.database import Redshift
from diagrams.aws.general import Users, InternetAlt1
from diagrams.aws.network import ClientVpn, ALB
from diagrams.aws.security import KMS

from diagrams.azure.analytics import LogAnalyticsWorkspaces, AnalysisServices
from diagrams.azure.compute import SpringCloud
from diagrams.azure.database import BlobStorage
from diagrams.azure.general import Usericon
from diagrams.azure.iot import Sphere
from diagrams.azure.network import LoadBalancers, ApplicationGateway, Subnets as Azsubnets, VirtualNetworks, VirtualNetworkGateways, RouteTables, DNSZones
from diagrams.azure.security import KeyVaults

from diagrams.ibm.compute import PowerSystems
from diagrams.ibm.general import *
from diagrams.ibm.logging import *
from diagrams.ibm.network import *
from diagrams.ibm.storage import ObjectStorage, FileStorage



fname = "maximo400"
with open("./public/"+fname+".json", "r") as stream:
    file = (json.load(stream))
stream.close()

# temp
namespaceicon = VpcEndpoints
globalicon = PowerSystems


@app.route("/software")
def software():
    
    """software route"""


    name = file["bom"]["metadata"]["annotations"]["displayName"]
    with Diagram(name, show=False, filename='/tmp/diagram'):
        with Cluster("OpenShift cluster"):
            namespaces = {"global":[]}
            other = []
            # iterate through modules
            for i in file["bom"]["spec"]["modules"]:
                d = True
                v = True
                # go through each item in the module
                for key, val in i.items():
                    # for each module, get the name and dependencies
                    if key == "name":
                        name = val
                        if "namespace" in name:
                            break
                        continue
                    # if key == "alias":
                    #     name = val  # get the more specific name
                    #     continue
                   
                    if key == "dependencies":
                        d = False
                        # loop through each dependency
                        for dep in val:
                            s = str(val[0]["ref"])
                            if s in namespaces.keys():
                                namespaces[s].append(name) # add the curr val to the list of things in the namespace
                            else:
                                namespaces[s] = [name]
                        break
                    
                    namespaces["global"].append(name)
                    break
                    # things that belong in namespaces dont have this/it doesnt matter
                    # if key == "enrichedMetadata":
                    #     if d and key == "enrichedMetadata":
                    #         # loop through each dependency
                    #         for dep in val["dependencies"]:
                    #             s = str(dep["id"])
                    #             if s in namespaces.keys():
                    #                 namespaces[s].append(name)
                    #             else:
                    #                 namespaces[s] = [name]

            # create new cluster for each key
            j = 0
            newlist = []
            for clust in namespaces.keys():
                nodes = makeClusters(namespaces, clust, j)
                j += 1
                newlist.append(nodes[0])
                print(nodes)
            for i in range(0,len(newlist) - 1):
                newlist[i] - Edge(color="red") - newlist[i + 1]
            
            
            # nodes[5] - Edge(color="red") - nodes[6] - \
            #     Edge(color='red') - nodes["gitops-cp-queue-manager"]
            # nodes["gitops-cp-apic"] - Edge(color="red") - nodes["gitops-cp-event-streams"] - \
            #     Edge(color='red') - nodes["gitops-cp-platform-navigator"]

    return send_file('/tmp/diagram.png', mimetype='image/png')



def makeClusters(namespaces, clust, j):
    nodes = []
    with Cluster(clust):
        # include each node that belongs in the cluster
        for node in namespaces[clust]:
            # if there are nested namespaces, find those first
            if (node in namespaces.keys()):
                # want to go to that cluster and get its nodes first
                makeClusters(namespaces, node, 0)
                namespaces[node] = []
            else:
                if len(node) > 13:
                    node = node.rsplit('-', 1)
                    node = node[0] + '\n' + node[1]
                if clust == "global":
                    newnode = globalicon(node)
                else:
                    newnode = namespaceicon(node)
                nodes.append(newnode)
    for i in range(0,len(nodes) - 1):
        nodes[i] - Edge(color="blue") - nodes[i + 1]
    return nodes