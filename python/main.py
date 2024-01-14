from PyQt6.QtWidgets import QApplication, QMainWindow, QLabel, QLineEdit, QPushButton, QVBoxLayout, QWidget, QFileDialog, QListWidget, QInputDialog
from pymongo import MongoClient
import gridfs
import os

def clear_layout(layout, exclude=[]):
    for i in reversed(range(layout.count())):
        widget_item = layout.itemAt(i)
        if widget_item is not None:
            widget = widget_item.widget()
            if widget is not None and widget not in exclude:
                layout.removeWidget(widget)
                widget.deleteLater()



class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.db = self.connect_to_database()
        self.init_login_ui()

    def connect_to_database(self):
        client = MongoClient("mongodb://localhost:27017/")
        return client["ogrenci_bilgi_sistemi"]

    def init_login_ui(self):
        if not hasattr(self, 'username_input'):
            self.username_input = QLineEdit()
        if not hasattr(self, 'password_input'):
            self.password_input = QLineEdit()
            self.password_input.setEchoMode(QLineEdit.EchoMode.Password)

        self.setWindowTitle("Öğrenci Bilgi Sistemi")
        self.setGeometry(100, 100, 600, 600)

        layout = QVBoxLayout()

        self.username_label = QLabel("Kullanıcı Adı:")
        self.password_label = QLabel("Parola:")
        self.login_button = QPushButton("Giriş Yap")
        self.login_button.clicked.connect(self.login)

        layout.addWidget(self.username_label)
        layout.addWidget(self.username_input)
        layout.addWidget(self.password_label)
        layout.addWidget(self.password_input)
        layout.addWidget(self.login_button)

        self.central_widget = QWidget()
        self.central_widget.setLayout(layout)
        self.setCentralWidget(self.central_widget)

    def login(self):
        username = self.username_input.text()
        password = self.password_input.text()

        teacher = self.db["ogretmenler"].find_one({"ad": username, "parola": password})
        student = self.db["ogrenciler"].find_one({"ad": username, "parola": password})

        if teacher:
            self.init_teacher_ui()
        elif student:
            self.init_student_ui()
        else:
            print("Kullanıcı adı veya parola hatalı")

    def init_teacher_ui(self):
        clear_layout(self.central_widget.layout())

        layout = QVBoxLayout()

        self.upload_button = QPushButton("Dosya Yükle")
        self.upload_button.clicked.connect(self.upload_file)
        layout.addWidget(self.upload_button)

        self.central_widget = QWidget()
        self.central_widget.setLayout(layout)
        self.setCentralWidget(self.central_widget)

    def init_student_ui(self):
        clear_layout(self.central_widget.layout(), exclude=[self.username_input])  # Mevcut layout'u temizle

        layout = QVBoxLayout()

        self.ders_listesi = QListWidget()
        self.dosya_listesi = QListWidget()
        self.indir_button = QPushButton("Dosyayı İndir")
        self.indir_button.clicked.connect(self.download_file)

        self.populate_ders_listesi()

        layout.addWidget(QLabel("Dersler:"))
        layout.addWidget(self.ders_listesi)
        layout.addWidget(QLabel("Dosyalar:"))
        layout.addWidget(self.dosya_listesi)
        layout.addWidget(self.indir_button)

        self.central_widget = QWidget()
        self.central_widget.setLayout(layout)
        self.setCentralWidget(self.central_widget)

    def populate_ders_listesi(self):
        dersler = self.db["dersler"].find()
        for ders in dersler:
            self.ders_listesi.addItem(ders["ders_adi"])


    def upload_file(self):
        try:
            file_name, _ = QFileDialog.getOpenFileName(self, "Dosya Yükle")
            if file_name:
                # Ders adını ve yükleyen öğretmenin adını al
                ders_adi, ok = QInputDialog.getText(self, "Ders Adı", "Ders adını girin:")
                if ok and ders_adi:
                    yukleyen = self.username_input.text()
                    self.save_file_to_db(file_name, ders_adi, yukleyen)
        except Exception as e:
            print(f"Bir hata oluştu: {e}")

    def save_file_to_db(self, file_path, ders_adi, yukleyen):
        fs = gridfs.GridFS(self.db)

        with open(file_path, "rb") as f:
            file_name = os.path.basename(file_path)
            gridfs_id = fs.put(f, filename=file_name)

        self.db["ders_materyalleri"].insert_one({
            "dosya_adi": file_name,
            "gridfs_id": gridfs_id,
            "yukleyen": yukleyen,
            "ders": ders_adi
        })

        print(f"{file_name} veritabanına yüklendi.")



    def download_file(self):
        secili_dosya = self.dosya_listesi.currentItem()
        if secili_dosya:
            file_name = secili_dosya.text()
            self.get_file_from_db(file_name)

    def get_file_from_db(self, dosya_adi):
        materyal = self.db["ders_materyalleri"].find_one({"dosya_adi": dosya_adi})
        if materyal:
            fs = gridfs.GridFS(self.db)
            gridfs_id = materyal["gridfs_id"]
            file_data = fs.get(gridfs_id)

            with open(dosya_adi, "wb") as f:
                f.write(file_data.read())

            print(f"{dosya_adi} başarıyla indirildi.")


app = QApplication([])
window = MainWindow()
window.show()
app.exec()
