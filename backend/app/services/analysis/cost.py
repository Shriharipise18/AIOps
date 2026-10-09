"""
Cost Estimation Engine.
Deterministically calculates infrastructure costs based on the Deployment Specification.
Provides a CloudPricingProvider abstraction (initially AWS).
"""
from abc import ABC, abstractmethod
from typing import Dict, Any
from datetime import datetime, timezone
import re


def _parse_cpu_vcpus(value: Any) -> float:
    """Convert Kubernetes CPU quantities (cores or millicores) to vCPUs."""
    if value is None:
        value = "500m"
    text = str(value).strip()
    if text.endswith("m"):
        return float(text[:-1]) / 1000
    return float(text)

class CloudPricingProvider(ABC):
    @abstractmethod
    def get_provider_name(self) -> str:
        pass

    @abstractmethod
    def estimate_monthly_cost(self, spec: Dict[str, Any]) -> Dict[str, Any]:
        """Returns a cost breakdown dict."""
        pass


class AWSPricingProvider(CloudPricingProvider):
    def get_provider_name(self) -> str:
        return "AWS"

    def estimate_monthly_cost(self, spec: Dict[str, Any]) -> Dict[str, Any]:
        platform = spec.get("platform", {})
        replicas = platform.get("replicas", 1)
        
        # Parse CPU and Memory limits (rough parsing for MVP)
        cpu_str = platform.get("cpu_limit") or "500m"
        mem_str = str(platform.get("memory_limit") or "512Mi").strip()
        
        # Rough approximations
        vcpus = _parse_cpu_vcpus(cpu_str)
        mem_gb = 0.5
        match = re.fullmatch(r"([0-9]+(?:\.[0-9]+)?)(Mi|Gi)", mem_str, re.IGNORECASE)
        if match:
            amount, unit = float(match.group(1)), match.group(2).lower()
            mem_gb = amount / 1024 if unit == "mi" else amount
            
        # AWS Fargate rough pricing: $0.04048 / vCPU-hour, $0.004445 / GB-hour
        hours_per_month = 730
        cpu_cost = vcpus * 0.04048 * hours_per_month * replicas
        mem_cost = mem_gb * 0.004445 * hours_per_month * replicas
        compute_cost = round(cpu_cost + mem_cost, 2)
        
        breakdown = [
            {"item": f"Compute ({replicas}x {vcpus}vCPU, {mem_gb:.1f}GB)", "monthly_cost": compute_cost}
        ]
        
        total = compute_cost
        
        # Load balancer
        if platform.get("is_public", False):
            # ALB roughly $16/mo
            breakdown.append({"item": "Application Load Balancer", "monthly_cost": 16.00})
            total += 16.00
            
        # Database
        services = spec.get("services", [])
        for svc in services:
            if svc["type"] == "database":
                # RDS db.t4g.micro roughly $13/mo
                breakdown.append({"item": f"Managed DB ({svc['engine']})", "monthly_cost": 13.00})
                total += 13.00
            elif svc["type"] == "cache":
                # ElastiCache cache.t4g.micro roughly $12/mo
                breakdown.append({"item": "Managed Redis", "monthly_cost": 12.00})
                total += 12.00

        return {
            "available": True,
            "source": self.get_provider_name(),
            "region": "us-east-1 (Default)",
            "total_monthly_usd": round(total, 2),
            "breakdown": breakdown,
            "assumptions": [
                "100% utilization (730 hours/month)",
                "AWS Fargate pricing used for compute",
                "Minimum t4g.micro instance sizes assumed for managed services",
                "Data transfer costs not included"
            ],
            "timestamp": datetime.now(timezone.utc).isoformat()
        }


def analyze_cost(spec: Dict[str, Any]) -> Dict[str, Any]:
    """Calculate cost based on the specified provider."""
    provider_name = spec.get("platform", {}).get("provider", "").upper()
    
    if provider_name == "AWS":
        provider = AWSPricingProvider()
        return provider.estimate_monthly_cost(spec)
    else:
        # Never report a zero-dollar estimate when this provider has no pricing
        # model. The UI uses `available` to show this as unavailable instead.
        return {
            "available": False,
            "source": provider_name or "Unknown",
            "region": "N/A",
            "total_monthly_usd": None,
            "breakdown": [],
            "assumptions": [f"Pricing is not configured for {provider_name or 'this provider'}; no estimate was calculated."],
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
