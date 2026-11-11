"""Verify exported evidence, aggregate numbers, and audio fidelity."""
from collections import Counter, defaultdict
from pathlib import Path
import csv
import hashlib
import json

import h5py
import numpy as np
import soundfile as sf

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def rows(name):
    with (HERE / 'data' / name).open(newline='') as f:
        return list(csv.DictReader(f))


def main():
    manifest = json.loads((HERE / 'data/manifest.json').read_text())
    for name, expected in manifest['sources'].items():
        assert digest(ROOT / name) == expected, f'Source changed: {name}'
    for kind in ['audio', 'text']:
        item = manifest['registration'][kind]
        assert digest(ROOT / item['checkpoint_relative']) == item['sha256']
    assert len(manifest['examples']) == 25
    assert len({e['room'] for e in manifest['examples']}) == 6
    assert Counter(e['speaker'] for e in manifest['examples']) == {'174': 9, '2086': 8, '2412': 8}
    assert len({e['audio']['dry']['source_float32_sha256'] for e in manifest['examples']}) == 25
    assets = []
    for example in manifest['examples']:
        assert 'hamilton' not in example['rir_id'].lower()
        for name, item in example['audio'].items():
            path = HERE / item['path']; assets.append(path)
            assert digest(path) == item['sha256']
            info = sf.info(path)
            assert info.samplerate == 16000 and info.channels == 1 and info.subtype == 'PCM_16'
            audio, _ = sf.read(path)
            assert len(audio) == item['samples'] and np.isfinite(audio).all()
            assert np.max(np.abs(audio)) <= .95004 and np.max(np.abs(audio)) > .001
        for item in example['source']['checkpoints'].values():
            assert digest(ROOT / item['checkpoint']) == item['sha256']
            assert item['completed_updates'] == 300 and item['metrics_reconstruction_verified']
        # The two stored inputs must survive the exact same gain and PCM16 quantization.
        for name, h5_key, row_key in [('dry','dry_h5','dry_row'),('reference','reference_h5','reference_row')]:
            with h5py.File(ROOT / example['source'][h5_key], 'r') as h:
                row = example['source'][row_key]
                start, n = int(h['offset'][row]), int(h['n_samples'][row])
                source = h['audio'][start:start+n]
                assert h['speech_id'][row].decode() == example['speech_id']
                if name == 'reference': assert h['rir_id'][row].decode() == example['rir_id']
            assert hashlib.sha256(source.astype('<f4').tobytes()).hexdigest() == example['audio'][name]['source_float32_sha256']
            exported, _ = sf.read(HERE / example['audio'][name]['path'])
            assert np.max(np.abs(exported - source * example['common_listening_gain'])) <= 1 / 32768 + 1e-7
    assert len(set(assets)) == 100
    assert set((HERE / 'assets/audio').glob('*.wav')) == set(assets), 'Stale or missing WAV'
    per_pair = rows('per_pair_metrics.csv')
    assert len(per_pair) == 2 * 750 * 4
    assert {e['rir_id'] for e in manifest['examples']} == {r['rir_id'] for r in per_pair}
    assert len({e['rir_id'] for e in manifest['examples']}) == 25
    assert len({e['speech_id'] for e in manifest['examples']}) == 25
    groups = defaultdict(list)
    counts = defaultdict(int)
    for row in per_pair:
        assert row['stage'] == 'final' and row['updates'] == '300'
        groups[(row['model'], row['metric'])].append(row)
        counts[(row['model'], row['job'])] += row['bucket_match'] == 'True'
    for summary in rows('summary.csv'):
        group = groups[(summary['model'], summary['metric'])]
        assert len(group) == int(summary['n']) == 750
        assert np.isclose(np.mean([float(r['absolute_error']) for r in group]), float(summary['mae']), atol=1e-12)
        assert np.isclose(np.mean([r['bucket_match'] == 'True' for r in group]), float(summary['bucket_accuracy']), atol=1e-12)
    for summary in rows('joint_match_summary.csv'):
        match = [value for (model, _), value in counts.items() if model == summary['model']]
        assert len(match) == 750
        assert sum(v >= int(summary['matched']) for v in match) == int(summary['at_least_n'])
    figure = json.loads((HERE / 'data/figure1_representation_geometry_provenance.json').read_text())
    assert figure['centroids_displayed'] is False and figure['test_points'] == 750
    result = dict(status='passed', cases=25, wavs=100, evaluated_pairs_per_model=750,
        checked=['source hashes preserved', 'checkpoint hashes and final update=300',
                 'WAV hashes, PCM16, 16kHz, mono, finite and peak-safe',
                 'dry/reference HDF5 row identity and PCM export fidelity',
                 'MAE, per-attribute region agreement and joint counts recomputed',
                 '25 distinct test RIRs and 25 distinct test utterances, six spaces, three speakers, Hamilton excluded', 'centroid-free latest figure'])
    (HERE / 'data/verification.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
