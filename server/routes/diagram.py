
from crypt import methods
from doctest import master
from hashlib import new
from itertools import count
from re import I
from flask import send_file
from server import app

from diagrams import Cluster, Diagram, Edge
from diagrams.aws.compute import ECS, EKS, Lambda
from diagrams.aws.database import Redshift
from diagrams.aws.integration import SQS
from diagrams.aws.storage import S3

from diagrams.gcp.analytics import BigQuery
from diagrams.gcp.storage import GCS


import json


with open("./public/ibm-standard.json", "r") as stream:
    file = (json.load(stream))

stream.close()

if (file["bom"]["metadata"]["labels"]["platform"] == "ibm"):
    print(file["bom"]["metadata"]["labels"]["platform"])
    # some logic for using ibm icons


@app.route("/diagram")
def diagram():
    """diagram route"""
    
    with Diagram( show=False, filename='/tmp/diagram'):
        # have a dict of dependencies, key is the name and val is the list of nodes
        clusters = {}
        # iterate through modules
        for i in file["bom"]["spec"]["modules"]:
            d = True
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
                    for i in val:
                        s = str(val[0]["ref"])
                        if s in clusters.keys():
                            clusters[s].append(name)
                        else:
                            clusters[s] = [name]
                if d and key == "enrichedMetadata":
                    # loop through each dependency
                    for i in val["dependencies"]:
                        s = str(i["id"])
                        if s in clusters.keys():
                            clusters[s].append(name)
                        else:
                            clusters[s] = [name]

        # create new cluster for each key
        for clust in clusters.keys():
            makeClusters(clusters, clust)

    return send_file('/tmp/diagram.png', mimetype='image/png')


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





# hard code from before for reference:

# with Cluster("quick start (VPC)"):
    #     with Cluster("ACL: worker"):
    #         with Cluster("Zone 1 - 10.1.0.0/22"):
    #             worker1 = ECS("Worker 1")
            
    #         with Cluster("Zone 2 - 10.2.0.0/22"):
    #             worker2 = ECS("Worker 2")
            
    #         with Cluster("Zone 3 - 10.3.0.0/22"):
    #             worker3 = ECS("Worker 3")

    # with Cluster("Cloud Services"):
    #     handlers = [BigQuery("Monitoring"), 
    #                 GCS("Logging"), 
    #                 Redshift("Analytics")]
    # worker1 \
    #     - Edge(color="red", style="dashed") \
    #     - worker2 \
    #     - Edge(color="red", style="dashed") \
    #     - worker3 \
    #     - Edge(color="blue", style="dashed") \
    #     - handlers[0]