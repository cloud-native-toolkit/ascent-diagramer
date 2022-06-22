
from crypt import methods
from flask import send_file
from server import app

from diagrams import Cluster, Diagram
from diagrams.aws.compute import ECS, EKS, Lambda
from diagrams.aws.database import Redshift
from diagrams.aws.integration import SQS
from diagrams.aws.storage import S3

from diagrams.gcp.analytics import BigQuery
from diagrams.gcp.storage import GCS



@app.route("/diagram")
def diagram():
    """diagram route"""

    with Diagram("IBM Cloud", show=False, filename='/tmp/diagram'):

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

        worker1 >> worker2 >> worker3

    return send_file('/tmp/diagram.png', mimetype='image/png')
