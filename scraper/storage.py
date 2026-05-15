import oci
import gzip
import json
from typing import List, Dict, Any
from datetime import datetime

class OCIStorage:
    """Handle the Object Cloud Storage using the 'oci' SDK."""
    def __init__(self, namespace: str, bucket: str):
        signer = oci.auth.signers.InstancePrincipalsSecurityTokenSigner()

        self.client = oci.object_storage.ObjectStorageClient(
            config={},
            signer=signer
        )

        self.namespace = namespace
        self.bucket = bucket

    def write_jobs(self, jobs: List[Dict[str, Any]], source_id: int):
        """Write jobs to OCI Object Storage in gzip-compressed JSONL format, partitioned by date and source"""
        if not jobs:
            print(f"No jobs to write for source {source_id}")
            return

        date_str = datetime.utcnow().strftime("%Y/%m/%d")
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        key = f"raw/{date_str}/batch_{timestamp}_source_{source_id}.jsonl.gz"

        content = "\n".join(json.dumps(job) for job in jobs)
        compressed_content = gzip.compress(content.encode("utf-8"))

        self.client.put_object(
            namespace_name=self.namespace,
            bucket_name=selef.bucket,
            object_name=key,
            put_object_body=compressed_content
        )

        print(f"Wrote {len(jobs)} jobs to oci://{self.namespace}/{self.bucket}/{key}")

        