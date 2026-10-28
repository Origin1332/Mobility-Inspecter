# Mobility Inspecter
Android 태블릿의 후면 카메라로 차량 전면부 부품의 바운딩 박스·부품명·신뢰도·점검 참고 정보를 표시하는 오프라인 앱입니다.

## 현재 상태
[검증 완료 디버그 APK 다운로드](https://github.com/Origin1332/Mobility-Inspecter/actions/runs/40667510881/artifacts/12806856866) · [빌드/테스트 결과](https://github.com/Origin1332/Mobility-Inspecter/actions/runs/40667510881)

앱 소스와 데이터 변환/학습/ONNX 패키징 도구를 구현했습니다. 학습 모델은 포함되지 않습니다. 먼저 아래 절차로 사용자 로컬 데이터셋을 학습하고 앱에 모델 ZIP을 가져와야 실제 탐지가 가능합니다. 학습 완료·현장 정확도·실기기 성능은 아직 검증되지 않았습니다.

## 데이터와 학습 (PC)
Python 3.11/3.12 가상환경을 권장합니다. 저장소 루트에서 실행합니다.
```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r tools/requirements.txt
python tools/prepare_dataset.py --source "C:/datasets/dataset_front_reviewed.zip" --output data/front-reviewed
python tools/train_export.py --data data/front-reviewed/data.yaml --weights yolov8n.pt --epochs 100 --device cpu
```
출력 폴더는 존재하지 않는 경로를 지정하세요. 전처리는 기존 라벨을 덮어쓰지 않습니다.
가중치가 로컬에 없으면 최초 다운로드에 인터넷이 필요합니다. CUDA PC에서는 --device 0을 사용합니다.
기존 학습 체크포인트 내보내기:
```powershell
python tools/train_export.py --data data/front-reviewed/data.yaml --checkpoint runs/front-parts/weights/best.pt
```
모델 패키지: models/front-parts.zip. 내부에 model.onnx와 manifest.json이 있어야 합니다.
데이터/가중치/영상은 Git에 포함하지 않습니다. 학습 데이터와 모델은 PC 및 태블릿에 로컬로 보관합니다.
원본 10개 클래스 순서는 변경하지 않습니다. 수평 뒤집기는 좌우 라벨 오류를 피하기 위해 꺼져 있습니다.

## Android 빌드
JDK 17, Android SDK 35, Gradle 8.9가 필요합니다. Gradle wrapper 바이너리는 포함하지 않았습니다.
```powershell
gradle -p android testDebugUnitTest lintDebug assembleDebug
```
APK: android/app/build/outputs/apk/debug/app-debug.apk.
Android Studio에서 android 폴더를 열고 Gradle 8.9를 선택해 빌드할 수도 있습니다.
GitHub PR의 Android verification 작업에서도 테스트·lint·APK 빌드를 수행하며 성공 시 APK를 artifact로 제공합니다.

## 태블릿 사용
1. Android 8 이상, arm64 태블릿에 APK를 설치하고 카메라 권한을 허용합니다.
2. PC에서 만든 front-parts.zip을 태블릿으로 복사합니다.
3. 앱의 모델 ZIP 버튼으로 파일을 선택합니다. 체크섬/클래스/입출력 형태 검증 후 활성화됩니다.
4. 후면 카메라를 차량 전면부로 향하게 하고 신뢰도 기준을 조정합니다.
5. 박스를 누르면 부품 설명과 원본 프레임 기준 픽셀 좌표를 확인합니다.
6. 일시정지/재개를 사용할 수 있습니다. 회전 시 화면이 재생성되어 모델을 다시 로드합니다.
모델이 없어도 카메라 영상은 표시하지만 탐지 결과를 만들지 않습니다. 카메라 영상과 추론 결과는 서버에 보내지 않으며 앱에는 INTERNET 권한이 없습니다.

## 데이터 한계
학습 데이터가 작거나 클래스별 예시가 없으면 해당 부품의 인식 성능을 확보할 수 없습니다. 좌우는 원본 라벨 정의를 유지합니다. 부품 탐지 결과는 고장·손상 판정이 아닙니다.

## 문서
- [구성안](docs/IMPLEMENTATION_PLAN.md)
- [최종 기술 점검](docs/FINAL_REVIEW.md)

## 공식 참고 문서
- [CameraX ImageAnalysis](https://developer.android.com/reference/androidx/camera/core/ImageAnalysis)
- [ONNX Runtime Java](https://onnxruntime.ai/docs/get-started/with-java.html)
- [YOLOv8](https://docs.ultralytics.com/models/yolov8/)
