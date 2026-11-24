import errno
import os
import shutil
import stat
from tempfile import TemporaryDirectory
import tkinter as tk
from tkinter import filedialog, messagebox, Toplevel
from PIL import Image, ImageTk, ExifTags
import json
import sys
import datetime


def move_without_overwrite(source_path, destination_path):
    """Move a photo while preserving any file at the destination."""
    if os.path.lexists(destination_path):
        raise FileExistsError(f"같은 이름의 파일 또는 폴더가 있습니다.\n{destination_path}")

    # Windows의 같은 드라이브 안에서는 기존 파일을 덮어쓰지 않는 이름 변경을 사용한다.
    if os.name == 'nt':
        try:
            os.rename(source_path, destination_path)
            return
        except OSError as error:
            if error.errno != errno.EXDEV:
                raise

    # 복사가 끝난 파일만 최종 이름으로 옮기고, 기존 파일이 생겼으면 중단한다.
    destination_folder = os.path.dirname(destination_path) or '.'
    with TemporaryDirectory(dir=destination_folder) as temporary_folder:
        staged_path = os.path.join(temporary_folder, 'photo')
        shutil.copy2(source_path, staged_path, follow_symlinks=False)
        if os.name == 'nt':
            os.rename(staged_path, destination_path)
        else:
            os.link(staged_path, destination_path, follow_symlinks=False)

        try:
            os.unlink(source_path)
        except OSError:
            if os.name == 'nt' and not os.path.islink(destination_path):
                os.chmod(destination_path, stat.S_IWRITE)
            os.unlink(destination_path)
            raise


class PhotoSorterApp:
    def __init__(self, root):
        self.root = root
        self.root.title("사진 분류 프로그램")
        self.root.geometry("800x600")  # 창 크기 조정

        self.source_folder = ""
        self.destination_folders = {}
        self.photo_list = []
        self.current_photo_index = 0  # 현재 사진 인덱스

        self.is_sorting_mode = False

        self.resize_job = None  # resize_job 초기화

        self.move_history = []  # 이동 기록을 저장할 스택

        # 단축키 관련 변수 초기화
        self.shortcuts = {
            'select_source_folder': None,
            'select_all_destination_folders': None,
            'select_specific_destination_folders': None,
            'set_shortcuts': None,
            'toggle_sorting_mode': None,
            'undo_move': None  # 실행 취소 단축키 추가
        }
        self.function_map = {
            'select_source_folder': self.select_source_folder,
            'select_all_destination_folders': self.select_all_destination_folders,
            'select_specific_destination_folders': self.select_specific_destination_folders,
            'set_shortcuts': self.set_shortcuts,
            'toggle_sorting_mode': self.toggle_sorting_mode,
            'undo_move': self.undo_move  # 실행 취소 함수 매핑
        }
        self.shortcut_key_labels = {}  # 단축키 레이블 저장

        # 정렬 옵션 설정
        self.sort_options = [
            '파일 이름 오름차순',
            '파일 이름 내림차순',
            '수정 날짜 오름차순',
            '수정 날짜 내림차순',
            '촬영 날짜 오름차순',    # 추가
            '촬영 날짜 내림차순'     # 추가
        ]
        self.selected_sort_option = tk.StringVar()
        self.selected_sort_option.set(self.sort_options[0])  # 기본값 설정

        # UI 설정
        self.setup_ui()

        # 설정 불러오기
        self.load_settings()

    def get_settings_path(self):
        # 실행 파일의 경로를 안전하게 가져오기 위해 수정
        if getattr(sys, 'frozen', False):
            # PyInstaller로 빌드된 실행 파일인 경우
            application_path = os.path.dirname(sys.executable)
        else:
            # 일반 스크립트 실행인 경우
            application_path = os.path.dirname(__file__)

        if sys.platform.startswith('win'):
            # Windows인 경우
            appdata = os.getenv('APPDATA')
            settings_dir = os.path.join(appdata, 'PhotoSorter')
        elif sys.platform == 'darwin':
            # macOS인 경우
            home_dir = os.path.expanduser('~')
            settings_dir = os.path.join(home_dir, 'Library', 'Application Support', 'PhotoSorter')
        else:
            # Linux 등 다른 OS인 경우
            home_dir = os.path.expanduser('~')
            settings_dir = os.path.join(home_dir, '.config', 'PhotoSorter')

        # 디렉토리가 없으면 생성
        if not os.path.exists(settings_dir):
            os.makedirs(settings_dir)

        settings_path = os.path.join(settings_dir, 'settings.json')
        return settings_path

    def save_settings(self):
        settings = {
            'source_folder': self.source_folder,
            'destination_folders': self.destination_folders,
            'shortcuts': self.shortcuts,
            'selected_sort_option': self.selected_sort_option.get()
        }
        with open(self.get_settings_path(), 'w', encoding='utf-8') as f:
            json.dump(settings, f, ensure_ascii=False, indent=4)

    def load_settings(self):
        settings_path = self.get_settings_path()
        if os.path.exists(settings_path):
            with open(settings_path, 'r', encoding='utf-8') as f:
                settings = json.load(f)
                self.source_folder = settings.get('source_folder', '')
                # 원본 폴더 존재 여부 확인
                if not os.path.exists(self.source_folder):
                    self.source_folder = ''

                # 분류 폴더 로드 시 키를 정수로 변환
                self.destination_folders = {int(k): v for k, v in settings.get('destination_folders', {}).items()}
                # 분류 폴더 존재 여부 확인
                self.destination_folders = {k: v for k, v in self.destination_folders.items() if os.path.exists(v)}

                self.shortcuts = settings.get('shortcuts', {})
                selected_sort_option = settings.get('selected_sort_option', self.sort_options[0])
                self.selected_sort_option.set(selected_sort_option)
                # 단축키를 다시 바인딩
                for func_name, key_sym in self.shortcuts.items():
                    if key_sym:
                        self.root.bind_all(f'<{key_sym}>', lambda e, fn=func_name: self.execute_shortcut(e, fn))
                # UI 업데이트
                self.update_labels()
                if self.source_folder:
                    self.load_photos()

    def setup_ui(self):
        # 버튼들을 담을 프레임 생성
        self.button_frame = tk.Frame(self.root)
        self.button_frame.pack(pady=5, fill=tk.X)

        # 버튼들을 가로로 나열
        tk.Button(self.button_frame, text="원본 폴더 선택", command=self.select_source_folder).pack(side=tk.LEFT, padx=5)
        tk.Button(self.button_frame, text="모든 분류 폴더 선택", command=self.select_all_destination_folders).pack(side=tk.LEFT, padx=5)
        tk.Button(self.button_frame, text="분류 폴더 선택", command=self.select_specific_destination_folders).pack(side=tk.LEFT, padx=5)
        tk.Button(self.button_frame, text="단축키 설정", command=self.set_shortcuts).pack(side=tk.LEFT, padx=5)
        self.sort_button = tk.Button(self.button_frame, text="분류 시작", command=self.toggle_sorting_mode)
        self.sort_button.pack(side=tk.LEFT, padx=5)
        tk.Button(self.button_frame, text="실행 취소", command=self.undo_move).pack(side=tk.LEFT, padx=5)  # 실행 취소 버튼 추가

        # 정렬 옵션 드롭다운 메뉴 추가
        tk.Label(self.button_frame, text="정렬 기준:").pack(side=tk.LEFT, padx=5)
        self.sort_option_menu = tk.OptionMenu(self.button_frame, self.selected_sort_option, *self.sort_options, command=self.on_sort_option_changed)
        self.sort_option_menu.pack(side=tk.LEFT, padx=5)

        # 원본 폴더 및 분류 폴더 정보를 표시하는 레이블을 버튼 프레임에 추가
        self.info_label = tk.Label(self.button_frame, text="원본 폴더: 없음 / 선택된 분류 폴더: 0개")
        self.info_label.pack(side=tk.LEFT, padx=5)

        # 이미지 표시를 위한 프레임과 레이블
        self.image_frame = tk.Frame(self.root)
        self.image_frame.pack(expand=True, fill=tk.BOTH)
        self.image_label = tk.Label(self.image_frame)
        self.image_label.pack(expand=True, fill=tk.BOTH)

        self.root.bind("<KeyPress>", self.handle_keypress)
        self.root.bind("<Configure>", self.on_resize)  # 창 크기 변경 이벤트 바인딩

    def on_sort_option_changed(self, *args):
        if self.source_folder:
            self.load_photos()

    def update_labels(self):
        source_text = f"원본 폴더: {self.source_folder if self.source_folder else '없음'}"
        dest_count = len(self.destination_folders)
        dest_text = f"선택된 분류 폴더: {dest_count}개"
        self.info_label.config(text=f"{source_text} / {dest_text}")

    def select_source_folder(self):
        folder = filedialog.askdirectory(title="원본 폴더 선택")
        if folder:
            self.source_folder = folder
            self.load_photos()
            self.update_labels()  # 레이블 업데이트

    def load_photos(self):
        # 지원하는 이미지 파일 확장자 정의
        supported_extensions = ('.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.webp')
        # 원본 폴더에서 이미지 파일 리스트 로드
        photo_files = [
            f for f in os.listdir(self.source_folder)
            if os.path.isfile(os.path.join(self.source_folder, f))
            and not f.startswith('.')
            and f.lower().endswith(supported_extensions)
        ]

        # 정렬 옵션에 따라 정렬
        sort_option = self.selected_sort_option.get()

        if sort_option == '파일 이름 오름차순':
            self.photo_list = sorted(photo_files)
        elif sort_option == '파일 이름 내림차순':
            self.photo_list = sorted(photo_files, reverse=True)
        elif sort_option == '수정 날짜 오름차순':
            self.photo_list = sorted(photo_files, key=lambda x: os.path.getmtime(os.path.join(self.source_folder, x)))
        elif sort_option == '수정 날짜 내림차순':
            self.photo_list = sorted(photo_files, key=lambda x: os.path.getmtime(os.path.join(self.source_folder, x)), reverse=True)
        elif sort_option == '촬영 날짜 오름차순':
            self.photo_list = sorted(photo_files, key=lambda x: self.get_taken_date_safe(os.path.join(self.source_folder, x)) or datetime.datetime.min)
        elif sort_option == '촬영 날짜 내림차순':
            self.photo_list = sorted(photo_files, key=lambda x: self.get_taken_date_safe(os.path.join(self.source_folder, x)) or datetime.datetime.min, reverse=True)
        else:
            self.photo_list = photo_files  # 기본값

        self.current_photo_index = 0
        if self.photo_list:
            print(f"{len(self.photo_list)}개의 이미지 파일을 찾았습니다.")
            self.display_photo()
        else:
            messagebox.showinfo("사진이 없습니다", "선택한 원본 폴더에 사진이 없습니다.")

    def get_taken_date_safe(self, photo_path):
        date_str = get_taken_date(photo_path)
        if date_str:
            try:
                # 날짜 문자열을 datetime 객체로 변환
                return datetime.datetime.strptime(date_str, '%Y:%m:%d %H:%M:%S')
            except ValueError as e:
                print(f"날짜 형식 변환 오류 ({photo_path}): {e}")
        return None

    def display_photo(self):
        if self.photo_list and 0 <= self.current_photo_index < len(self.photo_list):
            photo_path = os.path.join(self.source_folder, self.photo_list[self.current_photo_index])
            try:
                img = Image.open(photo_path)
                img.verify()  # 이미지 파일 유효성 검증
                img.close()   # 파일 닫기

                img = Image.open(photo_path)
                # 창 크기에 따라 이미지 크기 조정
                self.root.update_idletasks()  # 최신 윈도우 크기 정보를 가져오기 위해 업데이트

                # 이미지 표시 영역의 크기 가져오기
                frame_width = self.image_frame.winfo_width()
                frame_height = self.image_frame.winfo_height()

                # 윈도우 크기가 아직 설정되지 않은 경우 기본값 사용
                if frame_width < 10 or frame_height < 10:
                    frame_width = 800
                    frame_height = 600

                # 이미지의 가로세로 비율 계산
                img_ratio = img.width / img.height
                frame_ratio = frame_width / frame_height

                if img_ratio > frame_ratio:
                    # 이미지가 프레임보다 더 넓은 경우
                    new_width = frame_width
                    new_height = frame_width / img_ratio
                else:
                    # 이미지가 프레임보다 더 높은 경우
                    new_height = frame_height
                    new_width = frame_height * img_ratio

                # 이미지 크기 조정
                img = img.resize((int(new_width), int(new_height)), Image.LANCZOS)

                self.photo_image = ImageTk.PhotoImage(img)
                self.image_label.config(image=self.photo_image)
            except Exception as e:
                print(f"이미지 로드 오류 {photo_path}: {e}")
                # 이미지 로드에 실패하면 다음 이미지로 넘어감
                self.current_photo_index += 1
                if self.current_photo_index >= len(self.photo_list):
                    self.image_label.config(image='')
                    self.photo_image = None
                    messagebox.showerror("오류", "유효한 이미지 파일을 찾을 수 없습니다.")
                    self.is_sorting_mode = False
                    self.update_sort_button()  # 버튼 UI 업데이트
                    return
                else:
                    self.display_photo()
        else:
            self.image_label.config(image='')
            self.photo_image = None

    def on_resize(self, event):
        # 이전에 예약된 작업이 있으면 취소
        if self.resize_job is not None:
            self.root.after_cancel(self.resize_job)
        # 200밀리초 후에 display_photo 호출
        self.resize_job = self.root.after(200, self.display_photo)

    def select_all_destination_folders(self):
        for i in range(1, 10):
            folder = filedialog.askdirectory(title=f"분류 폴더 {i} 선택")
            if folder:
                self.destination_folders[i] = folder
            else:
                break
        messagebox.showinfo("분류 폴더 선택 완료", f"{len(self.destination_folders)}개의 폴더를 선택했습니다.")
        self.update_labels()  # 레이블 업데이트

    def select_specific_destination_folders(self):
        popup = Toplevel(self.root)
        popup.title("분류 폴더 선택")
        popup.geometry("500x500")  # 높이를 증가시킴
        popup.transient(self.root)
        popup.grab_set()
        popup.focus_set()
        popup.bind("<Escape>", lambda e: popup.destroy())  # ESC 키로 창 닫기

        folder_labels = []  # 폴더 레이블들을 저장할 리스트

        for i in range(1, 10):
            folder_label = tk.Label(popup, text=f"분류 폴더 {i}: {self.destination_folders.get(i, '선택되지 않음')}")
            folder_label.grid(row=i-1, column=0, padx=5, pady=5)
            folder_labels.append(folder_label)  # 레이블 저장
            tk.Button(popup, text=f"폴더 {i} 선택", command=lambda i=i, label=folder_label: self.update_specific_folder(i, label)).grid(row=i-1, column=1, padx=5, pady=5)

        # 분류 폴더 초기화 버튼 추가
        reset_button = tk.Button(popup, text="분류 폴더 초기화", command=lambda: self.reset_destination_folders(folder_labels))
        reset_button.grid(row=10, column=0, columnspan=2, padx=5, pady=20)  # 버튼을 아래쪽에 위치시킴

    def reset_destination_folders(self, folder_labels):
        result = messagebox.askquestion("분류 폴더 초기화", "모든 분류 폴더를 초기화하시겠습니까?", icon='warning')
        if result == 'yes':
            self.destination_folders.clear()
            # 폴더 레이블 업데이트
            for i, label in enumerate(folder_labels, start=1):
                label.config(text=f"분류 폴더 {i}: 선택되지 않음")
            self.update_labels()  # 메인 윈도우의 레이블 업데이트
            self.save_settings()  # 설정 저장

    def update_specific_folder(self, folder_number, folder_label):
        folder = filedialog.askdirectory(title=f"분류 폴더 {folder_number} 선택")
        if folder:
            self.destination_folders[folder_number] = folder
            folder_label.config(text=f"분류 폴더 {folder_number}: {folder}")
            self.update_labels()  # 레이블 업데이트

    def toggle_sorting_mode(self):
        if not self.source_folder:
            messagebox.showwarning("원본 폴더 없음", "먼저 원본 폴더를 선택하세요.")
            return
        if not self.destination_folders:
            messagebox.showwarning("분류 폴더 없음", "적어도 하나의 분류 폴더를 선택하세요.")
            return

        self.is_sorting_mode = not self.is_sorting_mode
        self.update_sort_button()  # 버튼 UI 업데이트

        if self.is_sorting_mode:
            if self.photo_list:
                self.display_photo()
            else:
                messagebox.showinfo("사진이 없습니다", "더 이상 분류할 사진이 없습니다.")
                self.is_sorting_mode = False
                self.update_sort_button()  # 버튼 UI 업데이트

    def update_sort_button(self):
        if self.is_sorting_mode:
            self.sort_button.config(bg="red", text="분류 중지")
        else:
            self.sort_button.config(bg="SystemButtonFace", text="분류 시작")

    def handle_keypress(self, event):
        if self.is_sorting_mode and event.char.isdecimal():
            folder_number = int(event.char)
            if folder_number in self.destination_folders:
                self.move_photo(folder_number)

    def move_photo(self, folder_number):
        if self.current_photo_index >= len(self.photo_list):
            self.is_sorting_mode = False
            self.update_sort_button()
            self.display_photo()
            messagebox.showinfo("사진이 없습니다", "더 이상 분류할 사진이 없습니다.")
            return

        photo_to_move = self.photo_list[self.current_photo_index]
        source_path = os.path.join(self.source_folder, photo_to_move)
        destination_path = os.path.join(self.destination_folders[folder_number], photo_to_move)

        try:
            move_without_overwrite(source_path, destination_path)
        except OSError as error:
            messagebox.showerror("이동 오류", str(error))
            return

        self.move_history.append((source_path, destination_path, photo_to_move))
        del self.photo_list[self.current_photo_index]
        finished = self.current_photo_index >= len(self.photo_list)
        if finished:
            self.is_sorting_mode = False
            self.update_sort_button()
        self.display_photo()
        if finished:
            messagebox.showinfo("완료", "모든 사진이 분류되었습니다.")

    def undo_move(self):
        if not self.move_history:
            messagebox.showinfo("실행 취소 불가", "실행 취소할 작업이 없습니다.")
            return

        source_path, destination_path, photo_name = self.move_history[-1]

        try:
            move_without_overwrite(destination_path, source_path)
        except OSError as error:
            messagebox.showerror("실행 취소 오류", str(error))
            return

        self.move_history.pop()
        original_folder = os.path.normcase(os.path.realpath(os.path.dirname(source_path)))
        current_folder = os.path.normcase(os.path.realpath(self.source_folder))
        if original_folder == current_folder and photo_name not in self.photo_list:
            self.photo_list.insert(self.current_photo_index, photo_name)
            self.display_photo()

    def on_closing(self):
        # 프로그램 종료 시 설정 저장
        self.save_settings()
        self.root.destroy()

    # 단축키 설정 기능 수정
    def set_shortcuts(self):
        popup = Toplevel(self.root)
        popup.title("단축키 설정")
        popup.geometry("400x350")
        popup.transient(self.root)
        popup.grab_set()
        popup.focus_set()
        popup.bind("<Escape>", lambda e: popup.destroy())  # ESC 키로 창 닫기

        functions = [
            ('원본 폴더 선택', 'select_source_folder'),
            ('모든 분류 폴더 선택', 'select_all_destination_folders'),
            ('분류 폴더 선택', 'select_specific_destination_folders'),
            ('단축키 설정', 'set_shortcuts'),
            ('분류 시작', 'toggle_sorting_mode'),
            ('실행 취소', 'undo_move')  # 실행 취소 추가
        ]

        self.waiting_for_key = None  # 현재 단축키를 기다리는 기능

        for idx, (label_text, func_name) in enumerate(functions):
            label = tk.Label(popup, text=label_text)
            label.grid(row=idx, column=0, padx=5, pady=5)

            key_label_text = self.shortcuts.get(func_name, '없음')
            key_label = tk.Label(popup, text=f"현재 단축키: {key_label_text}")
            key_label.grid(row=idx, column=1, padx=5, pady=5)
            self.shortcut_key_labels[func_name] = key_label  # 레이블 저장

            set_button = tk.Button(popup, text="설정", command=lambda fn=func_name, kl=key_label: self.wait_for_key(popup, fn, kl))
            set_button.grid(row=idx, column=2, padx=5, pady=5)

    def wait_for_key(self, popup, func_name, key_label):
        self.waiting_for_key = (func_name, key_label)
        # 안내 레이블 표시
        self.prompt_label = tk.Label(popup, text="할당할 키를 눌러주세요.")
        self.prompt_label.grid(row=len(self.shortcuts)+1, column=0, columnspan=3, padx=5, pady=5)
        # 버튼 비활성화
        for child in popup.winfo_children():
            if isinstance(child, tk.Button):
                child.config(state='disabled')
        popup.bind("<Key>", self.capture_key)

    def capture_key(self, event):
        if self.waiting_for_key:
            func_name, key_label = self.waiting_for_key
            key_sym = event.keysym

            # 숫자 키(1-9)는 분류 기능 전용이므로 단축키로 사용할 수 없음
            if key_sym in [str(n) for n in range(1, 10)]:
                messagebox.showwarning("단축키 설정 불가", "숫자 키(1-9)는 분류 기능 전용 키로 사용할 수 없습니다.")
                return

            # 이전에 동일한 키가 다른 기능에 할당되어 있는지 확인
            for fn, key in self.shortcuts.items():
                if key == key_sym and fn != func_name:
                    self.root.unbind_all(f'<{key}>')
                    self.shortcuts[fn] = None
                    # 다른 기능의 키 레이블 업데이트
                    key_label_to_update = self.shortcut_key_labels.get(fn)
                    if key_label_to_update:
                        key_label_to_update.config(text="현재 단축키: 없음")

            # 현재 기능에 할당된 이전 키의 바인딩 제거
            prev_key = self.shortcuts.get(func_name)
            if prev_key:
                self.root.unbind_all(f'<{prev_key}>')

            # 단축키 딕셔너리 업데이트
            self.shortcuts[func_name] = key_sym
            key_label.config(text=f"현재 단축키: {key_sym}")

            # 키 바인딩 설정
            self.root.bind_all(f'<{key_sym}>', lambda e, fn=func_name: self.execute_shortcut(e, fn))

            # 대기 상태 초기화 및 키 이벤트 바인딩 해제
            self.waiting_for_key = None
            event.widget.unbind("<Key>")

            # 안내 레이블 제거 및 버튼 활성화
            self.prompt_label.destroy()
            for child in event.widget.winfo_children():
                if isinstance(child, tk.Button):
                    child.config(state='normal')

    def execute_shortcut(self, event, func_name):
        func = self.function_map.get(func_name)
        if func:
            func()

def get_taken_date(photo_path):
    try:
        img = Image.open(photo_path)
        exif_data = img._getexif()
        if exif_data:
            # EXIF 태그의 키와 이름 매핑 생성
            exif = {
                ExifTags.TAGS.get(k, k): v
                for k, v in exif_data.items()
            }
            taken_date = exif.get('DateTimeOriginal')
            if taken_date:
                # 날짜 형식을 통일하기 위해 반환
                return taken_date
    except Exception as e:
        print(f"EXIF 데이터 추출 오류 ({photo_path}): {e}")
    return None

if __name__ == "__main__":
    root = tk.Tk()
    app = PhotoSorterApp(root)
    root.protocol("WM_DELETE_WINDOW", app.on_closing)  # 창 닫기 이벤트 처리
    root.mainloop()
