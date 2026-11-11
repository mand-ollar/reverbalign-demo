# ReverbAlign paper demo

논문용 **영문 정적 데모 페이지**입니다. 모든 작업 파일과 복사한 자료는 이 `demo/` 안에 있습니다. 서버에서 모델을 실행하거나 학습하지 않습니다. 기존 논문, 학습 코드, checkpoint는 수정하지 않습니다.

## 폴더를 옮겨서 열기 / 배포하기

**`demo/` 전체만 복사하면 됩니다.** 페이지, 100개 WAV, 그림, 수치 CSV, 사례 manifest가 모두 이 폴더 안에 들어 있으며, 페이지에서 사용하는 파일은 전부 상대 경로로 연결됩니다. 별도 API, 외부 라이브러리, 웹 폰트, 모델 실행, 빌드 단계가 없습니다. 원본 연구 저장소가 없어도 재생 및 정적 호스팅이 가능합니다.

옮긴 폴더 안에서 다음을 실행합니다.

```sh
python3 serve.py
```

그다음 <http://127.0.0.1:8765>를 엽니다. 포트가 사용 중이면 `python3 serve.py --port 8766`으로 실행합니다. 브라우저에서 듣는 동안 서버를 켜둡니다. `index.html`을 일반 브라우저에서 직접 여는 것도 가능하지만, HTTP 미리보기를 권장합니다.

GitHub Pages 등 정적 호스팅에는 이 폴더 내용을 사이트 루트에 그대로 올리면 됩니다. `.nojekyll`도 포함되어 있습니다. 아직 외부 저장소 생성이나 게시 작업은 하지 않았습니다.

폴더 자체가 완전한지 확인하려면 옮긴 위치에서 다음을 실행합니다. **Python 기본 기능만 사용하며, 원본 연구 파일에 접근하지 않습니다.**

```sh
python3 verify_portable.py
```

## 포함된 자료

큰 소개 영역과 강조 숫자를 없앤 간결한 논문 데모입니다. 제목과 짧은 설명 다음에 비교 음원이 바로 나오며, 전체 수치와 representation 그림은 상단의 접힌 영역에서 펼쳐볼 수 있습니다. 한 페이지에 5개 사례(20개 플레이어)를 표시하며, Previous / Next로 전체 25개 사례를 볼 수 있습니다. 현재 페이지의 모든 음원 재생 정보를 즉시 불러옵니다. 각 트랙의 WAV 링크로 음원 파일을 직접 열 수도 있습니다. 재생 위치 유지는 기본적으로 꺼져 있으며, 켜면 현재 재생 중인 트랙에서 전환할 때만 적용합니다.

- 6개 테스트 공간의 **RIR 25개 전체**를 포함한 25개 사례. **서로 다른 발화 25개**를 사용합니다. 이전 버전과 RIR 및 화자 배정은 같고 발화만 중복 없이 다시 배치했습니다. 화자별 사례 수는 174: 9개, 2086: 8개, 2412: 8개입니다.
- 사례마다 실제 고정 acoustic caption, dry / Raw CLAP / ReverbAlign-512-v1 / measured-RIR reference 4종 음원. 총 100개 WAV.
- 단일 트랙 재생, 같은 사례의 재생 위치를 유지하는 비교 기능, 공간 필터.
- 사례별 RIR 측정값 및 caption 구간 일치 수, 전체 750쌍의 MAE 및 구간 일치율.
- 최신 Raw vs ReverbAlign representation SVG. Centroid 표시 없음.
- 출처와 SHA-256 해시, 내보내기 정책을 담은 `data/manifest.json` 및 전체 750쌍의 두 모델 final 측정 CSV.

## 최신 결과와 사용 가능한 음원 확인

`paper/main.tex`의 수치는 `experiments/07_fdn_text_optimization/results/gpu_three_model_physical_comparison/`의 `final` 결과와 일치합니다. 주 비교는 **Raw CLAP vs ReverbAlign-512-v1**입니다. Legacy-Best, 이전 780쌍 결과, best-loss 시점, 자유 자연어 실험, DRR 4단계 실험은 사용하지 않았습니다.

평가는 25 RIR × 30발화 = 750쌍, 6개 공간, 화자 3명입니다. 약 16초 Hamilton RIR을 제외합니다. 기본 caption은 4 RT60 × 4 C50 × 2 DRR × 3 EDT = 96개 조합입니다.

현재 `[gpu]raw-clap` 및 `[gpu]reverbalign-512-v1`에는 모델별 750쌍의 final/initial/best FDN checkpoint와 history가 있고, 기존 WAV는 없습니다. 기존 `test_full_*` 등의 WAV는 이전 실험 것이므로 최신 모델 결과로 대체 표시하지 않았습니다. 사용 가능 현황은 `data/availability.json`에 있습니다.

최신 모델의 **final 300-update FDN checkpoint**를 기존 `evaluate_gpu_checkpoints.py`의 렌더러로 복원해 음원을 만들었습니다. 추가 최적화, CLAP 추론, 재학습은 하지 않았습니다. 각 RIR의 네 측정값이 저장된 per-pair 결과와 일치하는지 확인한 뒤, 원래 처리된 dry speech와 동일한 FFT convolution을 적용했습니다. Reference는 `convolution_200.h5`의 정확히 대응하는 저장 음원입니다.

음원은 mono 16 kHz PCM16입니다. 생성 RIR L2 정규화, convolution 후 최대 10초 정책을 유지합니다. 각 사례의 4트랙 모두에 **같은 gain**을 적용해 최대 peak가 0.95가 되도록 했습니다. 개별 음원 loudness 정규화는 하지 않아 상대 음량은 유지됩니다. 사례 간 gain은 다를 수 있습니다. 원래 dry 입력은 −18 LUFS로 준비되었습니다. 10초 제한 때문에 일부 사례의 말미 잔향이 잘릴 수 있습니다.

## 사례 선택 기준

25개 테스트 RIR을 한 번씩 포함하고, **사례마다 서로 다른 테스트 발화**를 사용합니다. 모델 출력이나 청취 판단은 선택에 사용하지 않습니다.

1. RIR을 공간 ID, RIR ID 사전순으로 정렬합니다. 같은 공간명이 반복되는 것은 서로 다른 RIR이기 때문입니다.
2. 기존 화자 배정을 유지합니다. 각 공간의 reference RT60 중앙값에 가장 가까운 RIR 여섯 개에는 공간 ID 순으로 174, 2086, 2412를 순환 배치합니다. 나머지는 현재 배정 수가 가장 적은 화자에게 배정하고, 동률이면 숫자 ID가 작은 화자를 고릅니다. 최종 분포는 9 / 8 / 8개입니다.
3. 각 화자의 테스트 발화 10개를 ID 사전순으로 정렬합니다. 표시 순서대로 해당 화자의 **다음 미사용 발화**를 첫 번째부터 배치합니다. 따라서 25개 발화가 모두 다릅니다. 174는 첫 9개, 2086과 2412는 각각 첫 8개를 사용합니다.
4. 각 사례의 Dry, Raw CLAP, ReverbAlign, Reference는 동일 발화와 동일 caption/RIR 목표에 대응합니다. Raw와 ReverbAlign의 실제 해당 pair final checkpoint를 사용하며, 다른 발화에 최적화한 결과를 재사용하지 않습니다.

테스트 RIR 25개 전체와 테스트 발화 30개 중 25개를 포함합니다. 무작위 표본은 아니며 전체 성능은 **750쌍 전체**의 집계로 제시합니다. ReverbAlign의 구간 일치 수가 더 낮은 사례도 그대로 포함합니다. 실제 사례 ID, 발화 ID, source row, checkpoint 해시는 manifest에 기록합니다. Provenance의 연구 저장소 상대 경로는 출처 식별자이며, 페이지를 실행할 때 해당 원본 파일을 열지 않습니다.

## 연구 원본으로부터 재생성 및 대조 검증

이미 생성된 정적 페이지를 보는 데 Python이나 원본 데이터가 필요하지 않습니다. 원본 저장소와 기존 환경에서 자료를 다시 내보낼 때만 다음을 실행합니다.

```sh
.venv/bin/python demo/build_assets.py
.venv/bin/python demo/verify_assets.py
node --check demo/app.js
```

`build_assets.py`는 demo 폴더에만 씁니다. 기존 renderer는 import하여 복원 함수만 호출하며 그 모듈의 `main()`은 실행하지 않습니다. 모델 등록 checkpoint의 해시, 공통 pair metadata와 초기 FDN state, final update=300, 복원한 RIR의 수치 일치를 확인합니다. `verify_assets.py`는 WAV 형식·해시·peak, 원본 파일 보존, 750쌍 집계 및 reference/dry 내보내기 일치를 점검합니다.

파일 구성:

```text
demo/
  index.html, styles.css, app.js   정적 페이지
  assets/audio/                   재생용 WAV 100개
  assets/figures/representation.svg
  data/                           수치, provenance, 사례 manifest
  build_assets.py                 저장된 결과의 offline export
  verify_assets.py                연구 원본과 대조 검증
  verify_portable.py              폴더 내부 자료만으로 검증 (기본 Python)
  serve.py                       옮긴 위치에서 로컬 미리보기
  README.md
```
