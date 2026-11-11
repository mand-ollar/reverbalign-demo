"""Validate the complete static demo using only files inside this folder.

Python standard library only; no research repository, HDF5, model or network needed.
"""
from array import array
from collections import Counter
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit
import csv
import hashlib
import json
import math
import re
import statistics
import sys
import wave

HERE = Path(__file__).resolve().parent


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def local_file(reference):
    url = urlsplit(reference)
    assert not url.scheme and not url.netloc, f'External dependency: {reference}'
    assert not url.path.startswith('/'), f'Absolute asset path: {reference}'
    if not url.path:
        return
    path = (HERE / unquote(url.path)).resolve()
    assert path.is_relative_to(HERE), f'Asset escapes demo: {reference}'
    assert path.is_file(), f'Missing asset: {reference}'


class StaticLinks(HTMLParser):
    def handle_starttag(self, tag, attrs):
        for key, value in attrs:
            if key in ['src', 'href'] and value:
                local_file(value)


def csv_rows(name):
    with (HERE / 'data' / name).open(newline='') as stream:
        return list(csv.DictReader(stream))


def main():
    assert not any(path.is_symlink() for path in HERE.rglob('*')), 'Symlink depends on another folder'
    StaticLinks().feed((HERE / 'index.html').read_text())
    for url in re.findall(r'url\([\s\"\']*([^\)\"\']+)', (HERE / 'styles.css').read_text()):
        local_file(url.strip())
    manifest = json.loads((HERE / 'data/manifest.json').read_text())
    examples = manifest['examples']
    assert len(examples) == len({e['rir_id'] for e in examples}) == len({e['speech_id'] for e in examples}) == 25
    assert len({e['audio']['dry']['source_float32_sha256'] for e in examples}) == 25
    assert Counter(e['speaker'] for e in examples) == {'174': 9, '2086': 8, '2412': 8}
    assert len({e['room'] for e in examples}) == 6
    bundled = (HERE / 'data/demo-data.js').read_text().strip()
    assert bundled.startswith('window.REVERB_DEMO = ') and bundled.endswith(';')
    assert json.loads(bundled[len('window.REVERB_DEMO = '):-1])['examples'] == examples
    metrics = csv_rows('per_pair_metrics.csv')
    assert len(metrics) == 2 * 750 * 4
    lookup = {(r['job'], r['model'], r['metric']): r for r in metrics}
    assets = set()
    for ex in examples:
        assert 'hamilton' not in ex['rir_id'].lower()
        for model in ['raw-clap', 'reverbalign-512-v1']:
            matches = 0
            for metric, prediction in ex['values'][model].items():
                row = lookup[(ex['job'], model, metric)]
                assert row['rir_id'] == ex['rir_id'] and row['speech_id'] == ex['speech_id']
                assert row['stage'] == 'final' and row['updates'] == '300'
                assert math.isclose(prediction, float(row['prediction']), abs_tol=1e-12)
                assert math.isclose(ex['values']['reference'][metric], float(row['reference']), abs_tol=1e-12)
                matches += row['bucket_match'] == 'True'
            assert matches == ex['matches'][model]
        for item in ex['audio'].values():
            local_file(item['path'])
            path = HERE / item['path']
            assets.add(path)
            assert digest(path) == item['sha256']
            with wave.open(str(path), 'rb') as source:
                assert source.getframerate() == 16000 and source.getnchannels() == 1
                assert source.getsampwidth() == 2 and source.getnframes() == item['samples']
                values = array('h', source.readframes(source.getnframes()))
                if sys.byteorder != 'little':
                    values.byteswap()
                assert 0 < max(abs(v) for v in values) <= 31132
    assert len(assets) == 100 and assets == set((HERE / 'assets/audio').glob('*.wav'))
    for summary in csv_rows('summary.csv'):
        group = [r for r in metrics if r['model'] == summary['model'] and r['metric'] == summary['metric']]
        assert len(group) == 750
        assert math.isclose(statistics.mean(float(r['absolute_error']) for r in group), float(summary['mae']), abs_tol=1e-12)
    figure = json.loads((HERE / 'data/figure1_representation_geometry_provenance.json').read_text())
    assert figure['centroids_displayed'] is False
    assert digest(HERE / 'assets/figures/representation.svg') == manifest['sources']['output/pdf/figure1_representation_geometry.svg']
    result = dict(status='passed', self_contained=True, examples=25, unique_utterances=25,
        unique_rirs=25, wavs=100, speaker_counts=dict(Counter(e['speaker'] for e in examples)),
        checks=['all HTML/CSS/audio asset paths resolve inside the demo folder',
                'no symlinks or external static dependencies', 'all WAV hashes, formats and sample counts',
                '25 different utterances and all 25 RIRs', 'case metadata and RIR metrics match bundled CSV',
                'bundled full-test MAE recomputed', 'latest representation SVG hash'],
        dependencies='Python standard library only; original repository not accessed')
    (HERE / 'data/portable-verification.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
