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

from diagrams.ibm.general import Monitoring, MonitoringLogging, Cloudant, IotCloud
from diagrams.ibm.data import Cloud
from diagrams.ibm.storage import ObjectStorage
from diagrams.ibm.infrastructure import Diagnostics
from diagrams.ibm.network import InternetServices, VpnConnection, Router, Bridge, DirectLink, Gateway
from diagrams.ibm.management import DeviceManagement
from diagrams.ibm.user import User, Browser
from diagrams.ibm.compute import Key
from diagrams.ibm.social import FileSync
from diagrams.ibm.applications import EnterpriseApplications


import json


# change type of diagram here
type = "ibm-edge"
with open("./public/"+type+".json", "r") as stream:
    file = (json.load(stream))
stream.close()

# ibm specific node icons
ignored = ["ibm-resource-group", "ibm-access-group", "ibm-vpc-gateways", "ibm-log-analysis-bind", "ibm-cloud-monitoring-bind", "kms-key"]
platservice = {"ibm-log-analysis": MonitoringLogging, "ibm-cloud-monitoring": Monitoring, "ibm-activity-tracker":Diagnostics, 
                "ibm-object-storage":ObjectStorage, "cos":ObjectStorage}  # dict of cloud services

workernode = Key  # Cloud, Router
vpenode = VpnConnection
ingressnode = Bridge
bastionnode = DeviceManagement
egressnode = Cloud

@app.route("/diagram")
def diagram():
    """diagram route"""
    
    with Diagram( show=False, filename='/tmp/diagram'):
        with Cluster(file["bom"]["metadata"]["labels"]["platform"] + " Cloud"):
            # have a dict of dependencies, key is the name and val is the list of nodes
            clusters = {"ibm-vpc-subnets": [3, [0]], "ibm-ocp-vpc": [0, [0]], 
                        "worker-subnets": [0, [0]], "vpe-subnets": [0, [0]], "ingress-subnets": [0, [0]], "bastion-subnets": [0, [0]], "egress-subnets": [0, [0]]} 
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
                        
                        # for each variable:
                        for var in val:
                            if (var["name"] == "worker_count" or var["name"] == "_count") and "value" in var:
                                v = False
                                clusters[name][0] = var["value"]
                            if var["name"] == "ipv4_cidr_blocks":
                                v = False
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
            if type != "ibm-edge":
                with Cluster("Cloud Services"):
                    if "cos" in services and "ibm-object-storage" in services:
                        services.remove("cos")
                    for serv in services:
                        n = platservice[serv](serv)
                        nodes.update({serv: n})
            
            with Cluster(type + " (VPC)"):
                if clusters["worker-subnets"][0] > 0: 
                    for net in range(1, clusters["worker-subnets"][0] + 1):
                        with Cluster("Zone " + str(net)):
                            s = str(clusters["worker-subnets"][1][net - 1]) + " - worker"+str(net)
                            n = workernode(s)
                            nodes.update({"worker"+str(net): n})
                    nodes["worker1"] - Edge(color="red") - nodes["worker2"] - Edge(color="red") - nodes["worker3"] 
                    
                    conslink = nodes["worker1"]
                    dirlink = nodes["worker3"]

                elif clusters["ibm-ocp-vpc"][0] > 0:
                    for net in range(1, clusters["ibm-vpc-subnets"][0] + 1):
                        with Cluster("Zone " + str(net)):
                            s = "worker"+str(net)
                            n = workernode(s)
                            nodes.update({"worker"+str(net): n})
                    nodes["worker1"] - Edge(color="red") - nodes["worker2"] - Edge(color="red") - nodes["worker3"] \
                        >> nodes["ibm-log-analysis"]
                    

                if clusters["vpe-subnets"][0] > 0:
                    for net in range(1, clusters["vpe-subnets"][0] + 1):
                        with Cluster("Zone " + str(net)):
                            s = str(clusters["vpe-subnets"][1][net - 1]) + " - vpe"+str(net)
                            n = vpenode(s)
                            nodes.update({"vpe"+str(net): n})
                    nodes["vpe1"] - Edge(color="red") - nodes["vpe2"] - Edge(color="red") - nodes["vpe3"] \
                        >> Gateway("VPE Gateway") >> nodes["ibm-log-analysis"]
                    
                    emplink = nodes["vpe1"]


                if clusters["ingress-subnets"][0] > 0:
                    for net in range(1, clusters["ingress-subnets"][0] + 1):
                        with Cluster("Zone " + str(net)):
                            s = str(clusters["ingress-subnets"][1][net - 1]) + " - ingress"+str(net)
                            n = ingressnode(s)
                            nodes.update({"ingress"+str(net): n})
                    nodes["ingress1"] - Edge(color="red") - nodes["ingress2"] - Edge(color="red") - nodes["ingress3"]
                    
                    conslink = nodes["ingress1"]
                    emplink = nodes["ingress1"]
                    dirlink = nodes["ingress3"]
                

                if clusters["bastion-subnets"][0] > 0:
                    for net in range(1, clusters["bastion-subnets"][0] + 1):
                        with Cluster("Zone " + str(net)):
                            s = str(clusters["bastion-subnets"][1][net - 1]) + " - bastion"+str(net)
                            n = bastionnode(s)
                            nodes.update({"bastion"+str(net): n})
                    nodes["bastion1"] - Edge(color="red") - nodes["bastion2"] - Edge(color="red") - nodes["bastion3"] 
                

                if clusters["egress-subnets"][0] > 0:
                    for net in range(1, clusters["egress-subnets"][0] + 1):
                        with Cluster("Zone " + str(net)):
                            s = str(clusters["egress-subnets"][1][net - 1]) + " - egress"+str(net)
                            n = egressnode(s)
                            nodes.update({"egress"+str(net): n})
                    nodes["egress1"] - Edge(color="red") - nodes["egress2"] - Edge(color="red") - nodes["egress3"]
                

        # print(clusters["worker-subnets"])
        # print(clusters["vpe-subnets"])
        # print(clusters["ingress-subnets"])
        # print(clusters["bastion-subnets"])
        # print(clusters["egress-subnets"])

            
        if type != "quickstart":
            if type == "ibm-production" or type == "ibm-standard":
                with Cluster("Consumer"):
                    user = User("Users")
                    internet = Cloudant("Internet")
                user >> internet >> InternetServices("Cloud Internet Service") >> Bridge("Private LB") >> conslink
            if type == "ibm-edge" or type == "ibm-standard":
                with Cluster("Remote Employee"):
                    User("Remote employee") >> Cloudant() >> emplink
                with Cluster("Enterprise Network"):
                    dir = FileSync("Enterprise Directory")
                    User("Enterprise User")
                    EnterpriseApplications("Enterprise Application")
                dirlink >> DirectLink("Direct link") >> dir
                
            



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

