
from crypt import methods
from flask import send_file
from server import app

from diagrams import Cluster, Diagram, Edge
from diagrams.aws.compute import ECS, EKS, Lambda
from diagrams.aws.database import Redshift
from diagrams.aws.integration import SQS
from diagrams.aws.storage import S3

from diagrams.gcp.analytics import BigQuery
from diagrams.gcp.storage import GCS

import yaml


with open("./public/bom.yaml", "r") as stream:
    try:
        yamlFile = (yaml.safe_load(stream))
    except yaml.YAMLError as exc:
        print(exc)

stream.close()

print(yamlFile)

if (yamlFile['kind'] == "BillOfMaterial") :
    # do want to continue
    print(yamlFile['kind'])
if (yamlFile['metadata']['labels']['platform'] == "ibm"):
    print(yamlFile['metadata']['labels']['platform'])
    # some logic for using ibm icons
# elif (yamlFile['metadata']['labels']['platform'] == 'azure'):
#     # etc, use diff logic


@app.route("/diagram")
def diagram():
    """diagram route"""

    with Diagram( show=False, filename='/tmp/diagram'):
        with Cluster("IBM Cloud"):
            with Cluster("quick start (VPC)"):
                with Cluster("ACL: worker"):
                    with Cluster("Zone 1 - 10.1.0.0/22"):
                        worker1 = ECS("Worker 1")
                    
                    with Cluster("Zone 2 - 10.2.0.0/22"):
                        worker2 = ECS("Worker 2")
                    
                    with Cluster("Zone 3 - 10.3.0.0/22"):
                        worker3 = ECS("Worker 3")
            with Cluster("Cloud Services"):
                handlers = [BigQuery("Monitoring"), 
                            GCS("Logging"), 
                            Redshift("Analytics")]
            worker1 \
                - Edge(color="red", style="dashed") \
                - worker2 \
                - Edge(color="red", style="dashed") \
                - worker3 \
                - Edge(color="blue", style="dashed") \
                - handlers[0]

    return send_file('/tmp/diagram.png', mimetype='image/png')


# note: easy enough to parse a python file, just need to figure
# out the guidelines for how we want the icons to look, then we
# can put in logic for matching the specs in the yaml file and
# dynamically create a diagram based on what we see in there