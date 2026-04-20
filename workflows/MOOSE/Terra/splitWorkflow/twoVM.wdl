version 1.0

# ============================================================================
# MOOSE twoVM Workflow
# ----------------------------------------------------------------------------
# Task 1 (GPU): Download DICOM → Convert to NIfTI → Run moosez inference
# Task 2 (CPU): Post-process segmentations → Generate DICOM-SEG → Compress
#
# Based on twoVM pattern from Thiriveedhi et al. 2024 (CloudSegmentator).
# ============================================================================

workflow MOOSE {
  input {
    # ------------------------------------------------------------------------
    # REQUIRED INPUTS (no defaults — user must provide via Terra UI)
    # ------------------------------------------------------------------------

    # YAML list of SeriesInstanceUIDs to process (passed verbatim to papermill -y)
    String yamlListOfSeriesInstanceUIDs

    # ------------------------------------------------------------------------
    # ANALYSIS PARAMETERS (commonly overridden per run)
    # ------------------------------------------------------------------------

    # Comma-separated moosez model names
    # Available: clin_ct_organs, clin_ct_ribs, clin_ct_vertebrae, clin_ct_body,
    #            clin_ct_muscles, clin_ct_cardiac, clin_ct_lungs
    String mooseModels = "clin_ct_organs,clin_ct_ribs,clin_ct_vertebrae"

    # Accelerator for moosez: 'cuda' for GPU, 'cpu' for CPU-only
    String accelerator = "cuda"

    # ------------------------------------------------------------------------
    # INFERENCE TASK (GPU) — download, convert, run moosez
    # ------------------------------------------------------------------------

    String mooseInferenceDocker = "sunderlandkyl/moose-test:latest"

    Int mooseInferencePreemptibleTries = 3
    Int mooseInferenceCpus = 4
    Int mooseInferenceRAM = 16
    Int mooseInferenceDiskGB = 50
    String mooseInferenceDiskType = "HDD"

    String mooseInferenceGpuType = "nvidia-tesla-t4"
    Int mooseInferenceGpuCount = 1

    # Single region only — Google Cloud Batch requires all zones in one region
    String mooseInferenceZones = "us-east4-a us-east4-b us-east4-c"

    # ------------------------------------------------------------------------
    # POST-PROCESSING TASK (CPU-only) — DICOM-SEG generation, compression
    # ------------------------------------------------------------------------

    String moosePostProcessDocker = "imagingdatacommons/dicom_seg_pyradiomics_sr:main"

    Int moosePostProcessPreemptibleTries = 3
    Int moosePostProcessCpus = 4
    Int moosePostProcessRAM = 16
    Int moosePostProcessDiskGB = 20
    String moosePostProcessDiskType = "HDD"

    # AMD Rome (N2D) is cheapest CPU family on Terra per Thiriveedhi et al.
    String moosePostProcessCpuFamily = "AMD Rome"

    String moosePostProcessZones = "us-east4-a us-east4-b us-east4-c"
  }

  # ==========================================================================
  # Task 1: GPU inference
  # ==========================================================================
  call mooseInference {
    input:
      yamlListOfSeriesInstanceUIDs = yamlListOfSeriesInstanceUIDs,
      mooseModels                  = mooseModels,
      accelerator                  = accelerator,
      docker                       = mooseInferenceDocker,
      preemptibleTries             = mooseInferencePreemptibleTries,
      cpus                         = mooseInferenceCpus,
      ram                          = mooseInferenceRAM,
      diskGB                       = mooseInferenceDiskGB,
      diskType                     = mooseInferenceDiskType,
      gpuType                      = mooseInferenceGpuType,
      gpuCount                     = mooseInferenceGpuCount,
      zones                        = mooseInferenceZones
  }

  # ==========================================================================
  # Task 2: CPU post-processing
  # ==========================================================================
  call moosePostProcess {
    input:
      inferenceOutputArchive = mooseInference.segmentationArchive,
      docker                 = moosePostProcessDocker,
      preemptibleTries       = moosePostProcessPreemptibleTries,
      cpus                   = moosePostProcessCpus,
      ram                    = moosePostProcessRAM,
      diskGB                 = moosePostProcessDiskGB,
      diskType               = moosePostProcessDiskType,
      cpuFamily              = moosePostProcessCpuFamily,
      zones                  = moosePostProcessZones
  }

  # ==========================================================================
  # Outputs
  # ==========================================================================
  output {
    # Notebooks with logs for debugging
    File mooseInferenceNotebook   = mooseInference.outputNotebook
    File moosePostProcessNotebook = moosePostProcess.outputNotebook

    # Usage metrics (CPU/GPU/RAM over time)
    File mooseInferenceUsageMetrics   = mooseInference.usageMetrics
    File moosePostProcessUsageMetrics = moosePostProcess.usageMetrics

    # Primary outputs
    File mooseSegmentations    = mooseInference.segmentationArchive
    File mooseDicomSegFiles    = moosePostProcess.dicomSegArchive

    # Optional error files (only produced if errors occurred)
    File? downloadErrors       = mooseInference.downloadErrors
    File? dcm2niixErrors       = mooseInference.dcm2niixErrors
    File? mooseInferenceErrors = mooseInference.inferenceErrors
    File? dicomSegErrors       = moosePostProcess.dicomSegErrors
  }
}


# ============================================================================
# TASK: Inference (GPU)
# Downloads DICOM, converts to NIfTI, runs moosez segmentation.
# Output: tarball of NIfTI segmentation masks + source NIfTI volumes.
# ============================================================================
task mooseInference {
  input {
    String yamlListOfSeriesInstanceUIDs
    String mooseModels
    String accelerator
    String docker
    Int    preemptibleTries
    Int    cpus
    Int    ram
    Int    diskGB
    String diskType
    String gpuType
    Int    gpuCount
    String zones
  }

  command {
    set -e

    # Pin to a specific commit for reproducibility (update SHA as needed)
    wget https://raw.githubusercontent.com/Sunderlandkyl/CloudSegmentator/moose_test/workflows/MOOSE/Notebooks/endToEndMOOSENotebook.ipynb

    papermill endToEndMOOSENotebook.ipynb mooseInferenceOutputNotebook.ipynb \
      -y "~{yamlListOfSeriesInstanceUIDs}" \
      -p moose_models "~{mooseModels}" \
      -p accelerator "~{accelerator}" \
      || (>&2 echo "Inference task failed" && exit 1)
  }

  runtime {
    docker:      docker
    cpu:         cpus
    memory:      ram + " GiB"
    disks:       "local-disk " + diskGB + " " + diskType
    gpuType:     gpuType
    gpuCount:    gpuCount
    zones:       zones
    preemptible: preemptibleTries
    maxRetries:  1
  }

  output {
    File outputNotebook       = "mooseInferenceOutputNotebook.ipynb"
    File segmentationArchive  = "moose_segmentations.tar.lz4"
    File usageMetrics         = "moose_inference_UsageMetrics.lz4"

    File? downloadErrors      = "download_error_file.txt"
    File? dcm2niixErrors      = "dcm2niix_error_file.txt"
    File? inferenceErrors     = "moose_errors.txt"
  }
}


# ============================================================================
# TASK: Post-processing (CPU)
# Takes NIfTI segmentations from inference task, converts to DICOM-SEG format,
# compresses outputs. Runs on cheaper CPU-only VM (AMD Rome / N2D).
# ============================================================================
task moosePostProcess {
  input {
    File   inferenceOutputArchive
    String docker
    Int    preemptibleTries
    Int    cpus
    Int    ram
    Int    diskGB
    String diskType
    String cpuFamily
    String zones
  }

  command {
    set -o xtrace
    set -o pipefail
    set +o errexit

    wget https://raw.githubusercontent.com/Sunderlandkyl/CloudSegmentator/main/workflows/MOOSE/Notebooks/moosePostProcessNotebook.ipynb

    papermill moosePostProcessNotebook.ipynb moosePostProcessOutputNotebook.ipynb \
      -p segmentationArchivePath ~{inferenceOutputArchive}

    set -o errexit
    exit $?
  }

  runtime {
    docker:      docker
    cpu:         cpus
    cpuPlatform: cpuFamily
    memory:      ram + " GiB"
    disks:       "local-disk " + diskGB + " " + diskType
    zones:       zones
    preemptible: preemptibleTries
    maxRetries:  1
  }

  output {
    File outputNotebook     = "moosePostProcessOutputNotebook.ipynb"
    File dicomSegArchive    = "moose_dicom_seg.tar.lz4"
    File usageMetrics       = "moose_postprocess_UsageMetrics.lz4"

    File? dicomSegErrors    = "dicom_seg_error_file.txt"
  }
}
