"""Export a static listening demo from immutable, final 300-update results.

Run from the repository: .venv/bin/python demo/build_assets.py
No training, CLAP inference, or FDN optimization is performed.
"""
from pathlib import Path
from collections import Counter
import csv
import hashlib
import importlib.util
import json
import shutil
import sys

sys.dont_write_bytecode = True

import h5py
import numpy as np
import soundfile as sf
import torch

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
BASE = ROOT / 'experiments/07_fdn_text_optimization/results'
REPORT = BASE / 'gpu_three_model_physical_comparison'
MODELS = ['raw-clap', 'reverbalign-512-v1']
METRICS = ['rt60_s', 'c50_db', 'drr_db', 'edt_s']
LABELS = ['BUT CR2', 'Wheldrake Wood', 'Creswell Crags · outside',
          'Gill Heads Mine · site 2', 'Hoffmann lime kiln', 'Dixon Studio Theatre']
POLICY = ('Include every one of the 25 held-out RIRs once, sorted by room ID and RIR ID. '
          'Retain the previous speaker-to-RIR assignments: anchor RIRs nearest each '
          'room-median reference RT60 (distance rounded to 12 decimal places; ties: '
          'RIR ID) receive sorted speaker IDs in room-order rotation. Assign remaining RIRs to the '
          'speaker with the fewest examples so far (ties: numeric speaker ID), '
          'starting from the six anchors. In displayed RIR order, assign each speaker\'s '
          'next unused lexicographically sorted test utterance, starting at index 0. '
          'All 25 utterances are distinct. Speakers 174, 2086, and 2412 have 9, 8, '
          'and 8 examples respectively, selected from their 10 test utterances each. '
          'No output metric or listening judgment is used. Aggregate statistics '
          'continue to use all 750 test pairs.')


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_csv(path):
    with path.open(newline='') as stream:
        return list(csv.DictReader(stream))


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False) + '\n')


def portable_provenance(value):
    """Source identifiers are provenance, never machine-specific runtime paths."""
    if isinstance(value, dict):
        return {k: portable_provenance(v) for k, v in value.items()}
    if isinstance(value, list):
        return [portable_provenance(v) for v in value]
    if isinstance(value, str) and value.startswith(str(ROOT) + '/'):
        return value[len(str(ROOT)) + 1:]
    return value


def audio_row(handle, index):
    start, count = int(handle['offset'][index]), int(handle['n_samples'][index])
    return handle['audio'][start:start + count]


def main():
    torch.set_num_threads(1)
    prior_manifest = HERE / 'data/manifest.json'
    prior_assets = set()
    if prior_manifest.exists():
        prior_assets = {a['path'] for ex in json.loads(prior_manifest.read_text())['examples']
                        for a in ex['audio'].values()}
    # Import the audited renderer as a library; its main() is never called.
    spec = importlib.util.spec_from_file_location('saved_fdn_evaluation',
        ROOT / 'experiments/07_fdn_text_optimization/evaluate_gpu_checkpoints.py')
    renderer = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(renderer)
    registration = json.loads((ROOT / 'configs/adapter_pairs/reverbalign_512_v1.json').read_text())
    for kind in ['audio', 'text']:
        item = registration[kind]
        assert sha(ROOT / item['checkpoint_relative']) == item['sha256']
    audit = json.loads((REPORT / 'audit.json').read_text())
    config = audit['source_configs']['reverbalign-512-v1']
    assert config['adapter_pair'] == registration['id'] and config['steps'] == 300
    for kind in ['audio', 'text']:
        assert config[kind + '_checkpoint'].endswith('/' + registration[kind]['checkpoint_relative'])
    (HERE / 'assets/audio').mkdir(parents=True, exist_ok=True)
    (HERE / 'assets/figures').mkdir(parents=True, exist_ok=True)
    (HERE / 'data').mkdir(exist_ok=True)
    indexes = {}
    for model in MODELS:
        paths = sorted((BASE / ('[gpu]' + model)).glob('pair_*/pair.json'))
        indexes[model] = {}
        for path in paths:
            pair = json.loads(path.read_text())
            indexes[model][(pair['rir_id'], pair['speech_id'])] = (path.parent, pair)
        assert len(indexes[model]) == 750
    assert indexes[MODELS[0]].keys() == indexes[MODELS[1]].keys()
    pairs = [pair for _, pair in indexes[MODELS[0]].values()]
    rooms = sorted({p['room_id'] for p in pairs})
    speakers = sorted({p['speech_id'].split('/')[0] for p in pairs}, key=int)
    assert len(rooms) == 6 and speakers == ['174', '2086', '2412']
    assert len({p['rir_id'] for p in pairs}) == 25
    assert not any('hamilton' in p['rir_id'].lower() for p in pairs)
    anchors = {}
    room_medians = {}
    for i, room in enumerate(rooms):
        rirs = {p['rir_id']: float(p['caption']['rt60_s']) for p in pairs if p['room_id'] == room}
        median = float(np.median(list(rirs.values())))
        room_medians[room] = median
        rir = min(rirs, key=lambda r: (round(abs(rirs[r] - median), 12), r))
        speaker = speakers[i % len(speakers)]
        anchors[rir] = speaker
    speaker_counts = Counter(anchors.values())
    utterances_by_speaker = {speaker: sorted({p['speech_id'] for p in pairs
        if p['speech_id'].split('/')[0] == speaker}) for speaker in speakers}
    assert all(len(utterances) == 10 for utterances in utterances_by_speaker.values())
    used_utterances = Counter()
    chosen = []
    for room in rooms:
        for rir in sorted({p['rir_id'] for p in pairs if p['room_id'] == room}):
            if rir in anchors:
                speaker = anchors[rir]
            else:
                speaker = min(speakers, key=lambda s: (speaker_counts[s], int(s)))
                speaker_counts[speaker] += 1
            speech = utterances_by_speaker[speaker][used_utterances[speaker]]
            used_utterances[speaker] += 1
            chosen.append((rir, speech, room_medians[room], room))
    assert len(chosen) == 25 and dict(speaker_counts) == {'174': 9, '2086': 8, '2412': 8}
    assert len({speech for _, speech, _, _ in chosen}) == 25

    rows = [r for r in read_csv(REPORT / 'per_pair_metrics.csv')
            if r['stage'] == 'final' and r['model'] in MODELS]
    metric_index = {(r['model'], r['rir_id'], r['speech_id'], r['metric']): r for r in rows}
    summary = [r for r in read_csv(REPORT / 'summary.csv') if r['stage'] == 'final' and r['model'] in MODELS]
    joint = [r for r in read_csv(REPORT / 'joint_match_summary.csv') if r['stage'] == 'final' and r['model'] in MODELS]
    edges = json.loads((ROOT / registration['caption_buckets_relative']).read_text())['edges']
    exported = []
    with h5py.File(ROOT / 'experiments/00_embeddings_comparison/dry_200.h5', 'r') as dry_h5, \
         h5py.File(ROOT / 'experiments/00_embeddings_comparison/convolution_200.h5', 'r') as wet_h5:
        assert int(dry_h5.attrs['sample_rate_hz']) == int(wet_h5.attrs['sample_rate_hz']) == 16000
        dry_ids = dry_h5['speech_id'][:].astype(str)
        wet_rirs, wet_speech = wet_h5['rir_id'][:].astype(str), wet_h5['speech_id'][:].astype(str)
        for i, (rir, speech, median, room) in enumerate(chosen):
            key = (rir, speech)
            directory, pair = indexes[MODELS[0]][key]
            assert all(indexes[m][key][1] == pair for m in MODELS)
            di = int(np.flatnonzero(dry_ids == speech).item())
            wi = int(np.flatnonzero((wet_rirs == rir) & (wet_speech == speech)).item())
            assert dry_h5['speech_split'][di].decode() == 'test'
            dry, reference = audio_row(dry_h5, di), audio_row(wet_h5, wi)
            signals = {'dry': dry, 'reference': reference}
            provenance = {}
            values = {'reference': {m: float(pair['caption'][m]) for m in METRICS}}
            matches = {}
            initial = None
            for model in MODELS:
                directory, _ = indexes[model][key]
                checkpoint_path = directory / 'final_checkpoint.pt'
                checkpoint = renderer.load(checkpoint_path)
                assert checkpoint['completed_updates'] == 300
                state = renderer.load(directory / 'initial_checkpoint.pt')['fdn_state']
                if initial is None:
                    initial = state
                else:
                    assert initial.keys() == state.keys() and all(torch.equal(initial[k], state[k]) for k in state)
                response, nfft = renderer.reconstruct(checkpoint['fdn_state'])
                measured = renderer.measure(response)
                values[model], matches[model] = {}, 0
                for metric in METRICS:
                    row = metric_index[(model, rir, speech, metric)]
                    assert np.isclose(measured[metric], float(row['prediction']), rtol=1e-5, atol=1e-4)
                    values[model][metric] = float(row['prediction'])
                    matches[model] += row['bucket_match'] == 'True'
                # Full convolution followed by the same 10-second cap as the evaluated run.
                full_length = len(dry) + len(response) - 1
                conv_nfft = 1 << (full_length - 1).bit_length()
                signals[model] = torch.fft.irfft(
                    torch.fft.rfft(torch.from_numpy(dry), n=conv_nfft) *
                    torch.fft.rfft(torch.from_numpy(response), n=conv_nfft), n=conv_nfft
                )[:min(full_length, 160000)].numpy()
                provenance[model] = dict(checkpoint=str(checkpoint_path.relative_to(ROOT)),
                    sha256=sha(checkpoint_path), completed_updates=300, nfft=nfft,
                    rir_samples=len(response), metrics_reconstruction_verified=True)
            assert all(np.isfinite(s).all() for s in signals.values())
            # One shared scalar for all four signals in this case. No per-clip normalization.
            gain = .95 / max(float(np.max(np.abs(s))) for s in signals.values())
            assets = {}
            for name, signal in signals.items():
                path = HERE / 'assets/audio' / f'{pair["job_id"]}_{name}.wav'
                sf.write(path, signal * gain, 16000, subtype='PCM_16')
                assets[name] = dict(path=str(path.relative_to(HERE)), sha256=sha(path),
                    samples=len(signal), seconds=len(signal) / 16000,
                    source_float32_sha256=hashlib.sha256(signal.astype('<f4').tobytes()).hexdigest())
            title = LABELS[rooms.index(room)]
            exported.append(dict(number=i + 1, title=title, job=pair['job_id'],
                folder=directory.name, rir_id=rir, room=room, speech_id=speech,
                speaker=speech.split('/')[0], caption_id=pair['caption_id'],
                caption=pair['caption']['caption'], values=values, matches=matches,
                room_median_rt60=median, common_listening_gain=gain, audio=assets,
                source=dict(dry_h5='experiments/00_embeddings_comparison/dry_200.h5', dry_row=di,
                    reference_h5='experiments/00_embeddings_comparison/convolution_200.h5', reference_row=wi,
                    reference_policy='Exact stored measured-RIR convolution; full then truncate to 10s.',
                    checkpoints=provenance)))
            print(f'Exported {pair["job_id"]}: {title} | region matches {matches}', flush=True)

    figure = ROOT / 'output/pdf/figure1_representation_geometry.svg'
    shutil.copyfile(figure, HERE / 'assets/figures/representation.svg')
    for source in ['figure1_representation_geometry_provenance.json', 'figure1_distance_summary.csv']:
        source_path = ROOT / 'output/pdf' / source
        if source_path.suffix == '.json':
            write_json(HERE / 'data' / source, portable_provenance(json.loads(source_path.read_text())))
        else:
            shutil.copyfile(source_path, HERE / 'data' / source)
    for name, data in [('summary.csv', summary), ('joint_match_summary.csv', joint), ('per_pair_metrics.csv', rows)]:
        with (HERE / 'data' / name).open('w', newline='') as stream:
            writer = csv.DictWriter(stream, fieldnames=list(data[0])); writer.writeheader(); writer.writerows(data)
    manifest = dict(model='ReverbAlign-512-v1', selection_policy=POLICY,
        evaluation=dict(pairs=750, rirs=25, utterances=30, speakers=3, rooms=6, updates=300,
            stage='final', hamilton_16s_excluded=True, caption_combinations=96,
            caption_levels=[4, 4, 2, 3], free_form_input=False),
        audio_policy='Saved final FDN checkpoints rendered with the audited CPU float32 renderer; '
            'no optimization or CLAP inference. L2 RIR normalization; dry convolved then capped at 10s. '
            'Reference from stored convolution HDF5. All four tracks share one peak-safety gain '
            'per case (maximum 0.95); mono 16-kHz PCM16. No per-track loudness normalization.',
        bucket_edges=edges, registration=portable_provenance(registration), examples=exported,
        sources={str(p.relative_to(ROOT)): sha(p) for p in [
            ROOT / 'paper/main.tex', ROOT / 'configs/adapter_pairs/reverbalign_512_v1.json',
            REPORT / 'per_pair_metrics.csv', REPORT / 'summary.csv', REPORT / 'joint_match_summary.csv',
            REPORT / 'audit.json', REPORT / 'source_verification.json',
            ROOT / 'experiments/07_fdn_text_optimization/evaluate_gpu_checkpoints.py', figure]},
        figure_centroids_displayed=False)
    write_json(HERE / 'data/manifest.json', manifest)
    current_assets = {a['path'] for ex in exported for a in ex['audio'].values()}
    for relative in prior_assets - current_assets:
        stale = HERE / relative
        if stale.parent == HERE / 'assets/audio' and stale.suffix == '.wav':
            stale.unlink(missing_ok=True)
    # Local-file friendly: no network requests, bundler, or server needed to load data.
    (HERE / 'data/demo-data.js').write_text('window.REVERB_DEMO = ' + json.dumps(dict(
        examples=exported, summary=summary, joint=joint, edges=edges), ensure_ascii=False) + ';\n')
    write_json(HERE / 'data/availability.json', dict(current_result_pairs_per_model=750,
        current_result_format='final/initial/best FDN checkpoints and history; no pre-existing WAVs',
        exported_cases=len(exported), exported_listening_wavs=4 * len(exported),
        reference_available=True,
        historical_wavs='Available under test_full_* and single-case experiment folders; excluded because '
            'they are not the current matched CUDA ReverbAlign-512-v1 comparison.'))


if __name__ == '__main__':
    main()
