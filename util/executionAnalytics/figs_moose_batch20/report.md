# Cost report: submission_2aa62ff5_workflows.csv
workflows 3, series 60, Mvox 2633, slices 9167, region ['us-west4'], cost source ['estimate']
total $1.581  = $0.0264/series, $0.00060/Mvox, $0.000173/slice, 11.7 VM-hours

| task | VM-min total | VM-min/series | VM-min/Mvox | attempts | preempted | $ | $ share | eff $/h | catalog $/h |
|---|---|---|---|---|---|---|---|---|---|
| inference | 302 | 5.03 | 0.115 | 4 | 1 | 1.278 | 81% | 0.2539 | 0.2539 |
| outputConversion | 290 | 4.83 | 0.110 | 3 | 0 | 0.303 | 19% | 0.0628 | 0.0628 |

Per-series phase timings (median s / s per Mvox slope):
  downloadSec            median     6.0s  mean     6.1s  slope    0.01 s/Mvox  n=60
  dcm2niixSec            median     1.7s  mean     2.5s  slope    0.06 s/Mvox  n=60
  inferenceSec           median   234.9s  mean   248.9s  slope    1.19 s/Mvox  n=60
  refDownloadSec         median     1.6s  mean     1.7s  slope    0.01 s/Mvox  n=60
  segSec                 median     6.5s  mean     9.1s  slope    0.19 s/Mvox  n=60
  radiomicsSec           median   184.8s  mean   253.8s  slope    4.24 s/Mvox  n=60
  outputConversionSec    median   204.6s  mean   281.4s  slope    4.86 s/Mvox  n=60
  inference time by sub-model (total s):
    clin_ct_digestive                           3418.0
    clin_ct_body_composition                    1715.0
    clin_ct_peripheral_bones                    1506.4
    clin_ct_vertebrae                           1433.1
    clin_ct_ribs                                1406.0
    clin_ct_cardiac                             1284.7
    clin_ct_organs                              1281.1
    clin_ct_muscles                             1116.9
    clin_ct_lungs                               1047.9
    clin_ct_body                                 727.6

Figures: cost_vs_workload.png, task_runtime_vs_workload.png, unit_cost_vs_batch_size.png, cost_by_task_per_workflow.png, series_phase_timings.png, phase_breakdown_per_workflow.png, download_vs_size.png, model_fit.png