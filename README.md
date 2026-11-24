# 사진 분류 프로그램 1.0

사진을 한 장씩 확인하고 숫자 키로 최대 9개의 폴더에 옮기는 Windows 데스크톱 앱입니다. 파일 이름과 수정 날짜로 정렬할 수 있습니다.

## 실행하기

Windows에 Python 3.11 이상과 Tkinter가 필요합니다. Python 설치 시 Tcl/Tk 옵션을 포함합니다.

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe photo_sorter.py
```

1. **원본 폴더 선택**으로 사진이 있는 폴더를 엽니다.
2. **분류 폴더 선택**에서 숫자에 폴더를 연결합니다.
3. **분류 시작**을 누른 뒤 사진을 보면서 `1`~`9`로 원하는 폴더에 옮깁니다.

사진 파일은 실제로 이동합니다. 같은 이름의 대상 파일을 보호하는 코드와 테스트는 [maintenance 브랜치](https://github.com/nunmase/photo-sorter/tree/maintenance)에 있습니다.

## 버전별 소스

이 코드는 2024년 버전 1.0의 실행파일에서 복원했습니다. CPython 3.13.0으로 컴파일해 실행파일에 내장된 바이트코드와 소스 위치 정보가 일치하는지 확인했습니다. 주석과 공백의 원래 표기는 바이트코드로 확인할 수 없습니다.

| 버전 | 주요 기능 |
| --- | --- |
| [1.0](https://github.com/nunmase/photo-sorter/releases/tag/v1.0) | 미리보기, 숫자 키 분류, 파일 이름과 수정 날짜 정렬 |
| [1.1](https://github.com/nunmase/photo-sorter/releases/tag/v1.1) | 마지막 이동 실행 취소 |
| [1.2](https://github.com/nunmase/photo-sorter/releases/tag/v1.2) | EXIF 촬영 날짜 정렬 |
| [1.3](https://github.com/nunmase/photo-sorter/releases/tag/v1.3) | 분류 폴더 설정 초기화 |
