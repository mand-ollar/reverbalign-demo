# ReverbAlign paper demo

A static, English-language companion page for the ReverbAlign paper. The page plays saved experimental results. All demo files and exported assets are contained in this folder. The original paper, training code, and checkpoints are preserved.

## Move, preview, or publish the demo

**Copy the entire `demo/` folder.** The page, 100 WAV files, representation figure, numerical results, and case manifest are included. All runtime assets use relative paths. Playback and static hosting work without the original research repository, external libraries, web fonts, API services, model execution, or a build step.

To preview the demo locally, run this command from inside the copied folder:

```sh
python3 serve.py
```

Open [http://127.0.0.1:8765](http://127.0.0.1:8765). If that port is in use, run `python3 serve.py --port 8766` and open the corresponding address. Keep the server running while listening. Opening `index.html` directly in a regular browser is also possible, but an HTTP preview is recommended.

For GitHub Pages or another static host, place this folder's **contents** at the site root, with `index.html`, `assets/`, and `data/` at the same level. An empty `.nojekyll` file is included. Python scripts are local utilities; the published page runs entirely in the browser.

To verify that the copied folder is complete, run:

```sh
python3 verify_portable.py
```

This check uses only the Python standard library and files inside the demo folder. It does not access the research repository.

## Included content

The page uses a compact paper header followed by listening examples. Aggregate results and the representation figure are available in a collapsed section near the top.

- **25 examples covering all 25 test RIRs from six spaces**, each paired with a different test utterance. Speakers 174, 2086, and 2412 contribute 9, 8, and 8 examples, respectively.
- The actual fixed acoustic caption and four matched tracks for each example: dry speech, Raw CLAP, ReverbAlign-512-v1, and a measured-RIR reference. There are **100 WAV files** in total.
- Five examples per page, with Previous / Next navigation and space filter buttons. Metadata for all 20 tracks on the current page loads immediately. Each track also provides a direct WAV link.
- Single-track playback. Optional position transfer within a case is disabled by default; when enabled, it applies only when switching from a currently playing track.
- Per-case RIR measurements and caption-region match counts, plus MAE and region agreement over the complete 750-pair test set.
- The latest Raw CLAP vs ReverbAlign representation SVG, with no centroid markers.
- Source identifiers, SHA-256 hashes, selection and export policies in `data/manifest.json`, and final-state measurement CSVs for both models over all 750 matched pairs.

## Results and audio sources

The values in the source paper, `paper/main.tex`, match the `final` results in:

```text
experiments/07_fdn_text_optimization/results/gpu_three_model_physical_comparison/
```

The main comparison is **Raw CLAP vs ReverbAlign-512-v1**. Legacy-Best, the historical 780-pair results, best-loss checkpoints, free-form text experiments, and four-level DRR experiments are excluded.

The evaluation contains 25 RIRs × 30 utterances = **750 pairs**, spanning six spaces and three speakers. Hamilton's approximately 16-second RIR is excluded. Captions use the fixed 4 RT60 × 4 C50 × 2 DRR × 3 EDT vocabulary, giving 96 possible combinations.

The source `[gpu]raw-clap` and `[gpu]reverbalign-512-v1` directories contain final, initial, and best FDN checkpoints and optimization histories for 750 pairs per model, rather than pre-existing WAVs. Historical WAVs under `test_full_*` belong to earlier experiments and are not substituted for the current comparison. The source inventory is documented in `data/availability.json`.

The listening files were rendered from the saved **final 300-update FDN checkpoints** using the renderer in `evaluate_gpu_checkpoints.py`. No further optimization, CLAP inference, or training was performed. All four reconstructed RIR attributes were checked against the saved per-pair evaluation before convolution with the corresponding processed dry speech. Reference audio comes from the exactly matching stored rows in `convolution_200.h5`.

The WAV files are mono, 16-kHz PCM16. Generated RIRs retain the original L2 normalization and full-convolution-then-truncate policy, with a maximum output duration of 10 seconds. All four tracks in a case share **one gain**, setting the largest peak across those tracks to 0.95. Individual tracks are not loudness-normalized, so their relative levels are preserved. Gain can differ between cases. The original dry inputs were prepared at −18 LUFS. The 10-second cap can truncate late reverberation in some examples.

## Example selection

Every test RIR appears once, and **all 25 selected utterances are different**. Selection does not use model output scores or listening judgments.

1. Sort RIRs lexicographically by room ID, then RIR ID. Repeated space names denote different RIRs from that space.
2. Assign speakers using six anchor RIRs: the RIR nearest each space's median reference RT60 receives a speaker from the rotation 174, 2086, 2412 in room-ID order. RT60 distances are rounded to 12 decimal places, with ties resolved by RIR ID. Starting with these six assignments, assign each remaining RIR to the least-represented speaker, breaking ties by numeric speaker ID. The final counts are 9 / 8 / 8.
3. Sort each speaker's ten test utterances lexicographically by ID. In display order, give each case that speaker's **next unused utterance**, starting with the first. Speaker 174 uses its first nine utterances; speakers 2086 and 2412 each use their first eight.
4. Dry, Raw CLAP, ReverbAlign, and Reference tracks within a case correspond to the same utterance and caption/RIR target. Each optimized track uses the final checkpoint for that exact pair; results optimized for another utterance are not reused.

The demo covers all 25 test RIRs and 25 of the 30 test utterances. It is not a random sample. Aggregate performance is reported over **all 750 pairs**, independently of the displayed examples. Cases where ReverbAlign matches fewer target regions are retained. Case IDs, utterance IDs, source rows, and checkpoint hashes are recorded in the manifest.

Research-repository paths in the provenance are source identifiers. They are not runtime dependencies and are not opened by the page.

## Regenerate and audit against the research sources

Viewing the published static page requires only a browser. The original repository and research environment are needed only to regenerate the exported audio or audit it against the original HDF5 data and checkpoints.

From the research repository root, run:

```sh
.venv/bin/python demo/build_assets.py
.venv/bin/python demo/verify_assets.py
node --check demo/app.js
```

`build_assets.py` writes only inside the demo folder. It imports the existing renderer and calls its reconstruction functions without running that module's `main()`. It verifies registered model checkpoint hashes, matched pair metadata and initial FDN states, the final update count of 300, and agreement between reconstructed and saved RIR metrics.

`verify_assets.py` checks WAV formats, hashes and peaks; preservation of source files; full-test aggregates; and fidelity of the dry and reference exports to their source HDF5 rows.

For a copied demo without the research sources, use `python3 verify_portable.py` instead.

## Folder contents

```text
demo/
  index.html, styles.css, app.js   Static page
  .nojekyll                       Static publishing marker
  assets/audio/                   100 listening WAVs
  assets/figures/representation.svg
  data/                           Results, provenance, and case manifest
  qa/                             Browser verification and screenshots
  build_assets.py                 Offline export from saved research results
  verify_assets.py                Audit against original research sources
  verify_portable.py              Standalone folder check; standard library only
  serve.py                        Local preview from any folder location
  README.md
```
