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

from diagrams.aws.compute import ECS, EKS, Lambda, EC2
from diagrams.aws.database import Redshift
from diagrams.aws.integration import SQS
from diagrams.aws.storage import S3
from diagrams.aws.security import KMS
from diagrams.aws.analytics import Redshift

from diagrams.ibm.general import *
from diagrams.ibm.logging import *
from diagrams.ibm.storage import ObjectStorage, FileStorage
from diagrams.ibm.network import *
from diagrams.ibm.compute import PowerSystems



# change type of diagram here via json file name i.e. 'ibm-production' or 'ibm-quickstart'
type = "aws-standard"
with open("./public/"+type+".json", "r") as stream:
    file = (json.load(stream))
stream.close()

# ibm specific node icons
ignored = ["ibm-resource-group", "ibm-access-group", "ibm-vpc-gateways", "ibm-log-analysis-bind", "ibm-cloud-monitoring-bind", "kms-key"]

# pre-defined nodes for diagrams

icons ={"ibm" : {"worker":PowerSystems, "vpe":VpcEndpoints, 
        "ingress":Subnets, "bastion":VirtualRouterAppliance, "egress":VirtualRouterAppliance},
        
        "aws" : {"rosa":Redshift, "bastion":EC2, "instance":EC2}}

platservice = {"ibm-log-analysis":LogAnalysis, "ibm-cloud-monitoring":Monitoring, "ibm-activity-tracker":ActivityTracker, 
               "ibm-object-storage":ObjectStorage, "cos":ObjectStorage, 
               "aws-kms":KMS}  # dict of cloud services



@app.route("/diagram")
def diagram():
    
    """diagram route"""
    global emplink, conslink, dirlink, servlink
    
    with Diagram( show=False, filename='/tmp/diagram'):
        pform = type.split("-", 1)[0]  # get the platform i.e. aws, ibm, azure
        print(pform)
        with Cluster(pform + " Cloud"):
            # have a dict of dependencies, key is the name and val is the list of nodes
            clusters = {"ibm-ocp-vpc": [0, [0]], "worker-subnets": [0, [0]], "vpe-subnets": [0, [0]], 
                        "ingress-subnets": [0, [0]], "bastion-subnets": [0, [0]], "egress-subnets": [0, [0]],
                        "aws-vpc": [0, [0]], "pri_subnets": [0, [0], ''], "pub_subnets": [0, [0], '']} 
            awsnodes = ["aws-rosa", "aws-ec2-bastion", "aws-ec2-instance"]
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
                    if key == "alias" and ("-subnets" in val or val in clusters.keys()):
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
                            if var["name"] == "ipv4_cidr_blocks" or var["name"] == "subnet_cidrs":
                                v = False
                                clusters[name][1] = var["value"]
                                clusters[name][0] = len(clusters[name][1])

                    if name in awsnodes and key == "dependencies":
                        for dep in val:
                            if 'ref' in dep.keys() and dep['ref'] in clusters.keys():
                                print(dep['ref'])
                                clusters[dep['ref']][2] = name.rsplit("-", 1)[1]
                    
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


            print(clusters)
            nodes = {}

            with Cluster(type + " (VPC)"):
                if clusters["worker-subnets"][0] > 0 and clusters["ibm-ocp-vpc"][0] > 0:
                    clusters["ibm-ocp-vpc"][0] = 0
                    
                if type == 'ibm-quickstart':
                    for net in range(1, 4):
                        with Cluster("Zone " + str(net)):
                            s = "worker"+str(net)
                            n = icons["ibm"]["workernode"](s)
                            nodes.update({"worker"+str(net): n})
                    nodes["worker1"] - Edge(color="red") - nodes["worker2"] - Edge(color="red") - nodes["worker3"] \
                        >> nodes["ibm-log-analysis"]

                else:
                    for key in clusters.keys():
                        if clusters[key][0] > 0:
                            for net in range(1, clusters[key][0] + 1):
                                with Cluster("Zone " + str(net)):
                                    b = re.split('-|_', key)[0]
                                    s = str(clusters[key][1][net - 1]) + "\n" + b + str(net)  # "worker1"
                                    if 'pub' in b or 'pri' in b:
                                        with Cluster(s):
                                            n = icons[pform][clusters[key][2]](clusters[key][2])
                                            b = clusters[key][2]  # would be something like rosa
                                    else:
                                        n = icons[pform][b](s)
                                    nodes.update({b + str(net): n})
                                if net > 1:  # past first zone
                                    nodes[b + str(net - 1)] - Edge(color="red") - n

                    if "worker1" in nodes.keys():
                        conslink = nodes["worker1"]
                    elif "ingress1" in nodes.keys():
                        conslink = nodes["ingress1"]
                    elif "rosa1" in nodes.keys():
                        conslink = nodes["rosa1"]
                    elif "instance1" in nodes.keys():
                        conslink = nodes["instance1"]
                    
                    if "worker3" in nodes.keys():
                        dirlink = nodes["worker3"]
                        servlink = nodes["worker3"]
                    elif "ingress3" in nodes.keys():
                        dirlink = nodes["ingress3"]
                        servlink = nodes["ingress3"]
                    elif "bastion3" in nodes.keys():
                        dirlink = nodes["bastion3"]
                        servlink = nodes["bastion3"]

                    if "vpe1" in nodes.keys():
                        emplink = nodes["vpe1"]
                    elif "ingress1" in nodes.keys():
                        emplink = nodes["ingress1"]
                    elif "bastion1" in nodes.keys():
                        emplink = nodes["bastion1"]

        if "edge" not in type:
            with Cluster("Cloud Services"):
                services = list(set(services))  # get rid of duplicates
                if "cos" in services and "ibm-object-storage" in services:
                    services.remove("cos")
                for serv in services:
                    print(serv)
                    n = platservice[serv](serv)
                    nodes.update({serv: n})
                servlink - Edge(color="blue") - nodes[next(iter(services))]
        if 'quickstart' not in type:
            if 'production' in type or 'standard' in type:
                with Cluster("Consumer"):
                    user = PeerCloud("Users")
                    internet = Cis("Internet")
                user >> internet >> Cdn("Cloud Internet Service") >> LocalLoadBalancing("Private LB") >> conslink
            if 'edge' in type or 'standard' in type:
                with Cluster("Remote Employee"):
                    PeerCloud("Remote employee") >> Cis() >> emplink
                with Cluster("Enterprise Network"):
                    dir = FileStorage("Enterprise Directory")
                    PeerCloud("Enterprise User")
                    Enterprise("Enterprise Application")
                dirlink >> DirectLink("Direct link") >> dir

    return send_file('/tmp/diagram.png', mimetype='image/png')

