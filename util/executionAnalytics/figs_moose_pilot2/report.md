# Cost report: submission_71a2f34a_workflows.csv
workflows 9, series 30, Mvox 1442, slices 4134, region ['us-west4'], cost source ['billing']
total $1.297  = $0.0432/series, $0.00090/Mvox, $0.000314/slice, 11.7 VM-hours

| task | VM-min total | VM-min/series | VM-min/Mvox | attempts | preempted | $ | $ share | eff $/h | catalog $/h |
|---|---|---|---|---|---|---|---|---|---|
| inference | 340 | 11.34 | 0.236 | 23 | 14 | 1.069 | 82% | 0.1886 | 0.2539 |
| outputConversion | 221 | 7.35 | 0.153 | 8 | 0 | 0.228 | 18% | 0.0619 | 0.0628 |

Per-series phase timings (median s / s per Mvox slope):
  downloadSec            median     6.5s  mean     6.5s  slope    0.03 s/Mvox  n=8
  dcm2niixSec            median     1.4s  mean     1.5s  slope    0.05 s/Mvox  n=8
  inferenceSec           median   182.4s  mean   212.7s  slope    0.01 s/Mvox  n=23
  refDownloadSec         median     1.6s  mean     1.7s  slope    0.01 s/Mvox  n=24
  segSec                 median     7.6s  mean    11.6s  slope    0.20 s/Mvox  n=24
  radiomicsSec           median   290.2s  mean   429.1s  slope    9.13 s/Mvox  n=24
  outputConversionSec    median   310.0s  mean   457.6s  slope    9.64 s/Mvox  n=24
  inference time by sub-model (total s):
    clin_ct_digestive                           1013.8
    clin_ct_body_composition                     592.2
    clin_ct_vertebrae                            550.9
    clin_ct_peripheral_bones                     506.4
    clin_ct_ribs                                 474.6
    clin_ct_organs                               435.1
    clin_ct_cardiac                              389.6
    clin_ct_muscles                              381.1
    clin_ct_lungs                                363.4
    clin_ct_body                                 184.2

Actual $ by SKU category: GPU 0.614 (47%), vCPU 0.353 (27%), RAM 0.189 (15%), Disk 0.062 (5%), Egress 0.061 (5%), External IP 0.018 (1%), Other 0.000 (0%)

Figures: cost_vs_workload.png, task_runtime_vs_workload.png, unit_cost_vs_batch_size.png, cost_by_task_per_workflow.png, series_phase_timings.png, phase_breakdown_per_workflow.png, download_vs_size.png, billing_breakdown.png, model_fit.png