import sys
import os
import time
import shutil
import torch
import fitz
import olefile
import re
import logging  # 수정: 로깅 모듈 추가
import threading
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from transformers import BertTokenizer, BertForSequenceClassification
from PyQt5.QtWidgets import (QApplication, QWidget, QLabel, QLineEdit, QPushButton, 
                             QVBoxLayout, QHBoxLayout, QFrame, QGridLayout, QSizePolicy, QMainWindow,
                             QFileDialog, QMessageBox, QSystemTrayIcon, QMenu)
from PyQt5.QtGui import QIcon, QPixmap, QFont, QPainter, QColor, QPen, QMouseEvent
from PyQt5.QtCore import Qt, QSize, QRect, QPoint, QCoreApplication
# 수정: 로깅 설정
logging.basicConfig(filename='folder_management.log', level=logging.DEBUG, 
                    format='%(asctime)s - %(levelname)s - %(message)s')

# 전역 변수로 모델과 토크나이저 선언
model = None
tokenizer = None

def load_model():
    global model, tokenizer
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model = BertForSequenceClassification.from_pretrained('bert-base-uncased', num_labels=5)
    
    # 수정: 사전 훈련된 가중치 로드
    model.load_state_dict(torch.load('quantized_model.pth', map_location=device), strict=False)
    
    model.to(device)
    model.eval()  # 평가 모드로 설정
    tokenizer = BertTokenizer.from_pretrained('bert-base-uncased')
    print("모델이 성공적으로 로드되었습니다.")
class CustomTitleBar(QWidget):
    def __init__(self, parent):
        super(CustomTitleBar, self).__init__(parent)
        self.parent = parent
        self.layout = QHBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.setFixedHeight(30)  # Title bar height
        self.layout.setContentsMargins(10, 0, 0, 0)  # Left margin set to 10 to push the icon right
        self.setFixedHeight(30)  # Title bar height
        # Title label
        self.title = QLabel("폴더 관리")
        self.title.setStyleSheet("color: white; font-size: 12pt; font-weight: bold;")

        # Icon
        icon_label = QLabel()
        icon_pixmap = QPixmap('Vector3.png')
        icon_label.setPixmap(icon_pixmap.scaled(16, 16, Qt.KeepAspectRatio, Qt.SmoothTransformation))

        # Buttons
        self.btn_close = QPushButton("X")
        self.btn_max = QPushButton("□")
        self.btn_min = QPushButton("－")
        
        # Style for buttons
        for btn in [self.btn_close, self.btn_max, self.btn_min]:
            btn.setFixedSize(45, 30)
            btn.setStyleSheet("""
                QPushButton {
                    background-color: transparent;
                    color: white;
                    border: none;
                    font-size: 10pt;
                }
                QPushButton:hover {
                    background-color: rgba(255, 255, 255, 0.2);
                }
            """)

        self.layout.addWidget(icon_label)
        self.layout.addWidget(self.title)
        self.layout.addStretch()
        self.layout.addWidget(self.btn_min)
        self.layout.addWidget(self.btn_max)
        self.layout.addWidget(self.btn_close)

        # Connect buttons to actions
        self.btn_close.clicked.connect(self.parent.close)
        self.btn_max.clicked.connect(self.maximize_restore)
        self.btn_min.clicked.connect(self.parent.showMinimized)

        # Variables for dragging
        self.start = QPoint(0, 0)
        self.pressing = False

    def paintEvent(self, event):
        # Painting the background of the title bar
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setBrush(QColor("#001F3F"))  # Dark blue color
        painter.setPen(Qt.NoPen)
        painter.drawRect(self.rect())  # Fill the title bar area with color

    def mousePressEvent(self, event):
        self.start = self.mapToGlobal(event.pos())
        self.pressing = True

    def mouseMoveEvent(self, event):
        if self.pressing:
            end = self.mapToGlobal(event.pos())
            movement = end - self.start
            self.parent.setGeometry(self.parent.mapToGlobal(movement).x(),
                                    self.parent.mapToGlobal(movement).y(),
                                    self.parent.width(),
                                    self.parent.height())
            self.start = end

    def mouseReleaseEvent(self, event):
        self.pressing = False

    def maximize_restore(self):
        if self.parent.isMaximized():
            self.parent.showNormal()
        else:
            self.parent.showMaximized()

class CustomButton(QPushButton):
    def __init__(self, text, color, text_color, border_color=None, parent=None):
        super().__init__(text, parent)
        self.color = color
        self.text_color = text_color
        self.border_color = border_color if border_color else color
        self.setFont(QFont("Arial", 12, QFont.Bold))
        self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.setFixedSize(120, 40)
        self.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.color};
                color: {self.text_color};
                border: 2px solid {self.border_color};
                border-radius: 20px;
                padding: 5px;
            }}
            QPushButton:hover {{
                background-color: {QColor(self.color).lighter(110).name()};
            }}
            QPushButton:pressed {{
                background-color: {QColor(self.color).darker(110).name()};
            }}
        """)

class FolderIcon(QLabel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(30, 30)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor("#FFA500"))
        painter.drawRoundedRect(0, 5, 30, 20, 3, 3)
        painter.drawRoundedRect(0, 0, 15, 12, 3, 3)

# DownloadEventHandler 클래스 수정
class DownloadEventHandler(FileSystemEventHandler):
    def __init__(self, category_paths):
        self.last_modified = {}
        self.category_paths = category_paths

    def on_created(self, event):
        self.on_modified(event)

    def on_modified(self, event):
        if not event.is_directory:
            file_path = event.src_path
            current_time = time.time()
            if (file_path not in self.last_modified) or (current_time - self.last_modified[file_path] > 1):
                self.last_modified[file_path] = current_time
                _, file_extension = os.path.splitext(file_path)
                logging.info(f"파일이 수정되었습니다: {file_path}")
                self.process_modified(file_path)

    def process_modified(self, file_path):
        try:
            normalized_path = os.path.normpath(file_path)
            logging.info(f"파일 처리 시작: {normalized_path}")
            label = classify_files_in_folders([normalized_path])
            logging.info(f"분류 결과: {label}")
            
            if label in self.category_paths:
                dst_path = os.path.join(self.category_paths[label], os.path.basename(file_path))
                logging.info(f"파일을 이동할 경로: {dst_path}")
                try:
                    shutil.move(file_path, dst_path)
                    logging.info(f"파일을 이동했습니다: {dst_path}")
                except Exception as e:
                    logging.error(f"파일 이동 중 오류가 발생했습니다: {e}")
            else:
                logging.warning(f"레이블 {label}에 해당하는 경로가 없습니다.")
        except Exception as e:
            logging.error(f"파일 처리 중 예외가 발생했습니다: {e}")

# FolderManagementApp 클래스의 start_monitoring 메서드 수정
def start_monitoring(self):
    if not self.save_category_paths():
        return
    download_folder = self.download_path.text()
    if not download_folder:
        QMessageBox.warning(self, "경고", "다운로드 폴더 경로를 입력해주세요.")
        return
    
    if self.observer:
        self.observer.stop()
        self.observer.join()
    
    self.observer = Observer()
    event_handler = DownloadEventHandler(self.category_paths)
    self.observer.schedule(event_handler, download_folder, recursive=False)
    self.observer.start()
    logging.info(f"모니터링 시작: {download_folder}")
    print(f"모니터링 시작: {download_folder}")
    QMessageBox.information(self, "알림", "모니터링이 시작되었습니다.")

    # 모델 미리 로드
    load_model()

def classify_files_in_folders(paths):
    global model, tokenizer
    
    if model is None or tokenizer is None:
        load_model()

    def clean_text_for_excel(text):
        cleaned_text = re.sub(r'[\000-\010]|[\013-\014]|[\016-\037]', '', text)
        cleaned_text = ''.join(c for c in cleaned_text if c.isprintable())
        return cleaned_text

    def classify_file(file_content, file_name):
        device = next(model.parameters()).device  # 모델의 디바이스 확인
        text = file_content or file_name
        inputs = tokenizer.encode_plus(
            text, None, add_special_tokens=True, max_length=128,
            padding='max_length', truncation=True, return_token_type_ids=False
        )
        input_ids = torch.tensor(inputs['input_ids'], dtype=torch.long).unsqueeze(0).to(device)
        attention_mask = torch.tensor(inputs['attention_mask'], dtype=torch.long).unsqueeze(0).to(device)
        with torch.no_grad():
            outputs = model(input_ids=input_ids, attention_mask=attention_mask)
            _, preds = torch.max(outputs.logits, dim=1)
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

    dev_extensions = ['.py', '.js', '.java', '.cpp', '.c', '.html', '.css', '.php', '.rb', '.go', '.ts', '.swift']

    results = []

    for path in paths:
        if os.path.isfile(path):
            folder_path, filename = os.path.split(path)
            file_content = ""
            
            _, extension = os.path.splitext(filename.lower())
            
            if extension in dev_extensions:
                results.append((filename, '개발파일'))
                logging.info(f"{filename}은 개발 파일로 분류되었습니다.")
                continue

            try:
                if filename.endswith(".hwp"):
                    f = olefile.OleFileIO(path)
                    encoded_txt = f.openstream("PrvText").read()
                    file_content = encoded_txt.decode("utf-16", errors="ignore")
                elif filename.endswith(".pdf"):
                    doc = fitz.open(path)
                    for page in doc:
                        file_content += page.get_text()
                    doc.close()
                
                cleaned_text = clean_text_for_excel(file_content)
                file_label = classify_file(cleaned_text, filename)
                label_name = get_label_name(file_label)
                results.append((filename, label_name))
                logging.info(f"{filename}은 {label_name}으로 분류되었습니다.")
            except Exception as e:
                logging.error(f"{filename} 처리 중 오류 발생: {e}")
                results.append((filename, f"Error: {e}"))

    return results[0][1] if results else 'Unknown'

class SystemTrayIcon(QSystemTrayIcon):
    def __init__(self, icon, parent=None):
        QSystemTrayIcon.__init__(self, icon, parent)
        menu = QMenu(parent)
        exitAction = menu.addAction("Exit")
        exitAction.triggered.connect(QCoreApplication.instance().quit)
        self.setContextMenu(menu)
        self.activated.connect(self.Activation_Reason)

    def Activation_Reason(self, index):
        if index == 2:
            print("Double Click")

class FolderManagementApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.initUI()
        self.category_paths = {}
        self.observer = None

    def initUI(self):
        self.setWindowFlags(Qt.FramelessWindowHint)
        self.setGeometry(10, 50, 1920, 888)
        self.setMaximumSize(1920, 888)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Custom title bar
        self.title_bar = CustomTitleBar(self)
        self.title_bar.setFixedHeight(30)
        self.title_bar.setStyleSheet("background-color: #001F3F;")
        main_layout.addWidget(self.title_bar)

        # Main content
        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        content_widget.setStyleSheet("""
            QWidget {
                background-color: #F0F0F0;
                font-family: Arial;
                font-size: 14px;
            }
            QLineEdit {
                background-color: white;
                border: 1px solid #CCCCCC;
                border-radius: 5px;
                padding: 5px;
                font-size: 16px;
            }
            QLabel {
                color: #333333;
                font-weight: bold;
            }
        """)

        # Download folder path
        download_label = QLabel('다운로드 폴더 경로')
        download_label.setFont(QFont("Arial", 48, QFont.Bold))
        download_label.setAlignment(Qt.AlignCenter)
        content_layout.addWidget(download_label)
        download_label.setStyleSheet("font-size: 30px;")
        content_layout.addSpacing(-50)

        download_layout = QHBoxLayout()
        self.download_path = QLineEdit()
        self.download_path.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        download_layout.addWidget(self.download_path, 4)
        
        # 수정: '폴더 찾기' 버튼에 기능 추가
        find_folder_button = CustomButton('폴더 찾기', '#4169E1', 'white')
        find_folder_button.clicked.connect(self.browse_download_folder)
        download_layout.addWidget(find_folder_button, 1)
        
        # 수정: '추가' 버튼에 기능 추가
        add_button = CustomButton('추가', 'white', '#4169E1', '#4169E1')
        add_button.clicked.connect(self.add_download_path)
        download_layout.addWidget(add_button, 1)
        
        # 수정: '삭제' 버튼에 기능 추가
        delete_button = CustomButton('삭제', 'white', '#4169E1', '#4169E1')
        delete_button.clicked.connect(self.delete_download_path)
        download_layout.addWidget(delete_button, 1)
        
        content_layout.addLayout(download_layout)

        # Category paths
        category_label = QLabel('카테고리 폴더 경로')
        category_label.setFont(QFont("Arial", 48, QFont.Bold))
        category_label.setAlignment(Qt.AlignCenter)
        content_layout.addWidget(category_label)
        category_label.setStyleSheet("font-size: 30px;")
        content_layout.addSpacing(-50)
        categories_frame = QFrame()
        categories_frame.setStyleSheet("""
            QFrame {
                background-color: #001F3F;
                border-radius: 10px;
                padding: 10px;
            }
            QLabel { color: white;  font-weight: bold; }
        """)
        categories_layout = QGridLayout(categories_frame)
        categories = ['리포트', '강의파일', '취업파일', '신청서', '개발']
        self.category_edits = {}
        for i, category in enumerate(categories):
            categories_layout.addWidget(FolderIcon(), i, 0)
            categories_layout.addWidget(QLabel(category), i, 1)
            line_edit = QLineEdit()
            line_edit.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            categories_layout.addWidget(line_edit, i, 2)
            self.category_edits[category] = line_edit
            
            # 수정: 각 카테고리의 '폴더 찾기' 버튼에 기능 추가
            find_button = CustomButton('폴더 찾기', '#4169E1', 'white')
            find_button.clicked.connect(lambda _, le=line_edit: self.browse_folder(le))
            categories_layout.addWidget(find_button, i, 3)
            
            # 수정: 각 카테고리의 '삭제' 버튼에 기능 추가
            delete_button = CustomButton('삭제', 'white', '#4169E1', '#4169E1')
            delete_button.clicked.connect(lambda _, le=line_edit: self.delete_category_path(le))
            categories_layout.addWidget(delete_button, i, 4)

        categories_layout.setColumnStretch(2, 1)
        content_layout.addWidget(categories_frame)

        # Bottom buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch(1)
        start_button = CustomButton('시작', '#4169E1', 'white')
        start_button.clicked.connect(self.start_monitoring)
        button_layout.addWidget(start_button)
        quit_button = CustomButton('종료', '#4169E1', 'white')
        quit_button.clicked.connect(self.close)
        button_layout.addWidget(quit_button)
        content_layout.addLayout(button_layout)

        # Add wave decoration
        wave_label = QLabel()
        wave_pixmap = QPixmap('Group34868.png')
        wave_label.setPixmap(wave_pixmap)
        content_layout.addWidget(wave_label)

        main_layout.addWidget(content_widget)

    def mousePressEvent(self, event):
        self.oldPos = event.globalPos()

    def mouseMoveEvent(self, event):
        delta = QPoint(event.globalPos() - self.oldPos)
        self.move(self.x() + delta.x(), self.y() + delta.y())
        self.oldPos = event.globalPos()

    # 수정: 폴더 찾기 기능 구현
    def browse_folder(self, line_edit):
        folder_path = QFileDialog.getExistingDirectory(self, "폴더 선택")
        if folder_path:
            line_edit.setText(folder_path)

    # 수정: 다운로드 폴더 찾기 기능 구현
    def browse_download_folder(self):
        folder_path = QFileDialog.getExistingDirectory(self, "다운로드 폴더 선택")
        if folder_path:
            self.download_path.setText(folder_path)

    # 수정: 다운로드 경로 추가 기능 구현
    def add_download_path(self):
        path = self.download_path.text()
        if path:
            QMessageBox.information(self, "추가 완료", f"다운로드 경로가 추가되었습니다: {path}")
        else:
            QMessageBox.warning(self, "오류", "다운로드 경로를 입력해주세요.")

    # 수정: 다운로드 경로 삭제 기능 구현
    def delete_download_path(self):
        self.download_path.clear()
        QMessageBox.information(self, "삭제 완료", "다운로드 경로가 삭제되었습니다.")

    # 수정: 카테고리 경로 삭제 기능 구현
    def delete_category_path(self, line_edit):
        line_edit.clear()
        QMessageBox.information(self, "삭제 완료", "카테고리 경로가 삭제되었습니다.")

    def save_category_paths(self):
        self.category_paths = {
            "리포트파일": self.category_edits['리포트'].text(),
            "강의파일": self.category_edits['강의파일'].text(),
            "취업파일": self.category_edits['취업파일'].text(),
            "신청서파일": self.category_edits['신청서'].text(),
            "개발파일": self.category_edits['개발'].text()
        }
        for key, path in self.category_paths.items():
            if not path:
                QMessageBox.warning(self, "경고", "채워지지 않은 칸이 있습니다.")
                return False
        print(f"카테고리 경로가 저장되었습니다: {self.category_paths}")
        return True

    def start_monitoring(self):
        if not self.save_category_paths():
            return
        download_folder = self.download_path.text()
        if not download_folder:
            QMessageBox.warning(self, "경고", "다운로드 폴더 경로를 입력해주세요.")
            return
        
        if self.observer:
            self.observer.stop()
            self.observer.join()
        
        self.observer = Observer()
        event_handler = DownloadEventHandler(self.category_paths)
        self.observer.schedule(event_handler, download_folder, recursive=False)
        self.observer.start()
        print(f"모니터링 시작: {download_folder}")
        QMessageBox.information(self, "알림", "모니터링이 시작되었습니다.")

    def closeEvent(self, event):
        if self.observer:
            self.observer.stop()
            self.observer.join()
        event.accept()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = FolderManagementApp()
    tray_icon = SystemTrayIcon(QIcon('Group34869.png'), ex)
    tray_icon.show()
    ex.show()
    sys.exit(app.exec_())