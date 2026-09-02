# Cost report: submission_3951836b_workflows.csv
workflows 3, series 60, Mvox 2633, slices 9167, region ['us-west4'], cost source ['estimate']
total $0.942  = $0.0157/series, $0.00036/Mvox, $0.000103/slice, 7.2 VM-hours

| task | VM-min total | VM-min/series | VM-min/Mvox | attempts | preempted | $ | $ share | eff $/h | catalog $/h |
|---|---|---|---|---|---|---|---|---|---|
| inference | 185 | 3.09 | 0.070 | 7 | 4 | 0.785 | 83% | 0.2539 | 0.2539 |
| outputConversion | 150 | 2.50 | 0.057 | 3 | 0 | 0.157 | 17% | 0.0628 | 0.0628 |

Per-series phase timings (median s / s per Mvox slope):
  downloadSec            median     6.0s  mean     6.1s  slope    0.01 s/Mvox  n=60
  dcm2niixSec            median     1.6s  mean     2.5s  slope    0.06 s/Mvox  n=60
  inferenceSec           median   116.9s  mean   122.8s  slope    0.32 s/Mvox  n=60
  refDownloadSec         median     1.6s  mean     1.6s  slope    0.01 s/Mvox  n=60
  segSec                 median     0.9s  mean     1.2s  slope    0.03 s/Mvox  n=60
  radiomicsSec           median    94.0s  mean   137.6s  slope    2.93 s/Mvox  n=60
  outputConversionSec    median    99.1s  mean   142.3s  slope    3.00 s/Mvox  n=60
  inference time by sub-model (total s):
    total                                       7370.8

Figures: cost_vs_workload.png, task_runtime_vs_workload.png, unit_cost_vs_batch_size.png, cost_by_task_per_workflow.png, series_phase_timings.png, phase_breakdown_per_workflow.png, download_vs_size.png, model_fit.png