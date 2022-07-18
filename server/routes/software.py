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



@app.route("/software")
def software():
    
    """software route"""


    name = file["bom"]["metadata"]["annotations"]["displayName"]
    with Diagram(name, show=False, filename='/tmp/diagram'):
        with Cluster("Core Services"):
            clusters = {}
            # iterate through modules
            for i in file["bom"]["spec"]["modules"]:
                d = True
                v = True
                # go through each item in the module
                for key, val in i.items():
                    # for each module, get the name and dependencies
                    if key == "name":
                        name = val
                    if key == "alias":
                        name = val

                    if key == "dependencies":
                        d = False
                        # loop through each dependency
                        for dep in val:
                            s = str(val[0]["ref"])
                            if s in clusters.keys():
                                clusters[s].append(name)
                            else:
                                clusters[s] = [name]

                    if key == "enrichedMetadata":
                        if d and key == "enrichedMetadata":
                            # loop through each dependency
                            for dep in val["dependencies"]:
                                s = str(dep["id"])
                                if s in clusters.keys():
                                    clusters[s].append(name)
                                else:
                                    clusters[s] = [name]

        # create new cluster for each key
        for clust in clusters.keys():
            makeClusters(clusters, clust)

    return send_file('/tmp/diagram.png', mimetype='image/png')



def makeClusters(clusters, clust):
    nodes = []
    with Cluster(clust):
        # include each node that belongs in the cluster
        for node in clusters[clust]:
            # if there are nested clusters, find those first
            if (node in clusters.keys()):
                # want to go to that cluster and get its nodes first
                makeClusters(clusters, node)
                clusters[node] = []
            else:
                newnode = Sphere(node)
                nodes.append(newnode)
    for i in range(0,len(nodes) - 1):
        nodes[i] - Edge(color="blue") - nodes[i + 1]
    return 1