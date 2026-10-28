# 구현 후 기술 점검
작성: 2026-10-28

## 결과 요약
Android 앱 소스, 데이터 변환, 학습/ONNX 내보내기 도구를 작성했습니다. 로컬 수정 데이터셋 변환 및 Python 테스트 4개가 통과했습니다. 학습 완료 모델과 실제 태블릿 동작은 아직 확인되지 않았습니다. GitHub CI에서 Android 단위 테스트·lint·APK 빌드가 통과했습니다.

## 기술 스택
| 영역 | 선택 |
|---|---|
| 앱 | Kotlin 2.0.21, Android API 26+, compile/target 35 |
| 빌드 | AGP 8.7.3, Gradle 8.9, JDK 17 |
| 카메라 | CameraX 1.4.1, RGBA, 최신 프레임 우선 |
| 추론 | ONNX Runtime Android 1.20.0, CPU 2 스레드 |
| 모델 | YOLOv8n, FP32, 640×640, RGB CHW /255 |
| 후처리 | 클래스별 NMS IoU 0.45, 최대 50개, 신뢰도 0.35 기본값 |
| 학습 환경 정의 | Ultralytics 8.3.40, ONNX 1.17.0, ORT Python 1.20.1 |
| 테스트 | Python unittest, JUnit 4.13.2, Android lint |

## 디렉터리 구조와 책임
- android/app/src/main/java/com/mobility/inspect/
  - MainActivity.kt: 권한, 라이프사이클, 분석 큐, 임계값/일시정지/모델 선택.
  - CameraFrame.kt: RGBA row/pixel stride 해석 및 회전.
  - Detector.kt: manifest/해시/텐서 검증, 전처리, 추론, 좌표 복원.
  - Geometry.kt: letterbox 복원, IoU, 클래스별 NMS.
  - InspectionView.kt: 동일 분석 프레임과 박스 표시, 터치 선택.
  - Parts.kt: 10종 한국어 이름과 점검 참고 정보.
  - ModelPackage.kt: ZIP 허용 파일/용량 제한, 검증 후 활성화.
- tools/prepare_dataset.py: annotations.json 검증 및 YOLO 분할.
- tools/train_export.py: 학습, ONNX 구조/출력 검증, 모델 패키징.
- tests/, android/app/src/test/: 데이터·좌표·NMS 테스트.
- .github/workflows/android.yml: Python 및 Android 검증, APK artifact.
- docs/: 사전 구성안, 본 점검서, 실제 데이터 통계.

## 데이터 검증
로컬 데이터 검증 결과는 로컬 점검 문서에 보관합니다. 원본 데이터/파일 해시/개별 이미지 목록은 업로드하지 않습니다.

## 점검 결과
- Python 테스트 4개 통과: 좌표 정규화, 재현 가능한 분할/분할 간 누출 방지, 잘못된 박스, 동일 이미지 중복, 기존 출력 경로 거부.
- Python 소스 컴파일 검사 통과.
- 모델 부재 시 카메라만 표시하고 가짜 탐지를 생성하지 않음.
- 모델 로딩: SHA-256, 클래스 ID 순서, 입력 [1,3,640,640], 출력 [1,14,8400] 검사.
- 분석 프레임과 박스를 함께 렌더링하여 비율/회전 좌표와 표시 시점을 일치시킴.
- 프레임은 finally에서 닫고 ORT tensor/result/session을 해제하도록 구현.
- ZIP 경로 탐색/중복 파일/과도한 압축 해제 제한. 새 모델 실패 시 기존 패키지 유지.
- 카메라/추론 서버 전송 없음. INTERNET 권한 없음.
- UI 속도 표시값은 완료 프레임 간 FPS이며 실측 성능 보장 수치가 아님.

## 실행 환경과 미완료 항목
로컬에는 PyTorch 2.14.0+cpu와 Ultralytics 8.4.166이 설치되어 있어 requirements의 재현 환경과 다릅니다. CUDA 없음. 확인한 로컬 데이터 위치에 학습 가중치가 없고 외부 DNS가 차단되어 사전학습 가중치 다운로드/원격 의존성 설치가 불가능했습니다.
JDK/Gradle/Android SDK가 확인되지 않아 로컬 APK 빌드와 Kotlin 테스트는 실행하지 못했습니다. CI 결과는 별도로 기록합니다.
학습/ONNX export는 미실행이며 실제 탐지 가능 모델이 포함되지 않습니다.

## 태블릿 인수 시험 (미실행)
- 모델 ZIP 가져오기 성공/실패, 다른 클래스 모델 거부, 앱 재시작 후 모델 복원.
- 카메라 권한 거절/재허용, 후면 카메라 없는 장치 오류.
- 가로/세로, 화면 재생성, 백그라운드 복귀, 일시정지/재개.
- 실제 차량에서 박스/선택 위치, 한국어 표시, 색상과 회전 확인.
- 10분 연속 실행 후 FPS/처리 지연/메모리/발열 측정.
- 추가 차량으로 클래스별 precision/recall/mAP 평가. 학습 예시 0개인 3종 보완.

## 최종 CI 확인
- 검증 코드 커밋: fd49f084423382603e70fa3458acdd6e6a52d502
- [GitHub Actions 실행 #3](https://github.com/Origin1332/Mobility-Inspecter/actions/runs/40667510881): success
- Python 데이터 테스트, Android testDebugUnitTest, lintDebug, assembleDebug 통과.
- [디버그 APK ZIP](https://github.com/Origin1332/Mobility-Inspecter/actions/runs/40667510881/artifacts/12806856866) 생성 확인.
- 로컬 SDK 부재는 CI 빌드로 보완했습니다. 실기기 카메라/성능 시험과 실제 학습 모델 준비는 미완료입니다.
- 첫 CI의 오래된 SDK tools 패키지 설치 실패는 필요한 SDK 플랫폼/빌드 도구 명시로 해결했습니다.
