# Weather Report on one Panacea bundle

Eleven storage and CPU checks, plus three network checks, on one `log_bundle_id`. Metric rows live in `panacea.nu_metrics_sysstats`. Config lives in the `nu_config_*` tables. No new ClickHouse table.

The network checks do not need new parsers. `sar.INFO`, `ping_all.INFO`, and `host_nic_stats.INFO` are already ingested.

Every query filters `log_bundle_id` first, because that column leads the sort key. Replace `12345` with the bundle id. End every query with:

```sql
SETTINGS max_execution_time = 30,
         timeout_before_checking_execution_speed = 0,
         max_rows_to_read = 1000000000
```

VM checks and cluster checks in `weather_report.py` are empty lists. There is nothing to add for those two groups.

## Already present

These are ingested today. The report reads them.

| Piece | Where | Columns | How the check uses it |
|---|---|---|---|
| Cluster header | `nu_config_cluster_details` | `cluster_id`, `cluster_name`, `nos_version`, `num_nodes` | Print these on the report. VM count, hot-tier size, and cold-tier size are not in this table. |
| Node list | `nu_config_node_details` | `cvm_ip`, `host_ip`, `hypervisor` | One row per CVM in the bundle. |
| Disk tier | `nu_config_disks` | `storage_tier`, `disk_serial_number`, `mount_path` | Await check keeps a disk when `storage_tier` contains `SSD`. |
| Device to serial | `df.INFO`, already parsed | `tags.filesystem` (`/dev/sdX`) and `tags.mount_point` | `component` is `disk`, `metric_name` is `disk_usage_percent`. The mount path contains the serial. |
| Write await | `iostat.INFO` | `disk_write_await_ms`, `disk_avg_queue_size`, `disk_write_iops` | `component` `disk`. Instance is the kernel device (`sda`, `nvme0n1`). |
| vCPU count | `mpstat.INFO` | `cpu_idle_percent`, one row per core | Count instances other than `all`. This is the count only. It is not the usage check. |
| Whole-host idle | `top_host.INFO` | `top_host_cpu_idle` | One number for the host. Host CPU level and core imbalance still need per-core rows. |
| SAR | `sar.INFO` | `sar_rx_drops_per_sec`, `sar_tx_drops_per_sec`, `sar_rx_errors_per_sec`, `sar_tx_errors_per_sec`, `sar_ifutil_pct`, `sar_*_packets_per_sec` | `component` `network`. Instance is the interface. Section 8. |
| Ping all | `ping_all.INFO` | `ping_all_latency`, `ping_all_lost_pkt`, `ping_all_unreachable` | `component` `ping`. Instance is the target. Section 9. |
| Host NIC CRC | `host_nic_stats.INFO` | `host_nic_rx_crc_errors` | Absolute counter. Score the increase during the bundle. Section 10. |

### Disk write await, from data already stored

Keep devices whose tier contains `SSD`. Match iostat’s device name to df’s filesystem, and df’s mount path to `nu_config_disks`. Interesting when at least 2% of samples have `w_await` ≥ 10 ms. Investigate at 10%. The message also reports mean and coefficient of variation of queue size and write iops, on the slow samples only.

```sql
WITH tier AS (
    SELECT cvm_ip, disk_serial_number, mount_path
    FROM panacea.nu_config_disks
    WHERE log_bundle_id = 12345
      AND positionCaseInsensitive(storage_tier, 'SSD') > 0
),
devmap AS (
    SELECT DISTINCT cvm_ip,
           replaceRegexpOne(JSONExtractString(tags, 'filesystem'), '.*/', '') AS device,
           JSONExtractString(tags, 'mount_point') AS mount_point
    FROM panacea.nu_metrics_sysstats
    WHERE log_bundle_id = 12345
      AND component = 'disk'
      AND metric_name = 'disk_usage_percent'
),
ssd AS (
    SELECT d.cvm_ip, d.device
    FROM devmap AS d
    INNER JOIN tier AS t
      ON d.cvm_ip = t.cvm_ip
     AND d.mount_point = t.mount_path
)
SELECT s.cvm_ip, s.device,
       count() AS samples,
       countIf(s.w_await >= 10) AS slow_samples,
       avgIf(s.aqu_sz, s.w_await >= 10) AS avg_qusz,
       stddevSampIf(s.aqu_sz, s.w_await >= 10)
         / nullIf(avgIf(s.aqu_sz, s.w_await >= 10), 0) AS cv_qusz,
       avgIf(s.w_s, s.w_await >= 10) AS avg_w_s,
       stddevSampIf(s.w_s, s.w_await >= 10)
         / nullIf(avgIf(s.w_s, s.w_await >= 10), 0) AS cv_w_s
FROM (
    SELECT cvm_ip, component_instance AS device, event_timestamp,
           maxIf(value, metric_name = 'disk_write_await_ms') AS w_await,
           maxIf(value, metric_name = 'disk_avg_queue_size') AS aqu_sz,
           maxIf(value, metric_name = 'disk_write_iops') AS w_s
    FROM panacea.nu_metrics_sysstats
    WHERE log_bundle_id = 12345
      AND component = 'disk'
      AND metric_name IN (
            'disk_write_await_ms', 'disk_avg_queue_size', 'disk_write_iops')
    GROUP BY cvm_ip, device, event_timestamp
) AS s
INNER JOIN ssd ON s.cvm_ip = ssd.cvm_ip AND s.device = ssd.device
GROUP BY s.cvm_ip, s.device
LIMIT 1000
```

### vCPU count, from mpstat already stored

```sql
SELECT cvm_ip, uniqExact(component_instance) AS vcpu_count
FROM panacea.nu_metrics_sysstats
WHERE log_bundle_id = 12345
  AND component = 'cpu'
  AND metric_name = 'cpu_idle_percent'
  AND component_instance NOT IN ('all', 'cpu')
GROUP BY cvm_ip
LIMIT 100
```

## Still to add

| Gap | Source | Rule that must survive |
|---|---|---|
| CVM CPU usage and ready | Hypervisor sample of the CVM | `pct_used` is summed across vCPUs. On 4 vCPUs the investigate line is 360, not 90. |
| Host CPU per core | `mpstat_host.INFO` | Numeric core ids, sorted 0..n-1, then split in half for the two sockets. |
| CVM threads | `top.INFO`, file already ingested | Parser keeps about 30 service processes and drops threads. |
| Stargate starts | `stargate.out` | More than one start in the bundle is investigate. |
| Oplog bytes and flags | hvars and `stargate.gflags` | Counter `oplog_bytes` is bytes. Flags are max dirty MB and low-water percent. |
| Oplog names | hosted vDisks, `arithmos_vdisks`, `vdisk_to_vg`, `vm_to_vg`, `vm_ls` | Status does not need these. The sentence on a hit does. A partial set can throw and become status 3. |
| Metadata latency | Stargate latency page | Two `nfs_reads` stages. Content-cache stats are a different file and are already ingested. |
| Cold-tier reads | Arithmos virtual-disk stats | `estore_hdd_kb` and `estore_ssd_kb` per vDisk uuid. |

## 1. CVM CPU usage and CVM CPU ready

**Missing.** Both checks read `host_cvm_cpu_util` from the hypervisor. `pct_used` is a sum across vCPUs. `pct_ready` is percent ready. `mpstat.INFO` is taken inside the CVM and supplies only the vCPU count above.

**Add.** One hypervisor file, expected name `cvm_cpu_ready.INFO`. Confirm the basename on a bundle. `component` `cvm_sched`. Metrics `cvm_cpu_used_percent` and `cvm_cpu_ready_percent`. Instance `cvm`. `cvm_cpu_used_percent` uses the same scale as the check: 100 means one fully busy vCPU, so a 4-vCPU CVM can reach 400.

**How.** New parser, one sample per timestamp, registered in `ParserFactory`. Re-ingest. Score the upper quartile of each series, then its mean.

```sql
SELECT cvm_ip, metric_name, avg(value) AS mean_value
FROM panacea.nu_metrics_sysstats
WHERE log_bundle_id = 12345
  AND component = 'cvm_sched'
  AND metric_name IN ('cvm_cpu_used_percent', 'cvm_cpu_ready_percent')
GROUP BY cvm_ip, metric_name
LIMIT 100
```

Usage: interesting at `vcpu_count × 75`, investigate at `vcpu_count × 90`. Ready: interesting at `vcpu_count × 3`, investigate at `vcpu_count × 5`. The query above is the plain mean. The check uses the mean of the upper quartile.

## 2. Host CPU per core

**Missing.** Per-core host busy percent. `top_host_cpu_idle` is the whole host.

**Add.** File `mpstat_host.INFO`. `component` `host_cpu`. Metric `host_cpu_busy_percent`. Instance is the numeric core id. Busy is 100 minus idle.

**How.** Copy the mpstat parser. Register `mpstat_host\.INFO` before the generic mpstat pattern. Re-ingest. Sort cores as integers and split the list in half. That half is the socket group the imbalance check uses.

```sql
SELECT cvm_ip, component_instance AS cpu_id, avg(value) AS mean_busy_percent
FROM panacea.nu_metrics_sysstats
WHERE log_bundle_id = 12345
  AND component = 'host_cpu'
  AND metric_name = 'host_cpu_busy_percent'
GROUP BY cvm_ip, cpu_id
ORDER BY cvm_ip, toUInt16OrZero(cpu_id)
LIMIT 1000
```

Level: upper-quartile mean across cores. 75 interesting, 90 investigate. Imbalance: coefficient of variation inside a socket half. 0.5 interesting, 0.7 investigate.

## 3. CVM threads

**Missing.** Thread rows. The file `top.INFO` is already ingested. `TopParser` keeps about 30 processes from a fixed service list.

**Add.** Same file. `component` `cvm_thread`. Metric `cvm_thread_cpu_percent`. Instance `pid:command`. Write a sample only when CPU is at least 60.

**How.** Extend `top_parser.py`. Do not add a second factory registration. Re-ingest. Keep timestamp so a consecutive run can be counted. A thread with zero runs is ignored. Coefficient of variation in the message is std divided by sample count.

```sql
SELECT cvm_ip, component_instance AS thread,
       avg(value) AS mean_cpu, max(value) AS max_cpu, count() AS samples
FROM panacea.nu_metrics_sysstats
WHERE log_bundle_id = 12345
  AND component = 'cvm_thread'
  AND metric_name = 'cvm_thread_cpu_percent'
GROUP BY cvm_ip, thread
HAVING mean_cpu >= 60
ORDER BY mean_cpu DESC
LIMIT 100
```

Interesting at a sustained mean of 60. Investigate at 75.

## 4. Stargate starts

**Missing.** Start timestamps. `stargate.out` is not read for this. The existing Stargate parser looks for errors.

**Add.** `component` `stargate`, metric `stargate_start_event`, instance pid, value 1. One row per start.

**How.** New parser on the start line. Register `stargate\.out`. Re-ingest.

```sql
SELECT cvm_ip, count() AS starts, groupArray(event_timestamp) AS start_times
FROM panacea.nu_metrics_sysstats
WHERE log_bundle_id = 12345
  AND component = 'stargate'
  AND metric_name = 'stargate_start_event'
GROUP BY cvm_ip
LIMIT 100
```

More than one start is investigate. One start is status 0.

## 5. Oplog

**Missing.** hvars counter `oplog_bytes` (bytes, skip instance `total`). Two flags: `vdisk_distributed_oplog_max_dirty_MB` (tests use 6144) and `vdisk_distributed_oplog_dynamic_draining_low_water_pct` (tests use 85). The low-water flag is used only by the busy check. The name on a hit also needs `stargate_hosted_active` (`vdiskid`, `vdiskname`; first word is the NFS name), `arithmos_vdisks` (`nfs_name`, `virtual_disk_uuid`), `vdisk_to_vg` (`vmdisk_uuid`, `vg_name`, `vg_uuid`, `vg_attachment_type`), `vm_to_vg` (`vg_uuid`, `uuid`), and `vm_ls` (VM name, uuid, NFS names).

**Add.** `component` `vdisk`, metric `oplog_dirty_mb`, instance vdisk id. Store MB, which is bytes divided by 1024². `component` `stargate_gflag`, metrics `oplog_max_dirty_mb` and `oplog_low_water_pct`, one row per node. Name rows can sit in tags on `component` `vdisk_hosted`, metric `hosted`, value 1. If `vdisk_to_vg` is present and `arithmos_vdisks` is absent, the name lookup throws. Ingest the name files together or leave all of them out. The status still computes from dirty MB and the flags.

**How.** One parser for the hvars counter, one for the two gflags, one for the name tables. Confirm each basename on a bundle, register the patterns, re-ingest.

```sql
WITH limits AS (
    SELECT cvm_ip,
           anyIf(value, metric_name = 'oplog_max_dirty_mb') AS max_mb,
           anyIf(value, metric_name = 'oplog_low_water_pct') AS low_water_pct
    FROM panacea.nu_metrics_sysstats
    WHERE log_bundle_id = 12345
      AND component = 'stargate_gflag'
      AND metric_name IN ('oplog_max_dirty_mb', 'oplog_low_water_pct')
    GROUP BY cvm_ip
),
samples AS (
    SELECT cvm_ip, component_instance AS vdisk_id, value AS dirty_mb
    FROM panacea.nu_metrics_sysstats
    WHERE log_bundle_id = 12345
      AND component = 'vdisk'
      AND metric_name = 'oplog_dirty_mb'
)
SELECT s.cvm_ip, s.vdisk_id, count() AS samples,
       countIf(s.dirty_mb > l.max_mb * l.low_water_pct / 100) AS over_low_water,
       countIf(s.dirty_mb >= l.max_mb * 0.9) AS near_limit
FROM samples AS s
INNER JOIN limits AS l ON s.cvm_ip = l.cvm_ip
GROUP BY s.cvm_ip, s.vdisk_id
LIMIT 1000
```

Busy: `over_low_water / samples` greater than 0.3. Exactly one such vDisk is investigate. Two to four is interesting. Zero, or five or more, is status 0. Logical limit: `near_limit` greater than 0 is investigate. That check has no interesting state.

## 6. Metadata latency

**Missing.** Stargate latency page, `nfs_reads` only, stages `VdiskBlockmapLookupDone` and `EgroupFinderOpDone`. Columns in the original frame are `avglatency_us` and `latencypct_oftotal`, filtered to this CVM and component `vdisk_controller`. `stargate_content_cache.INFO` is already ingested and is a different file.

**Add.** `component` `stargate_latency`. Metrics `stage_avg_lat_usec` and `stage_latency_pct_of_total`. Instance `nfs_reads:VdiskBlockmapLookupDone` and `nfs_reads:EgroupFinderOpDone`.

**How.** New parser for that page. Keep those two stages. Register the file pattern. Re-ingest. Sum the two stages per timestamp.

```sql
SELECT cvm_ip, event_timestamp,
       sumIf(value, metric_name = 'stage_avg_lat_usec') AS avg_lat_usec,
       sumIf(value, metric_name = 'stage_latency_pct_of_total') AS pct_total
FROM panacea.nu_metrics_sysstats
WHERE log_bundle_id = 12345
  AND component = 'stargate_latency'
  AND metric_name IN ('stage_avg_lat_usec', 'stage_latency_pct_of_total')
  AND component_instance IN (
        'nfs_reads:VdiskBlockmapLookupDone',
        'nfs_reads:EgroupFinderOpDone')
GROUP BY cvm_ip, event_timestamp
HAVING avg_lat_usec >= 10000 AND pct_total >= 25
ORDER BY pct_total DESC
LIMIT 100
```

Investigate when any sample is at least 10 ms and at least 40% of read latency. Interesting at 25%. 10000 microseconds is 10 ms.

## 7. Cold-tier reads

**Missing.** Per-vDisk `estore_hdd_kb` and `estore_ssd_kb`. No arithmos virtual-disk parser is registered.

**Add.** `component` `vdisk`, metrics `estore_hdd_kb` and `estore_ssd_kb`, instance the vDisk uuid, unit KB.

**How.** New parser. Confirm the basename, register it, re-ingest. This component is shared with `oplog_dirty_mb`, so the metric name is the filter.

```sql
SELECT cvm_ip, vdisk, count() AS samples,
       countIf(hdd_kb / (hdd_kb + ssd_kb) >= 0.40) AS hot_cold,
       countIf(hdd_kb / (hdd_kb + ssd_kb) >= 0.25) AS warm_cold
FROM (
    SELECT cvm_ip, component_instance AS vdisk, event_timestamp,
           maxIf(value, metric_name = 'estore_hdd_kb') AS hdd_kb,
           maxIf(value, metric_name = 'estore_ssd_kb') AS ssd_kb
    FROM panacea.nu_metrics_sysstats
    WHERE log_bundle_id = 12345
      AND component = 'vdisk'
      AND metric_name IN ('estore_hdd_kb', 'estore_ssd_kb')
    GROUP BY cvm_ip, vdisk, event_timestamp
)
WHERE hdd_kb + ssd_kb > 0
GROUP BY cvm_ip, vdisk
LIMIT 1000
```

Investigate when `hot_cold / samples` is at least 0.40. Interesting when `warm_cold / samples` is at least 0.25.

## 8. SAR

**Already stored.** `sar.INFO`. `component` `network`. Instance is the interface. Guest `tap` and `veth` interfaces are skipped at ingest. The names below are the ones the parser writes.

**Add.** Drops, errors, and utilization need no parser. Packet rate needs the interface speed, which is not stored today. Add one row per interface, `component` `network`, metric `nic_speed_bps`, from ethtool speed or the speed SAR used for `%ifutil`.

**How.** Drops and errors use 1 per second as the hit. Byte load uses `sar_ifutil_pct`, which is already throughput divided by link bandwidth: 80 interesting, 90 investigate. Packet rate uses that same bandwidth. The ceiling is the smallest Ethernet frame, 64 bytes, which is 512 bits:

`line_pps = nic_speed_bps / 512`

Interesting when receive or transmit packets per second reach half of `line_pps`. Investigate at 80% of `line_pps`. On a 10 Gbps link that is about 9.8 million and 15.6 million packets per second. On a 25 Gbps link it is about 24.4 million and 39.1 million. A single packet-rate number for every NIC is the wrong line.

```sql
WITH speed AS (
    SELECT cvm_ip, component_instance AS iface, any(value) AS speed_bps
    FROM panacea.nu_metrics_sysstats
    WHERE log_bundle_id = 12345
      AND component = 'network'
      AND metric_name = 'nic_speed_bps'
    GROUP BY cvm_ip, iface
),
rates AS (
    SELECT cvm_ip, component_instance AS iface,
           countIf(metric_name IN (
                'sar_rx_drops_per_sec', 'sar_tx_drops_per_sec',
                'sar_rx_errors_per_sec', 'sar_tx_errors_per_sec')
              AND value >= 1) AS bad_samples,
           countIf(metric_name IN (
                'sar_rx_drops_per_sec', 'sar_tx_drops_per_sec',
                'sar_rx_errors_per_sec', 'sar_tx_errors_per_sec')) AS rate_samples,
           maxIf(value, metric_name = 'sar_ifutil_pct') AS max_ifutil_pct,
           maxIf(value, metric_name = 'sar_rx_packets_per_sec') AS max_rx_pps,
           maxIf(value, metric_name = 'sar_tx_packets_per_sec') AS max_tx_pps
    FROM panacea.nu_metrics_sysstats
    WHERE log_bundle_id = 12345
      AND component = 'network'
      AND metric_name IN (
            'sar_rx_drops_per_sec', 'sar_tx_drops_per_sec',
            'sar_rx_errors_per_sec', 'sar_tx_errors_per_sec',
            'sar_ifutil_pct',
            'sar_rx_packets_per_sec', 'sar_tx_packets_per_sec')
    GROUP BY cvm_ip, iface
)
SELECT r.cvm_ip, r.iface, r.bad_samples, r.rate_samples, r.max_ifutil_pct,
       r.max_rx_pps, r.max_tx_pps, s.speed_bps,
       s.speed_bps / 512 AS line_pps
FROM rates AS r
LEFT JOIN speed AS s ON r.cvm_ip = s.cvm_ip AND r.iface = s.iface
LIMIT 500
```

Drops or errors at or above 1 per second: investigate when `bad_samples / rate_samples` is at least 0.02, interesting when `bad_samples` is at least 1. Interface utilization: 80 interesting, 90 investigate. Packet rate: interesting at `0.5 * line_pps`, investigate at `0.8 * line_pps`. If `nic_speed_bps` is missing for that interface, the packet-rate check is status 3 and the utilization check still runs.

## 9. Ping all

**Already stored.** `ping_all.INFO`. `component` `ping`. Instance is the target (CVM, host, or gateway). Metrics `ping_all_latency` (ms), `ping_all_lost_pkt`, and `ping_all_unreachable`. A value above 0 on the last two is a lost or unreachable sample.

**Add.** No parser. Score the rows.

**How.** Any loss or unreachable target is investigate. That matches the Panacea ping check, which treats loss and unreachable above 0 as a hit. Latency has no fixed millisecond line in that check. For this report, p95 at or above 5 ms is interesting and p95 at or above 20 ms is investigate.

```sql
SELECT cvm_ip, component_instance AS target,
       countIf(metric_name IN ('ping_all_lost_pkt', 'ping_all_unreachable')
               AND value > 0) AS loss_samples,
       quantileIf(0.95)(value, metric_name = 'ping_all_latency') AS p95_ms
FROM panacea.nu_metrics_sysstats
WHERE log_bundle_id = 12345
  AND component = 'ping'
  AND metric_name IN (
        'ping_all_lost_pkt', 'ping_all_unreachable', 'ping_all_latency')
GROUP BY cvm_ip, target
HAVING loss_samples > 0 OR p95_ms >= 5
ORDER BY loss_samples DESC, p95_ms DESC
LIMIT 200
```

## 10. Host NIC CRC

**Already stored.** `host_nic_stats.INFO`. `component` `network`. Instance is the interface. Metric `host_nic_rx_crc_errors`. The parser keeps the ethtool counter as an absolute total, not a per-second rate. Per-queue keys are dropped at ingest.

`ethtool_rx_crc_errors` is also ingested, from a single `ethtool -S` snapshot. A non-zero snapshot can be CRC from before the bundle. The check uses the `host_nic_stats` series and counts only the increase inside the bundle.

**Add.** No parser. Take the positive step between samples.

**How.** The Panacea NIC check treats a CRC increment above 0 as a physical-layer hit (cable, SFP, or PHY). There is no soft line. An increase during the bundle is investigate. An unchanged counter is status 0, even when the absolute value is already above 0.

```sql
SELECT cvm_ip, iface, sum(delta) AS crc_increase
FROM (
    SELECT cvm_ip,
           component_instance AS iface,
           value - lagInFrame(value) OVER (
               PARTITION BY cvm_ip, component_instance
               ORDER BY event_timestamp
           ) AS delta
    FROM panacea.nu_metrics_sysstats
    WHERE log_bundle_id = 12345
      AND component = 'network'
      AND metric_name = 'host_nic_rx_crc_errors'
)
WHERE delta > 0
GROUP BY cvm_ip, iface
ORDER BY crc_increase DESC
LIMIT 100
```

A CRC increase with SAR drops on the same CVM is the pair to read together. Soft drops with a CRC increase of 0 are not a cable fault.

## Read the status

| Status | Meaning |
|---|---|
| 0 | Under the soft line, or the busy-oplog count is 0 or 5 or more. |
| 1 | At least one object crossed the soft line. |
| 2 | At least one object crossed the hard line. |
| 3 | The series is missing, or the check threw. A data gap, not a performance finding. |

When a query returns nothing, the file was not in the bundle. That check prints status 3. A parser that ran and wrote zero rows is a bug. Re-ingest after each parser, then run that check’s query before moving to the next one.
