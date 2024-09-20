### 1. 모델 파일 준비
quantized_model.pth 을 다음 링크해서 다운로드 받기 <br>
https://drive.google.com/file/d/1FvBUkKSjkOtcZb4oIa9lcyqaRw8W4nQ6/view?usp=drive_link

### 2. 가상환경 생성 및 활성화
프로젝트 디렉토리에서 다음 명령어를 실행하여 가상환경을 생성하고 활성화합니다<br>
python -m venv venv <br>
source venv/bin/activate  # macOS 및 Linux <br>
venv\Scripts\activate  # Windows <br>

### 3. 필요한 패키지 설치
다음 명령어를 사용하여 필요한 패키지들을 설치합니다 <br>
pip install PyQt5 <br>
pip install watchdog <br>
pip install torch <br>
pip install transformers <br>
pip install PyMuPDF <br>
pip install olefile <br>

### 4. 실행 방법
가상환경이 활성화된 상태에서 다음 명령어로 애플리케이션을 실행합니다 <br>
python main.py
