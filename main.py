#!/usr/bin/env python3
# cloud-security-scanner — Scans AWS, GCP, and Azure configurations for security misconfigurations across S3/GCS/Blob storage, IAM, VPC/networking, encryption, and logging — with severity scoring and remediation guides.
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from llm_client import LLM
import json, os, re, sys, time, statistics
from datetime import datetime, timedelta

def _get_aws_client(service):
    try:
        import boto3
        return boto3.Session().client(service)
    except ImportError:
        raise SystemExit("boto3 not installed. Run: pip install boto3")

def _findings_list():
    return []

FINDINGS = []

def _add(severity, category, resource, title, detail, remediation, cloud):
    score = {"critical": 9.0, "high": 7.5, "medium": 5.0, "low": 2.5, "info": 1.0}[severity]
    FINDINGS.append({"id": f"{cloud}-{category}-{resource[:20]}", "severity": severity, "score": score,
                     "category": category, "resource": resource, "title": title, "detail": detail,
                     "remediation": remediation, "cloud": cloud, "detected_at": datetime.utcnow().isoformat()})

def _scan_aws_s3(region):
    print("  Scanning S3 buckets...")
    try:
        s3 = _get_aws_client("s3")
        buckets = s3.list_buckets().get("Buckets", [])
        for b in buckets[:50]:
            name = b["Name"]
            try:
                acl = s3.get_bucket_acl(Bucket=name)
                grants = acl.get("Grants", [])
                public = any(g.get("Grantee", {}).get("URI", "").endswith("AllUsers") or
                             g.get("Grantee", {}).get("URI", "").endswith("AuthenticatedUsers")
                             for g in grants)
                if public:
                    _add("critical", "storage", name, "S3 bucket has public ACL",
                         f"Bucket {name} grants access to AllUsers or AuthenticatedUsers",
                         f"aws s3api delete-bucket-public-block --bucket {name}  # then set ACL to private", "aws")
                except Exception:
                    pass
            except Exception:
                pass
            try:
                block = s3.get_public_access_block(Bucket=name)
                if not block.get("PublicAccessBlockAssignment", {}).get("BlockPublicAcls", False):
                    _add("high", "storage", name, "S3 public access block not fully enabled",
                         f"Bucket {name} does not block public ACLs via BucketPublicAccessBlock",
                         f"aws s3api put-public-access-block --bucket {name} --public-access-block-configuration BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true", "aws")
            except Exception:
                pass
            try:
                enc = s3.get_bucket_encryption(Bucket=name)
            except Exception:
                _add("medium", "storage", name, "S3 bucket has no default server-side encryption",
                     f"Bucket {name} does not enforce SSE by default",
                     f"aws s3api put-bucket-encryption --bucket {name} --server-side-encryption-configuration {{'Rules':[{{'ApplyServerSideEncryptionByDefault':{{'SSEAlgorithm':'aws:kms'}}}}]}}", "aws")
    except Exception as e:
        print(f"    [warn] S3: {e}")

def _scan_aws_iam():
    print("  Scanning IAM...")
    try:
        iam = _get_aws_client("iam")
        for role in iam.list_roles().get("Roles", [])[:50]:
            rname = role["RoleName"]
            if any(x in rname.lower() for x in ["admin", "root", "superuser"]):
                try:
                    pol = iam.get_role_policy(RoleName=rname, PolicyName=role["Arn"].split("/")[-1]) if "/" in rname else None
                except Exception:
                    pol = None
                _add("high", "iam", rname, "IAM role with admin-level naming",
                     f"Role {rname} has a name suggesting broad permissions — verify actual policy scope",
                     "Review and scope down to least privilege; use AWS IAM Access Analyzer for unused permissions", "aws")
        users = iam.list_users().get("Users", [])
        for u in users[:50]:
            uname = u["UserName"]
            try:
                keys = iam.list_access_keys(UserName=uname).get("AccessKeyMetadata", [])
                for k in keys:
                    if k.get("Status") == "Active" and k.get("CreateDate"):
                        age = (datetime.utcnow() - k["CreateDate"]).days
                        if age > 90:
                            _add("medium", "iam", uname, f"Active access key older than 90 days",
                                 f"User {uname} access key {k['AccessKeyId']} is {age} days old",
                                 f"aws iam create-access-key --user-name {uname} && aws iam delete-access-key --user-name {uname} --access-key-id {k['AccessKeyId']}", "aws")
            except Exception:
                pass
        policies = iam.list_policies(Scope="All").get("Policies", [])
        for pol in policies[:50]:
            pname = pol.get("PolicyName", "")
            if pol.get("AttachmentCount", 0) > 0 and ("*" in pname.lower() or "admin" in pname.lower()):
                _add("medium", "iam", pname, "Broad policy attached to multiple entities",
                     f"Policy {pname} attached to {pol['AttachmentCount']} entities",
                     "Break into scoped policies per service; use IAM Access Analyzer", "aws")
    except Exception as e:
        print(f"    [warn] IAM: {e}")

def _scan_aws_network(region):
    print("  Scanning VPC / network security...")
    try:
        ec2 = _get_aws_client("ec2")
        for sg in ec2.describe_security_groups(MaxResults=50).get("SecurityGroups", []):
            sgid = sg["GroupId"]
            for rule in sg.get("IpPermissions", []):
                proto = rule.get("IpProtocol", "")
                port = rule.get("FromPort")
                ranges = rule.get("IpRanges", [])
                for r in ranges:
                    if r.get("CidrIp") == "0.0.0.0/0" and proto in ["tcp", "-1"]:
                        pstr = f"port {port}" if port else "all ports"
                        _add("high", "network", sgid, f"Security group open to world ({pstr})",
                             f"SG {sgid} allows {pstr} from 0.0.0.0/0",
                             f"Restrict to specific CIDR ranges or use a NAT/ALB front end", "aws")
        ebs = _get_aws_client("ec2")
        for vol in ebs.describe_volumes(Filters=[{"Name": "status", "Values": ["in-use"]}], MaxResults=50).get("Volumes", []):
            if not vol.get("Encrypted"):
                _add("medium", "storage", vol["VolumeId"], "Unencrypted EBS volume in use",
                     f"EBS volume {vol['VolumeId']} is not encrypted",
                     "Migrate data to a new encrypted volume; enable default encryption: aws ec2 enable-ebs-encryption-by-default --region " + region, "aws")
    except Exception as e:
        print(f"    [warn] Network: {e}")

def _scan_aws_logging():
    print("  Scanning logging/monitoring...")
    try:
        ct = _get_aws_client("cloudtrail")
        trails = ct.list_trails().get("TrailList", [])
        if not trails:
            _add("high", "logging", "account", "No CloudTrail trail found",
                 "CloudTrail is not logging management events",
                 "aws cloudtrail create-trail --name main --s3-bucket-name my-audit-bucket --enable-logs", "aws")
        else:
            for t in trails:
                st = ct.get_trail_status(TrailName=t["TrailName"])
                if not st.get("IsLogging", False):
                    _add("medium", "logging", t["TrailName"], "CloudTrail trail exists but is not logging",
                         f"Trail {t['TrailName']} is stopped",
                         f"aws cloudtrail update-trail --name {t['TrailName']} --is-logging true", "aws")
    except Exception as e:
        print(f"    [warn] Logging: {e}")

def _scan_gcp():
    print("  Scanning GCP...")
    try:
        from google.cloud import storage
        client = storage.Client()
        for bucket in client.list_buckets():
            if bucket.name.endswith("-pub") or "public" in bucket.name.lower():
                _add("medium", "storage", bucket.name, "GCS bucket name suggests public access",
                     f"Bucket {bucket.name} — verify IAM bindings",
                     f"gcloud storage buckets remove-iam-binding gs://{bucket.name} --member allUsers --role roles/storage.objectViewer", "gcp")
    except Exception as e:
        print(f"    [warn] GCP: {e}")
    try:
        from google.cloud import compute_v1
        inst = compute_v1.InstancesClient()
        for zone in ["us-central1-a"]:
            for vm in inst.list(project="auto", zone=zone):
                if not vm.disks or not any(d.auto_delete for d in vm.disks):
                    pass
    except Exception:
        pass

def _scan_azure():
    print("  Scanning Azure...")
    try:
        from azure.identity import DefaultAzureCredential
        from azure.mgmt.storage import StorageManagementClient
        cred = DefaultAzureCredential()
        client = StorageManagementClient(cred, os.environ.get("AZURE_SUBSCRIPTION_ID", ""))
        for sa in client.storage_accounts.list():
            props = sa.properties
            if props.public_network_access and props.public_network_access == "Enabled":
                _add("medium", "network", sa.name, "Azure Storage public network access enabled",
                     f"Storage account {sa.name} allows public network access",
                     f"az storage account update --name {sa.name} --resource-group {sa.resource_group_name} --public-network-access disabled", "azure")
            if not props.is_hns_enabled and props.https_only == False:
                _add("high", "network", sa.name, "Azure Storage does not enforce HTTPS",
                     f"Storage account {sa.name} allows HTTP",
                     f"az storage account update --name {sa.name} --resource-group {sa.resource_group_name} --https-only true", "azure")
    except Exception as e:
        print(f"    [warn] Azure: {e}")

def cmd_scan(args):
    llm = LLM()
    FINDINGS.clear()
    cloud = args.cloud.lower()
    print(f"{'='*60}")
    print(f"CLOUD SECURITY SCAN — {cloud.upper()}")
    print(f"{'='*60}\n")
    if cloud == "aws":
        if args.category in (None, "storage", "all"): _scan_aws_s3(args.region)
        if args.category in (None, "iam", "all"): _scan_aws_iam()
        if args.category in (None, "network", "all"): _scan_aws_network(args.region)
        if args.category in (None, "logging", "all"): _scan_aws_logging()
    elif cloud == "gcp":
        _scan_gcp()
    elif cloud == "azure":
        _scan_azure()
    findings = FINDINGS
    if args.severity:
        order = {"critical": 0, "high": 1, "medium": 2, "low": 3, "info": 4}
        min_ord = order.get(args.severity, 0)
        findings = [f for f in findings if order.get(f["severity"], 5) <= min_ord]
    print(f"\n{'='*60}")
    print(f"SCAN COMPLETE — {len(findings)} findings")
    print(f"{'='*60}\n")
    sev_order = {"critical": 0, "high": 1, "medium": 2, "low": 3, "info": 4}
    for f in sorted(findings, key=lambda x: (sev_order[x["severity"]], x["title"])):
        icon = {"critical": "🔴", "high": "🟠", "medium": "🟡", "low": "🟢", "info": "⚪"}[f["severity"]]
        print(f"  {icon} [{f['severity'].upper():<8}] {f['title']}")
        print(f"           resource: {f['resource']}  |  {f['detail'][:80]}")
    if args.output:
        with open(args.output, "w") as fh:
            json.dump({"scan_time": datetime.utcnow().isoformat(), "cloud": cloud,
                       "findings": findings, "summary": {"total": len(findings)}}, fh, indent=2)
        print(f"\nReport saved to {args.output}")
    if findings:
        top3 = sorted(findings, key=lambda x: -x["score"])[:3]
        prompt = f"You are a cloud security expert. Here are the top 3 security findings from a {cloud} scan:\n{json.dumps(top3, indent=2)}\n\nFor each finding, provide: 1) why it matters (threat model), 2) the exact CLI command to remediate, 3) how to verify the fix, 4) whether this is a common attack vector (CWE ID if applicable)."
        analysis = llm.generate(prompt)
        print(f"\n{'='*60}")
        print("AI SECURITY ANALYSIS (TOP FINDINGS)")
        print(f"{'='*60}\n")
        print(analysis)

def cmd_iam_audit(args):
    llm = LLM()
    FINDINGS.clear()
    _scan_aws_iam()
    findings = FINDINGS
    print(f"\nIAM AUDIT — {len(findings)} findings\n")
    for f in findings:
        print(f"  [{f['severity'].upper()}] {f['title']} — {f['resource']}")
        print(f"    Fix: {f['remediation']}")
    if findings:
        prompt = f"Audit this IAM setup for least-privilege violations. Findings: {json.dumps(findings, indent=2)}\n\nFor each: identify the specific permission that is too broad, what the minimal replacement policy would be, and flag any that could lead to privilege escalation."
        print(f"\n{'='*60}")
        print("AI IAM ANALYSIS:")
        print(f"{'='*60}\n")
        print(llm.generate(prompt))

def cmd_network_check(args):
    llm = LLM()
    FINDINGS.clear()
    _scan_aws_network(args.region)
    findings = FINDINGS
    print(f"\nNETWORK CHECK — {len(findings)} findings\n")
    for f in findings:
        print(f"  [{f['severity'].upper()}] {f['title']} — {f['resource']}")
        print(f"    {f['detail']}")
        print(f"    Fix: {f['remediation']}")
    if findings:
        print(f"\nAI NETWORK ANALYSIS:\n")
        print(llm.generate(f"Analyze these network security findings: {json.dumps(findings, indent=2)}\nFor each, explain the attack path an adversary could use and the minimal fix."))

def cmd_remediate(args):
    llm = LLM()
    finding_id = args.finding
    print(f"{'='*60}")
    print(f"REMEDIATION GUIDE — {finding_id}")
    print(f"{'='*60}\n")
    prompt = f"Provide a step-by-step remediation guide for cloud security finding: {finding_id}\n\nInclude: 1) pre-requisites and backups, 2) exact CLI commands (with AWS/GCP/Azure variants), 3) verification steps to confirm the fix, 4) rollback plan if something breaks, 5) monitoring to detect regression. Be specific — use real command syntax, not pseudocode."
    guide = llm.generate(prompt)
    print(guide)

def cmd_report(args):
    llm = LLM()
    cloud = args.cloud.lower()
    FINDINGS.clear()
    if cloud == "aws":
        _scan_aws_s3("us-east-1"); _scan_aws_iam(); _scan_aws_network("us-east-1"); _scan_aws_logging()
    elif cloud == "gcp":
        _scan_gcp()
    elif cloud == "azure":
        _scan_azure()
    findings = FINDINGS
    summary = {"critical": 0, "high": 0, "medium": 0, "low": 0, "info": 0}
    for f in findings:
        summary[f["severity"]] = summary.get(f["severity"], 0) + 1
    print(f"{'='*60}")
    print(f"SECURITY REPORT — {cloud.upper()}")
    print(f"{'='*60}")
    print(f"Generated: {datetime.utcnow().isoformat()}")
    print(f"Total findings: {len(findings)}")
    for sev, cnt in summary.items():
        if cnt: print(f"  {sev}: {cnt}")
    if args.output:
        report = {"cloud": cloud, "generated_at": datetime.utcnow().isoformat(), "summary": summary, "findings": findings}
        with open(args.output, "w") as fh:
            json.dump(report, fh, indent=2)
        print(f"\nReport written to {args.output}")
    exec_summary = llm.generate(f"Write a 200-word executive security summary for this {cloud} scan. {len(findings)} findings: {json.dumps(summary)}. Top issues: {json.dumps([f['title'] for f in findings[:5]])}. Tone: direct, risk-focused, action-oriented. Include a risk rating (Low/Med/High/Critical) and the top 3 actions to take this week.")
    print(f"\n{'='*60}")
    print("EXECUTIVE SUMMARY (AI-generated):")
    print(f"{'='*60}\n")
    print(exec_summary)

def main():
    import argparse
    p = argparse.ArgumentParser(prog="cloud-security-scanner", description="Cloud security misconfiguration scanner")
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("scan", help="Full security scan")
    s.add_argument("--cloud", required=True, choices=["aws", "gcp", "azure"])
    s.add_argument("--region", default="us-east-1"); s.add_argument("--category", default=None, choices=["storage", "iam", "network", "logging", "all"])
    s.add_argument("--severity", default=None, choices=["critical", "high", "medium", "low"])
    s.add_argument("--output", default=None)
    s.set_defaults(fn=cmd_scan)

    i = sub.add_parser("iam-audit", help="IAM-specific audit")
    i.add_argument("--cloud", default="aws")
    i.set_defaults(fn=cmd_iam_audit)

    n = sub.add_parser("network-check", help="VPC/network security check")
    n.add_argument("--cloud", default="aws"); n.add_argument("--region", default="us-east-1")
    n.set_defaults(fn=cmd_network_check)

    r = sub.add_parser("remediate", help="AI remediation guide for a finding")
    r.add_argument("--finding", required=True)
    r.set_defaults(fn=cmd_remediate)

    rp = sub.add_parser("report", help="Generate full security report")
    rp.add_argument("--cloud", default="aws", choices=["aws", "gcp", "azure"])
    rp.add_argument("--output", default=None)
    rp.set_defaults(fn=cmd_report)

    args = p.parse_args()
    args.fn(args)

if __name__ == '__main__':
    main()
