# 사진 분류 프로그램

사진을 한 장씩 보면서 숫자 키로 최대 9개의 폴더에 옮기는 Windows 데스크톱 도구입니다. 파일 이름, 수정 날짜, EXIF 촬영 날짜로 정렬할 수 있고, 프로그램을 실행하는 동안 옮긴 사진은 실행 취소로 되돌릴 수 있습니다.

## 실행하기

Windows에 Python 3.11 이상과 Tkinter가 설치되어 있어야 합니다. Python 설치 시 Tcl/Tk 옵션을 포함합니다.

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe photo_sorter.py
```

1. **원본 폴더 선택**으로 분류할 사진이 있는 폴더를 엽니다.
2. **분류 폴더 선택**에서 숫자에 폴더를 연결합니다. **모든 분류 폴더 선택**을 누르면 1번부터 순서대로 지정할 수 있습니다.
3. **분류 시작**을 누르고 미리보기에서 사진을 확인한 뒤 `1`~`9`로 해당 폴더에 옮깁니다. **실행 취소**를 누르면 마지막 이동을 되돌립니다.

JPG, JPEG, PNG, GIF, BMP, TIFF, WebP 파일을 열 수 있습니다. 사진은 실제로 이동하며, 이동하거나 되돌릴 위치에 같은 이름의 파일이나 폴더가 있으면 작업을 중단합니다. 폴더와 단축키 설정은 `%APPDATA%\PhotoSorter\settings.json`에 저장됩니다.

## 소스 이력

첫 커밋에 2024년 11월 25일자로 보관된 Python 소스의 내용을 그대로 남겼습니다. 보관 소스와 당시 1.3 실행파일 사이에는 폴더 상태 표시 문구의 차이가 확인되었습니다. 1.0~1.3 실행파일이 남아 있지만, 현재 확인한 자료에서는 각 배포본의 정확한 소스 사본을 찾지 못했습니다. 현재 브랜치에는 같은 이름의 파일을 보호하고 이동 취소를 다시 시도할 수 있도록 수정한 코드가 들어 있습니다.

## 테스트

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```
