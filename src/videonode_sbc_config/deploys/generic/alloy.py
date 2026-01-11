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
from pyinfra.context import host
from pyinfra.operations import files, server
from pyinfra.facts.server import Home, Command
from pyinfra.facts.files import File

# Get home directory and Grafana Cloud credentials
USER_HOME = host.get_fact(Home)
ALLOY_DIR = f"{USER_HOME}/alloy"
ALLOY_VERSION = "v1.10.1"

# Get Grafana Cloud config from pyinfra data
GRAFANA_CLOUD_TOKEN = host.data.get("grafana_cloud_token")
GRAFANA_CLOUD_USERNAME = host.data.get("grafana_cloud_username")
GRAFANA_CLOUD_URL = host.data.get("grafana_cloud_url")

if not all([GRAFANA_CLOUD_TOKEN, GRAFANA_CLOUD_USERNAME, GRAFANA_CLOUD_URL]):
    logger.error(
        "Missing Grafana Cloud config! Required --data args: "
        "grafana_cloud_token, grafana_cloud_username, grafana_cloud_url"
    )
    exit(1)

# Check for BSSID mappings file
BSSID_MAPPINGS_FILE = Path(__file__).parent.parent.parent / "bssid_mappings.alloy"
bssid_rules = ""
wifi_forward_to = "prometheus.relabel.add_hostname.receiver"

if BSSID_MAPPINGS_FILE.exists():
    logger.info(f"Found BSSID mappings file at {BSSID_MAPPINGS_FILE}")
    with open(BSSID_MAPPINGS_FILE, "r") as f:
        bssid_rules = f.read()
    # If we have BSSID rules, wifi metrics should forward to the enrichment first
    wifi_forward_to = "prometheus.relabel.wifi_bssid_enrichment.receiver"
else:
    logger.info("No BSSID mappings file found, WiFi metrics won't have AP name labels")

# Create Alloy directory
files.directory(
    name="Ensure Alloy directory exists",
    path=ALLOY_DIR,
)

# Check if Alloy exists and get version
alloy_file = host.get_fact(File, path=f"{ALLOY_DIR}/alloy")
current_version = None
if alloy_file:
    version_output = host.get_fact(
        Command,
        command=f"{ALLOY_DIR}/alloy --version 2>/dev/null | awk '{{print $3}}' | head -1",
    )
    if version_output:
        current_version = version_output.strip()

# Download and install Alloy if needed
if current_version == ALLOY_VERSION:
    logger.info(f"Alloy {ALLOY_VERSION} already installed, skipping download")
else:
    # Download Alloy ARM64 binary
    files.download(
        name="Download Alloy ARM64 binary",
        src=f"https://github.com/grafana/alloy/releases/download/{ALLOY_VERSION}/alloy-linux-arm64.zip",
        dest="/tmp/alloy-linux-arm64.zip",
    )

    # Extract and install
    server.shell(
        name="Extract and install Alloy",
        commands=[
            "unzip -o /tmp/alloy-linux-arm64.zip -d /tmp",
            f"mv /tmp/alloy-linux-arm64 {ALLOY_DIR}/alloy",
            f"chmod +x {ALLOY_DIR}/alloy",
        ],
    )

    # Clean up
    files.file(
        name="Remove Alloy archive",
        path="/tmp/alloy-linux-arm64.zip",
        present=False,
    )

# Create Alloy configuration
alloy_config_content = f"""
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
      url  = "{GRAFANA_CLOUD_URL}"

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
        username = "{GRAFANA_CLOUD_USERNAME}"
        password = "{GRAFANA_CLOUD_TOKEN}"
      }}
   }}
}}
"""

files.put(
    name="Create Alloy configuration",
    dest=f"{ALLOY_DIR}/config.alloy",
    src=StringIO(alloy_config_content),
    mode="644",
)

# Create Alloy systemd user service
alloy_service_content = f"""[Unit]
Description=Grafana Alloy Metrics Collector
After=network-online.target

[Service]
Type=simple
WorkingDirectory={ALLOY_DIR}
ExecStart={ALLOY_DIR}/alloy run --server.http.listen-addr=0.0.0.0:12345 {ALLOY_DIR}/config.alloy
Restart=on-failure
RestartSec=10

# Performance settings
LimitNOFILE=65536
LimitNPROC=32768

[Install]
WantedBy=default.target
"""

# Create systemd user directory
files.directory(
    name="Ensure systemd user directory exists",
    path=f"{USER_HOME}/.config/systemd/user",
)

files.put(
    name="Create Alloy systemd user service",
    dest=f"{USER_HOME}/.config/systemd/user/alloy.service",
    src=StringIO(alloy_service_content),
    mode="644",
)

# Reload systemd and start service
server.shell(
    name="Reload systemd daemon and enable/start Alloy service",
    commands=[
        "systemctl --user daemon-reload",
        "systemctl --user enable alloy.service",
        "systemctl --user restart alloy.service",
    ],
)

# Verify service status
server.shell(
    name="Check Alloy service status",
    commands=["systemctl --user status alloy.service --no-pager"],
)
