
from crypt import methods
from curses.ascii import ETB
from doctest import master
from hashlib import new
from itertools import count
from re import I
from telnetlib import EC
from flask import send_file
from server import app

from diagrams import Cluster, Diagram, Edge

from diagrams.aws.compute import ECS, EKS, Lambda
from diagrams.aws.database import Redshift
from diagrams.aws.integration import SQS
from diagrams.aws.storage import S3

from diagrams.gcp.analytics import BigQuery
from diagrams.gcp.storage import GCS

from diagrams.ibm.general import Monitoring, MonitoringLogging, Cloudant, IotCloud
from diagrams.ibm.data import Cloud
from diagrams.ibm.storage import ObjectStorage
from diagrams.ibm.infrastructure import Diagnostics
from diagrams.ibm.network import InternetServices, VpnConnection, Router, Bridge, DirectLink
from diagrams.ibm.management import DeviceManagement
from diagrams.ibm.user import User, Browser
from diagrams.ibm.compute import Key
from diagrams.ibm.social import FileSync
from diagrams.ibm.applications import EnterpriseApplications


import json



# change type of diagram here
type = "ibm-standard"
with open("./public/"+type+".json", "r") as stream:
    file = (json.load(stream))
stream.close()

# ibm specific node icons
ignored = ["ibm-resource-group", "ibm-access-group", "ibm-vpc-gateways", "ibm-log-analysis-bind", "ibm-cloud-monitoring-bind", "kms-key"]
platservice = {"ibm-log-analysis": MonitoringLogging, "ibm-cloud-monitoring": Monitoring, "ibm-activity-tracker":Diagnostics, 
                "ibm-object-storage":ObjectStorage, "cos":ObjectStorage}  # dict of cloud services

workernode = Key  # Cloud, Router
vpenode = VpnConnection

@app.route("/diagram")
def diagram():
    """diagram route"""
    
    with Diagram( show=False, filename='/tmp/diagram'):
        with Cluster(file["bom"]["metadata"]["labels"]["platform"] + " - " + type):
            # have a dict of dependencies, key is the name and val is the list of nodes
            clusters = {"ibm-vpc-subnets": [3, [0]], "ibm-ocp-vpc": [0, [0]], 
                        "worker-subnets": [0, [0]], "vpe-subnets": [0, [0]]} # last two are for standard
            services = []
            # iterate through modules
            for i in file["bom"]["spec"]["modules"]:
                d = True
                v = True
                # go through each item in the module
                for key, val in i.items():
                    # for each module, get the name and dependencies
                    if key == "name":
                        name = val
                        if name in ignored:
                            break
                    if key == "alias" and "-subnets" in val:
                        name = val
                    
                    if name in platservice.keys():
                        # new node in cloud service cluster
                        services.append(name)
                        break

                    if name in clusters.keys() and key == "variables":
                        v = False
                        # for each variable:
                        for var in val:
                            if var["name"] == "worker_count" or var["name"] == "_count":
                                clusters[name][0] = var["value"]
                            if var["name"] == "ipv4_cidr_blocks":
                                clusters[name][1] = var["value"]

                    # if key == "dependencies":
                    #     d = False
                    #     # loop through each dependency
                    #     for i in val:
                    #         s = str(val[0]["ref"])
                    #         if s in clusters.keys():
                    #             clusters[s].append(name)
                    #         else:
                    #             clusters[s] = [name]

                    if key == "enrichedMetadata":
                        if v:
                            # get num subnets and num worker nodes
                            if name in clusters.keys():
                                for i in val["variables"]:
                                    if i["name"] == "worker_count" or i["name"] == "_count":
                                        num = int(i["default"])
                                        clusters[name][0] =  num
                                        break

                        if d:
                            # loop through each dependency
                            for depend in val["dependencies"]:
                                s = str(depend["id"])
                                if s in ignored:
                                    break
                                if s in platservice.keys() and "ibm-object-storage" not in services:
                                    services.append(s)
                                    continue
                                # if s in clusters.keys():
                                #     clusters[s].append(name)
                                # else:
                                #     clusters[s] = [name]


            nodes = {}
            with Cluster("Cloud Services"):
                for serv in services:
                    n = platservice[serv](serv)
                    nodes.update({serv: n})
            
            with Cluster("VPC"):
                if clusters["worker-subnets"][0] > 0:
                    for net in range(1, clusters["worker-subnets"][0] + 1):
                        with Cluster("Zone " + str(net)):
                            for worker in range(0, clusters["ibm-ocp-vpc"][0]):
                                s = str(clusters["worker-subnets"][1][worker]) + " - worker"+str(net)
                                n = workernode(s)
                                nodes.update({"worker"+str(net): n})
                            
                    for net in range(1, clusters["vpe-subnets"][0] + 1):
                        with Cluster("Zone " + str(net)):
                            for worker in range(0, clusters["ibm-ocp-vpc"][0]):
                                s = str(clusters["vpe-subnets"][1][worker]) + " - vpe"+str(net)
                                n = vpenode(s)
                                nodes.update({"vpe"+str(net): n})
                    nodes["vpe1"] - Edge(color="red") - nodes["vpe2"] - Edge(color="red") - nodes["vpe3"] \
                        - Edge(color="blue", style="dashed") - nodes["ibm-log-analysis"]


                    
                else:
                    for net in range(1, clusters["ibm-vpc-subnets"][0] + 1):
                        with Cluster("Zone " + str(net)):
                            for worker in range(0, clusters["ibm-ocp-vpc"][0]):
                                s = str(clusters["ibm-ocp-vpc"][1][worker]) + " - worker"+str(net)
                                n = workernode(s)
                                nodes.update({"worker"+str(net): n})
                    nodes["worker3"] - Edge(color="blue", style="dashed") - nodes["ibm-log-analysis"]
 
            nodes["worker1"] - Edge(color="red") - nodes["worker2"] - Edge(color="red") - nodes["worker3"]

            
        if type == "ibm-standard":
            with Cluster("Remote Employee"):
                User("Remote employee") >> Cloudant() >> nodes["vpe1"]
            with Cluster("Consumer"):
                user = User("Users")
                internet = Cloudant("Internet")
            with Cluster("Enterprise Network"):
                    dir = FileSync("Enterprise Directory")
                    User("Enterprise User")
                    EnterpriseApplications("Enterprise Application")
            
            nodes["vpe3"] >> DirectLink("Direct link") >> dir
                
            user >> internet >> InternetServices("Cloud Internet Service") \
                >> Bridge("Private LB") >> nodes["worker1"]



            # create new cluster for each key
            # for clust in clusters.keys():
            #     makeClusters(clusters, clust)


    return send_file('/tmp/diagram.png', mimetype='image/png')


# not being used right now
def makeClusters(clusters, clust):
    with Cluster(clust):
        # include each node that belongs in the cluster
        nodes = []
        for node in clusters[clust]:
            # if there are nested clusters, find those first
            if (node in clusters.keys()):
                # want to go to that cluster and get its nodes first
                makeClusters(clusters, node)
                clusters[node] = []
            else:
                newnode = GCS(node)
                nodes.append(newnode)
        for i in range(0,len(nodes) - 1):
            nodes[i] - Edge(color="blue") - nodes[i + 1]
    return 1

