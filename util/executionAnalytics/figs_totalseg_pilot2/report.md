# Cost report: submission_02b36d47_workflows.csv
workflows 9, series 30, Mvox 1442, slices 4134, region ['us-west4'], cost source ['billing']
total $0.794  = $0.0265/series, $0.00055/Mvox, $0.000192/slice, 9.4 VM-hours

| task | VM-min total | VM-min/series | VM-min/Mvox | attempts | preempted | $ | $ share | eff $/h | catalog $/h |
|---|---|---|---|---|---|---|---|---|---|
| inference | 185 | 6.16 | 0.128 | 15 | 6 | 0.644 | 81% | 0.2093 | 0.2539 |
| outputConversion | 133 | 4.42 | 0.092 | 9 | 0 | 0.150 | 19% | 0.0677 | 0.0628 |

Per-series phase timings (median s / s per Mvox slope):
  downloadSec            median     6.5s  mean     6.6s  slope    0.00 s/Mvox  n=27
  dcm2niixSec            median     1.7s  mean     2.6s  slope    0.04 s/Mvox  n=27
  inferenceSec           median    99.4s  mean   104.4s  slope    0.55 s/Mvox  n=29
  refDownloadSec         median     1.6s  mean     1.8s  slope    0.01 s/Mvox  n=30
  segSec                 median     0.8s  mean     1.3s  slope    0.02 s/Mvox  n=30
  radiomicsSec           median   134.2s  mean   218.1s  slope    5.87 s/Mvox  n=30
  outputConversionSec    median   138.4s  mean   222.5s  slope    5.92 s/Mvox  n=30
  inference time by sub-model (total s):
    total                                       3027.2

Actual $ by SKU category: GPU 0.350 (44%), vCPU 0.212 (27%), RAM 0.114 (14%), Egress 0.070 (9%), Disk 0.038 (5%), External IP 0.011 (1%), Other 0.000 (0%)

Figures: cost_vs_workload.png, task_runtime_vs_workload.png, unit_cost_vs_batch_size.png, cost_by_task_per_workflow.png, series_phase_timings.png, phase_breakdown_per_workflow.png, download_vs_size.png, billing_breakdown.png, model_fit.png