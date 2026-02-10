"""
Deploy Grafana Alloy for metrics collection from videonode.

Automatically includes BSSID mappings if bssid_mappings.alloy file exists locally.

Usage:
    pyinfra @local deploys/generic/alloy.py \
        --data grafana_cloud_token=<TOKEN> \
        --data grafana_cloud_username=<USER_ID> \
        --data grafana_cloud_url=<PROMETHEUS_PUSH_URL>
"""

from io import StringIO
from pathlib import Path

from pyinfra import logger
from pyinfra.api.deploy import deploy
from pyinfra.context import host
from pyinfra.facts.files import File
from pyinfra.facts.server import Command, Home
from pyinfra.operations import files, server

ALLOY_VERSION = "v1.10.1"
BSSID_MAPPINGS_FILE = Path(__file__).parent.parent.parent / "bssid_mappings.alloy"


def _get_alloy_config(
    grafana_cloud_url: str,
    grafana_cloud_username: str,
    grafana_cloud_token: str,
    bssid_rules: str,
    wifi_forward_to: str,
) -> str:
    """Generate Alloy configuration content."""
    return f"""
// Prometheus scrape configuration for local services
prometheus.scrape "videonode" {{
  targets = [{{
    __address__ = "localhost:8090",
  }}]
  metrics_path = "/metrics"
  forward_to = [prometheus.relabel.add_hostname.receiver]
  scrape_interval = "10s"
  scrape_timeout = "8s"
}}

// Node metrics - CPU and hardware monitoring
prometheus.exporter.unix "node" {{
  include_exporter_metrics = true
  disable_collectors = ["arp", "bonding", "conntrack", "diskstats", "edac", "entropy", "fibrechannel", "filesystem", "infiniband", "ipvs", "loadavg", "mdadm", "meminfo", "netclass", "netstat", "nfs", "nfsd", "pressure", "rapl", "schedstat", "sockstat", "softnet", "stat", "textfile", "time", "timex", "udp_queues", "uname", "vmstat", "xfs", "zfs"]
  enable_collectors = ["cpu", "hwmon"]
}}

prometheus.scrape "node_metrics" {{
  targets = prometheus.exporter.unix.node.targets
  forward_to = [prometheus.relabel.add_hostname.receiver]
  scrape_interval = "30s"
  scrape_timeout = "25s"
}}

// WiFi and network metrics
prometheus.exporter.unix "wifi" {{
  include_exporter_metrics = true
  disable_collectors = ["arp", "bonding", "conntrack", "cpu", "diskstats", "edac", "entropy", "fibrechannel", "filesystem", "hwmon", "infiniband", "ipvs", "loadavg", "mdadm", "meminfo", "netclass", "nfs", "nfsd", "pressure", "rapl", "schedstat", "sockstat", "softnet", "stat", "textfile", "time", "timex", "udp_queues", "uname", "vmstat", "xfs", "zfs"]
  enable_collectors = ["wifi", "netdev"]
}}

prometheus.scrape "wifi_metrics" {{
  targets = prometheus.exporter.unix.wifi.targets
  forward_to = [{wifi_forward_to}]
  scrape_interval = "30s"
  scrape_timeout = "25s"
}}

{bssid_rules}

// Add hostname label to all metrics
prometheus.relabel "add_hostname" {{
  forward_to = [prometheus.remote_write.metrics_hosted_prometheus.receiver]

  rule {{
    replacement = constants.hostname
    target_label = "hostname"
  }}
}}

// Remote write to Grafana Cloud
prometheus.remote_write "metrics_hosted_prometheus" {{
   endpoint {{
      name = "hosted-prometheus"
      url  = "{grafana_cloud_url}"

      send_exemplars = false
      send_native_histograms = false

      queue_config {{
        capacity = 10000
        max_shards = 1
        min_shards = 1
        max_samples_per_send = 500
        batch_send_deadline = "30s"
        min_backoff = "1s"
        max_backoff = "30s"
      }}

      basic_auth {{
        username = "{grafana_cloud_username}"
        password = "{grafana_cloud_token}"
      }}
   }}
}}
"""


def _get_systemd_service(alloy_dir: str) -> str:
    """Generate systemd service content."""
    return f"""[Unit]
Description=Grafana Alloy Metrics Collector
After=network-online.target

[Service]
Type=simple
WorkingDirectory={alloy_dir}
ExecStart={alloy_dir}/alloy run --server.http.listen-addr=0.0.0.0:12345 {alloy_dir}/config.alloy
Restart=on-failure
RestartSec=10

# Performance settings
LimitNOFILE=65536
LimitNPROC=32768

[Install]
WantedBy=default.target
"""


@deploy("Setup Grafana Alloy")
def install_alloy(
    grafana_cloud_token: str,
    grafana_cloud_username: str,
    grafana_cloud_url: str,
) -> None:
    """Install and configure Grafana Alloy for metrics collection."""
    user_home = host.get_fact(Home)
    alloy_dir = f"{user_home}/alloy"

    # Check for BSSID mappings
    bssid_rules = ""
    wifi_forward_to = "prometheus.relabel.add_hostname.receiver"
    if BSSID_MAPPINGS_FILE.exists():
        logger.info(f"Found BSSID mappings file at {BSSID_MAPPINGS_FILE}")
        with open(BSSID_MAPPINGS_FILE, "r") as f:
            bssid_rules = f.read()
        wifi_forward_to = "prometheus.relabel.wifi_bssid_enrichment.receiver"

    files.directory(
        name="Ensure Alloy directory exists",
        path=alloy_dir,
    )

    # Check current version
    alloy_file = host.get_fact(File, path=f"{alloy_dir}/alloy")
    current_version = None
    if alloy_file:
        version_output = host.get_fact(
            Command,
            command=f"{alloy_dir}/alloy --version 2>/dev/null | awk '{{print $3}}' | head -1",
        )
        if version_output:
            current_version = version_output.strip()

    needs_download = current_version != ALLOY_VERSION
    if not needs_download:
        logger.info(f"Alloy {ALLOY_VERSION} already installed, skipping download")

    download = files.download(
        name="Download Alloy ARM64 binary",
        src=f"https://github.com/grafana/alloy/releases/download/{ALLOY_VERSION}/alloy-linux-arm64.zip",
        dest="/tmp/alloy-linux-arm64.zip",
        _if=lambda: needs_download,
    )

    server.shell(
        name="Extract and install Alloy",
        commands=[
            "unzip -o /tmp/alloy-linux-arm64.zip -d /tmp",
            f"mv /tmp/alloy-linux-arm64 {alloy_dir}/alloy",
            f"chmod +x {alloy_dir}/alloy",
        ],
        _if=download.did_change,
    )

    files.file(
        name="Remove Alloy archive",
        path="/tmp/alloy-linux-arm64.zip",
        present=False,
        _if=download.did_change,
    )

    config_content = _get_alloy_config(
        grafana_cloud_url,
        grafana_cloud_username,
        grafana_cloud_token,
        bssid_rules,
        wifi_forward_to,
    )

    config_put = files.put(
        name="Create Alloy configuration",
        dest=f"{alloy_dir}/config.alloy",
        src=StringIO(config_content),
        mode="644",
    )

    files.directory(
        name="Ensure systemd user directory exists",
        path=f"{user_home}/.config/systemd/user",
    )

    service_put = files.put(
        name="Create Alloy systemd user service",
        dest=f"{user_home}/.config/systemd/user/alloy.service",
        src=StringIO(_get_systemd_service(alloy_dir)),
        mode="644",
    )

    from pyinfra.operations.util import any_changed

    server.shell(
        name="Reload systemd daemon and enable/start Alloy service",
        commands=[
            "systemctl --user daemon-reload",
            "systemctl --user enable alloy.service",
            "systemctl --user restart alloy.service",
        ],
        _if=any_changed(config_put, service_put, download),
    )

    server.shell(
        name="Check Alloy service status",
        commands=["systemctl --user status alloy.service --no-pager"],
    )


if __name__ == "__main__":
    token = host.data.get("grafana_cloud_token")
    username = host.data.get("grafana_cloud_username")
    url = host.data.get("grafana_cloud_url")

    if not all([token, username, url]):
        logger.error(
            "Missing Grafana Cloud config! Required --data args: "
            "grafana_cloud_token, grafana_cloud_username, grafana_cloud_url"
        )
        exit(1)

    install_alloy(
        grafana_cloud_token=str(token),
        grafana_cloud_username=str(username),
        grafana_cloud_url=str(url),
    )
