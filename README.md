# ros2_ws

이 저장소는 로컬 ROS2 작업공간 `ros2_ws`의 내용을 GitHub 레포지토리로 옮기기 위한 초기화입니다.

## 구조
- `src/` : ROS2 패키지 소스
- `build/`, `install/`, `log/` : 빌드 출력 및 설치 결과
- `ocr_captures/`, `ocr_captures_tracking/` : OCR 관련 캡쳐와 트래킹 데이터
- `paddlepaddle_gpu-...whl` : 로컬에 보관된 패키지 파일

## 빠른 시작
로컬에서 Git 저장소를 초기화하고 커밋했습니다. 원격 GitHub 저장소에 푸시하려면 아래 예시 명령을 사용하세요.

1) GitHub에 새 리포지토리 만들기(웹 또는 `gh` 사용).
2) 예: 원격 추가 및 푸시

```bash
cd ros2_ws
git remote add origin <REMOTE_URL>
git branch -M main
git push -u origin main
```

또는 GitHub CLI 사용:

```bash
gh repo create <OWNER/REPO> --public --source=. --remote=origin --push
```

## 주의
- 큰 바이너리(.whl 등)는 필요시 Git LFS 사용을 고려하세요.
- 빌드/설치 디렉토리는 `.gitignore`에 포함되어 있습니다.
