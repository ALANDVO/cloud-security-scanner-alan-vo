import os
import json
import boto3
from datetime import datetime
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session

from ..models.domain import Scan, Finding, SeverityEnum, CloudEnum, ScanStatusEnum
from ..models.schemas import ScanCreate
from ..core.config import settings


SEVERITY_SCORES = {
    "critical": 9.0,
    "high": 7.5,
    "medium": 5.0,
    "low": 2.5,
    "info": 1.0,
}

SEVERITY_ORDER = {"critical": 0, "high": 1, "medium": 2, "low": 3, "info": 4}


class ScannerService:
    def __init__(self, db: Session):
        self.db = db
        self.findings_buffer: List[Dict[str, Any]] = []

    def _add_finding(
        self,
        severity: str,
        category: str,
        resource: str,
        title: str,
        detail: str,
        remediation: str,
        cloud: str,
    ) -> Dict[str, Any]:
        score = SEVERITY_SCORES.get(severity, 1.0)
        finding = {
            "finding_id": f"{cloud}-{category}-{resource[:20]}",
            "severity": severity,
            "score": score,
            "category": category,
            "resource": resource,
            "title": title,
            "detail": detail,
            "remediation": remediation,
            "cloud": cloud,
            "detected_at": datetime.utcnow().isoformat(),
        }
        self.findings_buffer.append(finding)
        return finding

    def _get_aws_client(self, service: str):
        try:
            return boto3.Session(region_name=settings.aws_region).client(service)
        except Exception as e:
            raise RuntimeError(f"Failed to create AWS {service} client: {e}")

    def scan_aws(self, scan: Scan, category: Optional[str] = None) -> None:
        if category in (None, "storage", "all"):
            self._scan_aws_s3(scan)
        if category in (None, "iam", "all"):
            self._scan_aws_iam(scan)
        if category in (None, "network", "all"):
            self._scan_aws_network(scan)
        if category in (None, "logging", "all"):
            self._scan_aws_logging(scan)

    def _scan_aws_s3(self, scan: Scan) -> None:
        try:
            s3 = self._get_aws_client("s3")
            buckets = s3.list_buckets().get("Buckets", [])
            for b in buckets[:50]:
                name = b["Name"]
                try:
                    acl = s3.get_bucket_acl(Bucket=name)
                    grants = acl.get("Grants", [])
                    public = any(
                        g.get("Grantee", {}).get("URI", "").endswith("AllUsers")
                        or g.get("Grantee", {}).get("URI", "").endswith("AuthenticatedUsers")
                        for g in grants
                    )
                    if public:
                        self._add_finding(
                            "critical",
                            "storage",
                            name,
                            "S3 bucket has public ACL",
                            f"Bucket {name} grants access to AllUsers or AuthenticatedUsers",
                            f"aws s3api delete-bucket-public-block --bucket {name}",
                            "aws",
                        )
                except Exception:
                    pass

                try:
                    block = s3.get_public_access_block(Bucket=name)
                    if not block.get("PublicAccessBlockAssignment", {}).get("BlockPublicAcls", False):
                        self._add_finding(
                            "high",
                            "storage",
                            name,
                            "S3 public access block not fully enabled",
                            f"Bucket {name} does not block public ACLs via BucketPublicAccessBlock",
                            f"aws s3api put-public-access-block --bucket {name} --public-access-block-configuration BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true",
                            "aws",
                        )
                except Exception:
                    pass

                try:
                    s3.get_bucket_encryption(Bucket=name)
                except Exception:
                    self._add_finding(
                        "medium",
                        "storage",
                        name,
                        "S3 bucket has no default server-side encryption",
                        f"Bucket {name} does not enforce SSE by default",
                        f"aws s3api put-bucket-encryption --bucket {name} --server-side-encryption-configuration {{\"Rules\":[{{\"ApplyServerSideEncryptionByDefault\":{{\"SSEAlgorithm\":\"aws:kms\"}}}}]}}",
                        "aws",
                    )
        except Exception as e:
            print(f"[warn] S3 scan: {e}")

    def _scan_aws_iam(self, scan: Scan) -> None:
        try:
            iam = self._get_aws_client("iam")
            for role in iam.list_roles().get("Roles", [])[:50]:
                rname = role["RoleName"]
                if any(x in rname.lower() for x in ["admin", "root", "superuser"]):
                    self._add_finding(
                        "high",
                        "iam",
                        rname,
                        "IAM role with admin-level naming",
                        f"Role {rname} has a name suggesting broad permissions — verify actual policy scope",
                        "Review and scope down to least privilege; use AWS IAM Access Analyzer for unused permissions",
                        "aws",
                    )

            users = iam.list_users().get("Users", [])
            for u in users[:50]:
                uname = u["UserName"]
                try:
                    keys = iam.list_access_keys(UserName=uname).get("AccessKeyMetadata", [])
                    for k in keys:
                        if k.get("Status") == "Active" and k.get("CreateDate"):
                            age = (datetime.utcnow() - k["CreateDate"]).days
                            if age > 90:
                                self._add_finding(
                                    "medium",
                                    "iam",
                                    uname,
                                    f"Active access key older than 90 days",
                                    f"User {uname} access key {k['AccessKeyId']} is {age} days old",
                                    f"aws iam create-access-key --user-name {uname} && aws iam delete-access-key --user-name {uname} --access-key-id {k['AccessKeyId']}",
                                    "aws",
                                )
                except Exception:
                    pass

            policies = iam.list_policies(Scope="All").get("Policies", [])
            for pol in policies[:50]:
                pname = pol.get("PolicyName", "")
                if pol.get("AttachmentCount", 0) > 0 and ("*" in pname.lower() or "admin" in pname.lower()):
                    self._add_finding(
                        "medium",
                        "iam",
                        pname,
                        "Broad policy attached to multiple entities",
                        f"Policy {pname} attached to {pol['AttachmentCount']} entities",
                        "Break into scoped policies per service; use IAM Access Analyzer",
                        "aws",
                    )
        except Exception as e:
            print(f"[warn] IAM scan: {e}")

    def _scan_aws_network(self, scan: Scan) -> None:
        try:
            ec2 = self._get_aws_client("ec2")
            for sg in ec2.describe_security_groups(MaxResults=50).get("SecurityGroups", []):
                sgid = sg["GroupId"]
                for rule in sg.get("IpPermissions", []):
                    proto = rule.get("IpProtocol", "")
                    port = rule.get("FromPort")
                    ranges = rule.get("IpRanges", [])
                    for r in ranges:
                        if r.get("CidrIp") == "0.0.0.0/0" and proto in ["tcp", "-1"]:
                            pstr = f"port {port}" if port else "all ports"
                            self._add_finding(
                                "high",
                                "network",
                                sgid,
                                f"Security group open to world ({pstr})",
                                f"SG {sgid} allows {pstr} from 0.0.0.0/0",
                                "Restrict to specific CIDR ranges or use a NAT/ALB front end",
                                "aws",
                            )

            for vol in ec2.describe_volumes(Filters=[{"Name": "status", "Values": ["in-use"]}], MaxResults=50).get("Volumes", []):
                if not vol.get("Encrypted"):
                    self._add_finding(
                        "medium",
                        "storage",
                        vol["VolumeId"],
                        "Unencrypted EBS volume in use",
                        f"EBS volume {vol['VolumeId']} is not encrypted",
                        f"Migrate data to a new encrypted volume; enable default encryption: aws ec2 enable-ebs-encryption-by-default --region {settings.aws_region}",
                        "aws",
                    )
        except Exception as e:
            print(f"[warn] Network scan: {e}")

    def _scan_aws_logging(self, scan: Scan) -> None:
        try:
            ct = self._get_aws_client("cloudtrail")
            trails = ct.list_trails().get("TrailList", [])
            if not trails:
                self._add_finding(
                    "high",
                    "logging",
                    "account",
                    "No CloudTrail trail found",
                    "CloudTrail is not logging management events",
                    "aws cloudtrail create-trail --name main --s3-bucket-name my-audit-bucket --enable-logs",
                    "aws",
                )
            else:
                for t in trails:
                    st = ct.get_trail_status(TrailName=t["TrailName"])
                    if not st.get("IsLogging", False):
                        self._add_finding(
                            "medium",
                            "logging",
                            t["TrailName"],
                            "CloudTrail trail exists but is not logging",
                            f"Trail {t['TrailName']} is stopped",
                            f"aws cloudtrail update-trail --name {t['TrailName']} --is-logging true",
                            "aws",
                        )
        except Exception as e:
            print(f"[warn] Logging scan: {e}")

    def scan_gcp(self, scan: Scan) -> None:
        try:
            from google.cloud import storage
            client = storage.Client(project=settings.gcp_project)
            for bucket in client.list_buckets():
                if bucket.name.endswith("-pub") or "public" in bucket.name.lower():
                    self._add_finding(
                        "medium",
                        "storage",
                        bucket.name,
                        "GCS bucket name suggests public access",
                        f"Bucket {bucket.name} — verify IAM bindings",
                        f"gcloud storage buckets remove-iam-binding gs://{bucket.name} --member allUsers --role roles/storage.objectViewer",
                        "gcp",
                    )
        except Exception as e:
            print(f"[warn] GCP scan: {e}")

    def scan_azure(self, scan: Scan) -> None:
        try:
            from azure.identity import DefaultAzureCredential
            from azure.mgmt.storage import StorageManagementClient
            cred = DefaultAzureCredential()
            client = StorageManagementClient(cred, settings.azure_subscription_id or os.environ.get("AZURE_SUBSCRIPTION_ID", ""))
            for sa in client.storage_accounts.list():
                props = sa.properties
                if props.public_network_access and props.public_network_access == "Enabled":
                    self._add_finding(
                        "medium",
                        "network",
                        sa.name,
                        "Azure Storage public network access enabled",
                        f"Storage account {sa.name} allows public network access",
                        f"az storage account update --name {sa.name} --resource-group {sa.resource_group_name} --public-network-access disabled",
                        "azure",
                    )
                if not props.is_hns_enabled and props.https_only == False:
                    self._add_finding(
                        "high",
                        "network",
                        sa.name,
                        "Azure Storage does not enforce HTTPS",
                        f"Storage account {sa.name} allows HTTP",
                        f"az storage account update --name {sa.name} --resource-group {sa.resource_group_name} --https-only true",
                        "azure",
                    )
        except Exception as e:
            print(f"[warn] Azure scan: {e}")

    def run_scan(self, scan_create: ScanCreate) -> Scan:
        scan = Scan(
            cloud=CloudEnum(scan_create.cloud.value),
            region=scan_create.region,
            category=scan_create.category,
            severity_filter=scan_create.severity_filter.value if scan_create.severity_filter else None,
            status=ScanStatusEnum.running,
        )
        self.db.add(scan)
        self.db.commit()
        self.db.refresh(scan)

        self.findings_buffer = []

        try:
            if scan_create.cloud == CloudEnum.aws:
                self.scan_aws(scan, scan_create.category)
            elif scan_create.cloud == CloudEnum.gcp:
                self.scan_gcp(scan)
            elif scan_create.cloud == CloudEnum.azure:
                self.scan_azure(scan)

            findings = self.findings_buffer
            if scan_create.severity_filter:
                min_ord = SEVERITY_ORDER.get(scan_create.severity_filter.value, 0)
                findings = [f for f in findings if SEVERITY_ORDER.get(f["severity"], 5) <= min_ord]

            for f in findings:
                finding = Finding(
                    scan_id=scan.id,
                    finding_id=f["finding_id"],
                    severity=SeverityEnum(f["severity"]),
                    score=f["score"],
                    category=f["category"],
                    resource=f["resource"],
                    title=f["title"],
                    detail=f["detail"],
                    remediation=f["remediation"],
                    cloud=CloudEnum(f["cloud"]),
                )
                self.db.add(finding)

            scan.findings_count = len(findings)
            scan.critical_count = sum(1 for f in findings if f["severity"] == "critical")
            scan.high_count = sum(1 for f in findings if f["severity"] == "high")
            scan.medium_count = sum(1 for f in findings if f["severity"] == "medium")
            scan.low_count = sum(1 for f in findings if f["severity"] == "low")
            scan.info_count = sum(1 for f in findings if f["severity"] == "info")
            scan.status = ScanStatusEnum.completed
            scan.completed_at = datetime.utcnow()
            self.db.commit()
            self.db.refresh(scan)
        except Exception as e:
            scan.status = ScanStatusEnum.failed
            scan.error_message = str(e)
            scan.completed_at = datetime.utcnow()
            self.db.commit()
            raise

        return scan