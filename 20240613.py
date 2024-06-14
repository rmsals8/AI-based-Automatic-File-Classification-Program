import os
import time
import shutil
import torch
import fitz
import olefile
import re
import threading
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from transformers import BertTokenizer, BertForSequenceClassification
import sys
from PyQt5.QtWidgets import QApplication, QWidget, QLabel, QPushButton, QLineEdit, QToolButton, QHBoxLayout, QSizePolicy, QFileDialog, QMessageBox
from PyQt5.QtGui import QPixmap, QIcon, QMouseEvent
from PyQt5.QtCore import QSize, Qt, QPoint
from PIL import Image
import pystray
from pystray import MenuItem as item
import sys
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *

class SystemTrayIcon(QSystemTrayIcon):

    def __init__(self, icon, parent=None):
        QSystemTrayIcon.__init__(self, icon, parent)
        menu = QMenu(parent)
        exitAction = menu.addAction("Exit")
        exitAction.triggered.connect(QCoreApplication.instance().quit)
        self.setContextMenu(menu)
        self.activated.connect(self.Activation_Reason)

    def Activation_Reason(self, index):
        if index == 2 :
            print ("Double Click")




# def on_quit(icon, item):
#     icon.stop()
#     sys.exit()

# icon_image = Image.open("Group 34869.png")

# icon = pystray.Icon("name")
# icon.icon = icon_image
# icon.menu = pystray.Menu(item('Quit', on_quit))
# icon.run()

class DownloadEventHandler(FileSystemEventHandler):
    last_modified = {}

    def on_created(self, event):
        self.on_modified(event)

    def on_modified(self, event):
        if not event.is_directory:
            file_path = event.src_path
            current_time = time.time()
            if (file_path not in self.last_modified) or (current_time - self.last_modified[file_path] > 1):
                self.last_modified[file_path] = current_time
                file_extension = os.path.splitext(file_path)[1]
                if file_extension.lower() in ['.pdf', '.hwp']:
                    print(f"파일이 수정되었습니다: {file_path}")
                    self.process_modified(file_path)

    def process_modified(self, file_path):
        normalized_path = os.path.normpath(file_path)
        key1 = classify_files_in_folders([normalized_path])
        print(f"key1은 ={key1}")
        src_path = file_path
        print(f"src_path={src_path}")
        key = [(os.path.basename(src_path), key1)]
        print(f"key={key}")
        category_paths = pathh
        print(f"프로세스 모디파이드 : pathh는 ={pathh}")
        if key:
            for filename, label in key:
                print(f"filename={filename}, label={label}")
                if label in category_paths:
                    print(f"category_paths[label]={category_paths[label]}")
                    dst_path = os.path.join(category_paths[label], filename)
                    print(f"파일을 이동할 경로: {dst_path}")
                    try:
                        shutil.move(src_path, dst_path)
                        print(f"파일을 이동했습니다: {dst_path}")
                        break
                    except Exception as e:
                        print(f"파일 이동 중 오류가 발생했습니다: {e}")

def classify_files_in_folders(paths):
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model = BertForSequenceClassification.from_pretrained('bert-base-uncased', num_labels=5)
    model.load_state_dict(torch.load('0529_model.pth', map_location=device))
    model.to(device)
    tokenizer = BertTokenizer.from_pretrained('bert-base-uncased')

    def clean_text_for_excel(text):
        cleaned_text = re.sub(r'[\000-\010]|[\013-\014]|[\016-\037]', '', text)
        cleaned_text = ''.join(c for c in cleaned_text if c.isprintable())
        return cleaned_text

    def classify_file(file_content, file_name):
        model.eval()
        text = file_content or file_name
        inputs = tokenizer.encode_plus(
            text, None, add_special_tokens=True, max_length=128,
            padding='max_length', truncation=True, return_token_type_ids=False
        )
        input_ids = torch.tensor(inputs['input_ids'], dtype=torch.long).unsqueeze(0).to(device)
        attention_mask = torch.tensor(inputs['attention_mask'], dtype=torch.long).unsqueeze(0).to(device)
        with torch.no_grad():
            outputs = model(input_ids=input_ids, attention_mask=attention_mask)
            _, preds = torch.max(outputs[0], dim=1)
        return preds.item()

    def get_label_name(label):
        label_dict = {
            0: '리포트파일',
            1: '강의파일',
            2: '취업파일',
            3: '신청서파일',
            4: '개발파일'
        }
        return label_dict.get(label, 'Unknown')

    results = []

    for path in paths:
        if os.path.isfile(path):
            folder_path, filename = os.path.split(path)
            file_content = ""
            if filename.endswith(".hwp"):
                try:
                    f = olefile.OleFileIO(path)
                    encoded_txt = f.openstream("PrvText").read()
                    file_content = encoded_txt.decode("utf-16", errors="ignore")
                    cleaned_text = clean_text_for_excel(file_content)
                    file_label = classify_file(cleaned_text, filename)
                    label_name = get_label_name(file_label)
                    results.append((filename, label_name))
                except Exception as e:
                    results.append((filename, f"Error: {e}"))
            elif filename.endswith(".pdf"):
                try:
                    doc = fitz.open(path)
                    for page in doc:
                        file_content += page.get_text()
                    doc.close()
                    cleaned_text = clean_text_for_excel(file_content)
                    file_label = classify_file(cleaned_text, filename)
                    label_name = get_label_name(file_label)
                    results.append((filename, label_name))
                except Exception as e:
                    results.append((filename, f"Error: {e}"))
    return results[0][1] if results else 'Unknown'

def start_monitoring():
    observer = Observer()
    event_handler = DownloadEventHandler()
    download_folder = download_path_mac()
    observer.schedule(event_handler, download_folder, recursive=False)
    observer.start()
    print(f"모니터링 중: {download_folder}")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()

def start_monitoring_in_thread():
    monitoring_thread = threading.Thread(target=start_monitoring)
    monitoring_thread.daemon = True
    monitoring_thread.start()

def stop_monitoring(observer):
    observer.stop()
    observer.join()
    print("모니터링을 중지했습니다.")

def download_path_mac():
    home = os.path.expanduser("~")
    download_path = os.path.join(home, 'Downloads')
    return download_path

def save_category_paths():
    paths = {}
    for i in range(1, 6):
        entry_path_key = f'download_edit{i}'
        if entry_path_key in globals():
            path = globals()[entry_path_key].text()
            paths[entry_path_key] = path
    return paths

class MyApp(QWidget):
    def __init__(self):
        super().__init__()
        self.initUI()
        self.isDragging = False 
        self.isMaximized = False  

    #def handle_start_button_click(self):
     #   self.save_category_paths()
      #  start_monitoring()
    def handle_start_button_click(self):
        global pathh
        pathh = self.save_category_paths()
        if pathh:  # pathh가 유효한 경우에만 모니터링 시작
            print(f"핸들 모니터링에서 pathh는 ={pathh}")
            print("채워지지 않는 칸 또있어")        
            start_monitoring_in_thread()
        # start_monitoring()    

    def save_category_paths(self):
        self.category_paths = {
            "리포트파일": self.download_edit1.text(),
            "강의파일": self.download_edit2.text(),
            "취업파일": self.download_edit3.text(),
            "신청서": self.download_edit4.text(),
            "개발": self.download_edit5.text()
        }
        # print(f"카테고리 경로가 저장되었습니다: {self.category_paths}")

        for key, path in self.category_paths.items():
            if not path:
                QMessageBox.warning(self, "경고", "채워지지 않은 칸이 있습니다.")
                return

            print(f"카테고리 경로가 저장되었습니다: {self.category_paths}")
        return self.category_paths

    def initUI(self):

       
        # 윈도우의 제목 설정
        self.setWindowTitle('폴더관리기본UI')
        self.setWindowIcon(QIcon('Group 34869.png'))
        # 윈도우의 위치와 크기 설정 (x, y, width, height)
        self.setWindowFlags(Qt.FramelessWindowHint)
        self.setGeometry(10, 50, 1920, 888)
        # 윈도우의 최대 크기 설정 (width, height)
        self.setMaximumSize(1920, 888)
        

        # 타이틀 바 생성
        self.createTitleBar()

        # 배경 이미지 설정
        self.background_label = QLabel(self)  # 배경 이미지를 담을 QLabel 생성
        self.background_pixmap = QPixmap('폴더 관리 기본 UI.png')  # 배경 이미지 로드
        self.background_label.setPixmap(self.background_pixmap)  # QLabel에 pixmap 설정
        # QLabel의 위치와 크기 설정 (x, y, width, height)
        self.background_label.setGeometry(0, 0, 2000, 900)
        # QLabel의 내용이 창 크기에 맞게 조정되도록 설정
        self.background_label.setScaledContents(True)

        # 하단 이미지 설정
        self.bottom_image_label = QLabel(self)  # 하단 이미지를 담을 QLabel 생성
        self.bottom_pixmap = QPixmap('Group34868.png')  # 하단 이미지 로드
        self.bottom_image_label.setPixmap(self.bottom_pixmap)  # QLabel에 pixmap 설정
        bottom_image_height = self.bottom_pixmap.height()  # 하단 이미지의 높이 가져오기
        # QLabel의 위치와 크기 설정 (x, y, width, height)
        self.bottom_image_label.setGeometry(0, 888 - bottom_image_height, 1920, bottom_image_height)
        # QLabel의 내용이 창 크기에 맞게 조정되도록 설정
        self.bottom_image_label.setScaledContents(True)

        # 중앙 이미지 설정
        self.center_image_label = QLabel(self)  # 중앙 이미지를 담을 QLabel 생성
        self.center_pixmap = QPixmap('Rectangle3.png')  # 중앙 이미지 로드
        self.center_image_label.setPixmap(self.center_pixmap)  # QLabel에 pixmap 설정
        self.center_image_label.setScaledContents(True)  # QLabel의 내용이 창 크기에 맞게 조정되도록 설정
        self.update_center_image()  # 중앙 이미지의 위치 업데이트

        # 카테고리 라벨 및 경로 입력 필드 추가
        # self.add_category('리포트.png', 350, 280, 450, 274, 1310, 240, 1430, 240)
        # self.add_category('강의파일.png', 350, 356, 450, 350, 1310, 316, 1430, 316)
        # self.add_category('취업파일.png', 350, 433, 450, 427, 1310, 393, 1430, 393)
        # self.add_category('신청서.png', 350, 508, 450, 502, 1310, 468, 1430, 468)
        # self.add_category('개발.png', 350, 580, 450, 575, 1310, 540, 1430, 540)
        # add_category(self, image, label_x, label_y, edit_x, edit_y, find_x, find_y, quit_x, quit_y)
        category_label1 = QLabel('', self)
        category_label1.move(350, 280)
        label_pixmap1 = QPixmap('리포트.png')
        category_label1.setPixmap(label_pixmap1)
        category_label1.setScaledContents(True)

        self.download_edit1 = QLineEdit(self)  # 다운로드 경로 입력을 위한 QLineEdit 생성
        self.download_edit1.setGeometry(450, 274, 870, 30)  # 입력 필드의 위치와 크기 설정 (x, y, width, height)

        self.add_button('폴더찾기.png', 1310, 240, 200, 100, lambda: self.browse_folder(self.download_edit1))
        self.add_button('종료3.png', 1430, 240, 200, 100, self.delete_folder)

       
        category_label2 = QLabel('', self)
        category_label2.move(350, 356)
        label_pixmap2 = QPixmap('강의파일.png')
        category_label2.setPixmap(label_pixmap2)
        category_label2.setScaledContents(True)

        self.download_edit2 = QLineEdit(self)  # 다운로드 경로 입력을 위한 QLineEdit 생성
        self.download_edit2.setGeometry(450, 350, 870, 30)  # 입력 필드의 위치와 크기 설정 (x, y, width, height)

        self.add_button('폴더찾기.png', 1310, 316, 200, 100, lambda: self.browse_folder(self.download_edit2))
        self.add_button('종료3.png', 1430, 316, 200, 100, self.delete_folder)

        # Employment file 카테고리
        category_label3 = QLabel('', self)
        category_label3.move(350, 433)
        label_pixmap3 = QPixmap('취업파일.png')
        category_label3.setPixmap(label_pixmap3)
        category_label3.setScaledContents(True)

        self.download_edit3 = QLineEdit(self)  # 다운로드 경로 입력을 위한 QLineEdit 생성
        self.download_edit3.setGeometry(450, 427, 870, 30)  # 입력 필드의 위치와 크기 설정 (x, y, width, height)

        self.add_button('폴더찾기.png', 1310, 393, 200, 100, lambda: self.browse_folder(self.download_edit3))
        self.add_button('종료3.png', 1430, 393, 200, 100, self.delete_folder)

        # Application 카테고리
        category_label4 = QLabel('', self)
        category_label4.move(350, 508)
        label_pixmap4 = QPixmap('신청서.png')
        category_label4.setPixmap(label_pixmap4)
        category_label4.setScaledContents(True)

        self.download_edit4 = QLineEdit(self)  
        self.download_edit4.setGeometry(450, 502, 870, 30)  
        self.add_button('폴더찾기.png', 1310, 468, 200, 100, lambda: self.browse_folder(self.download_edit4))
        self.add_button('종료3.png', 1430, 468, 200, 100, self.delete_folder)

        # Development 카테고리
        category_label5 = QLabel('', self)
        category_label5.move(350, 580)
        label_pixmap5 = QPixmap('개발.png')
        category_label5.setPixmap(label_pixmap5)
        category_label5.setScaledContents(True)

        self.download_edit5 = QLineEdit(self)  
        self.download_edit5.setGeometry(450, 575, 870, 30)  

        self.add_button('폴더찾기.png', 1310, 540, 200, 100, lambda: self.browse_folder(self.download_edit5))
        self.add_button('종료3.png', 1430, 540, 200, 100, self.delete_folder)

        ##########################################################################################################3

        # 다운로드 폴더 경로 라벨 및 입력 필드
        download_label = QLabel('', self)  # 다운로드 경로를 위한 QLabel 생성
        label_pixmap_down = QPixmap("다운로드폴더경로1.png")
        download_label.setPixmap(label_pixmap_down)
        download_label.setScaledContents(True)
        download_label.setStyleSheet("color: white;")  # 라벨의 텍스트 색상 설정
        download_label.move(250, 90)  # 라벨의 위치 설정 (x, y)
        
        # 카테고리 폴더 경로 라벨 및 입력 필드
        category_label = QLabel('카테고리폴더경로', self)  # 카테고리 경로를 위한 QLabel 생성
        label_pixmap_cate = QPixmap("카테고리폴더경로1.png")
        category_label.setPixmap(label_pixmap_cate)
        category_label.setScaledContents(True)
        category_label.setStyleSheet("color: white;")  # 라벨의 텍스트 색상 설정
        category_label.move(850, 200)  # 라벨의 위치 설정 (x, y)
        self.category_edit = QLineEdit(self)  # 카테고리 경로 입력을 위한 QLineEdit 생성
        self.category_edit.setGeometry(450, 85, 870, 30)  # 입력 필드의 위치와 크기 설정 (x, y, width, height)

        # 폴더 찾기 버튼
        self.add_button('폴더찾기.png', 1330, 50, 200, 100,self.browse_download_folder)
        self.add_button('추가1.png', 1450, 50, 200, 100,self.save_category_path)
        self.add_button('삭제1.png', 1530, 50, 200, 100, self.delete_folder)

        # 시작 버튼
        start_button = QPushButton('', self)  # 시작 버튼을 위한 QPushButton 생성
        start_icon = QIcon('시작.png')  # 시작 아이콘 이미지 로드
        start_button.setIcon(start_icon)  # 버튼에 아이콘 설정
        start_button.setIconSize(QSize(200, 100))  # 아이콘 크기 설정
        start_button.setGeometry(1400, 800, 200, 100)  # 버튼의 위치와 크기 설정 (x, y, width, height)
        # 버튼 클릭 시 start_monitoring 메소드를 호출하도록 연결
        start_button.clicked.connect(self.handle_start_button_click)
        # 배경을 투명하게 하고 테두리를 제거
        start_button.setStyleSheet("background: transparent; border: none;")

        # 종료 버튼
        quit_button = QPushButton('', self)  # 종료 버튼을 위한 QPushButton 생성
        quit_icon = QIcon('종료.png')  # 종료 아이콘 이미지 로드
        quit_button.setIcon(quit_icon)  # 버튼에 아이콘 설정
        quit_button.setIconSize(QSize(200, 100))  # 아이콘 크기 설정
        quit_button.setGeometry(1600, 800, 200, 100)  # 버튼의 위치와 크기 설정 (x, y, width, height)
        quit_button.clicked.connect(self.close)
        # 배경을 투명하게 하고 테두리를 제거
        quit_button.setStyleSheet("background: transparent; border: none;")

        # 배경 라벨을 뒤로 이동
        self.background_label.lower()

        self.show()  # 윈도우를 화면에 표시
    

    def browse_folder(self, download_edit):
        folder_path = QFileDialog.getExistingDirectory(self, "폴더 선택")
        if folder_path:
            download_edit.setText(folder_path)
  

    def delete_folder(self):
        folder_path = self.category_edit.text()
        print(folder_path)
        self.category_edit.clear()

    
    def save_category_path(self):
        path = self.category_edit.text()
        print(f"path={path}")
        return path
    def browse_download_folder(self):
            folder_path = QFileDialog.getExistingDirectory(self, '폴더 선택', os.path.expanduser('~'))
            if folder_path:
                self.category_edit.setText(folder_path)  # 선택한 경로를 QLineEdit에 설정


    def add_category(self, image, label_x, label_y, edit_x, edit_y, find_x, find_y, quit_x, quit_y):
        category_label = QLabel('', self)
        category_label.move(label_x, label_y)
        label_pixmap = QPixmap(image)
        category_label.setPixmap(label_pixmap)
        category_label.setScaledContents(True)
        self.download_edit = QLineEdit(self)  # 다운로드 경로 입력을 위한 QLineEdit 생성
        self.download_edit.setGeometry(edit_x, edit_y, 870, 30)  # 입력 필드의 위치와 크기 설정 (x, y, width, height)
        self.add_button('폴더찾기.png', find_x, find_y, 200, 100,lambda: self.browse_folder(self.download_edit))
        self.add_button('종료3.png', quit_x, quit_y, 200, 100, self.delete_folder)

    def add_button(self, icon_path, x, y, width, height, callback=None):
        button = QPushButton('', self)  # QPushButton 생성
        button_icon = QIcon(icon_path)  # 아이콘 이미지 로드
        button.setIcon(button_icon)  # 버튼에 아이콘 설정
        button.setIconSize(QSize(width, height))  # 아이콘 크기 설정
        button.setGeometry(x, y, width, height)  # 버튼의 위치와 크기 설정 (x, y, width, height)
        button.setStyleSheet("background: transparent; border: none;")  # 배경을 투명하게 하고 테두리를 제거
        if callback:
            button.clicked.connect(callback)

    def resizeEvent(self, event):
        super().resizeEvent(event)  # 부모 클래스의 resizeEvent 호출
        self.update_center_image()  # 중앙 이미지의 위치 업데이트

    def update_center_image(self):
        window_width = self.width()  # 현재 윈도우의 너비 가져오기
        window_height = self.height()  # 현재 윈도우의 높이 가져오기
        image_width = self.center_pixmap.width()  # 중앙 이미지의 너비 가져오기
        image_height = self.center_pixmap.height()  # 중앙 이미지의 높이 가져오기
        self.center_image_label.setGeometry(
            (window_width - image_width) // 2,  # 이미지를 수평으로 가운데 정렬
            (window_height - image_height) // 2,  # 이미지를 수직으로 가운데 정렬
            image_width,  # 이미지 너비 설정
            image_height  # 이미지 높이 설정
        )

    def createTitleBar(self):
        # 타이틀 바 위젯 생성
        self.title_bar = QWidget(self)
        self.title_bar.setGeometry(0, 0, self.width(), 50)
        self.title_bar.setStyleSheet("background-color: #05203C;")  # 타이틀 바 배경색 설정

        # 타이틀 바 레이아웃 생성
        title_bar_layout = QHBoxLayout()
        self.title_bar.setLayout(title_bar_layout)

        # 타이틀 바 아이콘 추가
        icon_button = QToolButton(self)
        icon = QIcon("Vector3.png")
        icon_button.setIcon(icon)
        icon_button.setIconSize(QSize(40, 40))
        title_bar_layout.addWidget(icon_button)

        # 타이틀 이미지 추가
        title_pixmap = QPixmap("폴더관리.png")
        title_label = QLabel(self)
        title_label.setPixmap(title_pixmap)
        title_bar_layout.addWidget(title_label)

        # 최소화, 최대화, 닫기 버튼 추가
        minimize_button = QToolButton(self)
        minimize_icon = QIcon("Vector2.png")
        minimize_button.setIcon(minimize_icon)
        minimize_button.setIconSize(QSize(30, 30))
        minimize_button.clicked.connect(self.showMinimized)
        title_bar_layout.addWidget(minimize_button)

        maximize_button = QToolButton(self)
        maximize_icon = QIcon("Rectangle5.png")
        maximize_button.setIcon(maximize_icon)
        maximize_button.setIconSize(QSize(30, 30))
        #  maximize_button.clicked.connect(self.toggleMaximizeRestore)/
        title_bar_layout.addWidget(maximize_button)

        close_button = QToolButton(self)
        close_icon = QIcon("Vector1.png")
        close_button.setIcon(close_icon)
        close_button.setIconSize(QSize(30, 30))
        close_button.clicked.connect(self.close)
        title_bar_layout.addWidget(close_button)

        
        self.title_bar.mousePressEvent = self.title_bar_mousePressEvent
        self.title_bar.mouseMoveEvent = self.title_bar_mouseMoveEvent
        self.title_bar.mouseReleaseEvent = self.title_bar_mouseReleaseEvent

    def toggleMaximizeRestore(self):
        if self.isMaximized:
            self.showNormal()
        else:
            self.showMaximized()
        self.isMaximized = not self.isMaximized

    def title_bar_mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.isDragging = True
            self.dragPosition = event.globalPos() - self.frameGeometry().topLeft()
            event.accept()

    def title_bar_mouseMoveEvent(self, event):
        if self.isDragging and event.buttons() == Qt.LeftButton:
            self.move(event.globalPos() - self.dragPosition)
            event.accept()

    def title_bar_mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.isDragging = False
            event.accept()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    ex = MyApp()
    app.setWindowIcon(QIcon('Group34869.png'))
    w = QWidget()
    trayIcon = SystemTrayIcon(QIcon('Group34869.png'), w)
    trayIcon.show()
    trayIcon.showMessage("제목", "내용", 1, 10000)
    sys.exit(app.exec_())
