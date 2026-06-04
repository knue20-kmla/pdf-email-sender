# PDF 이메일 자동 발송 시스템

구글 드라이브 폴더에 업로드된 PDF 파일을 자동으로 이메일로 발송하고 구글 시트에 기록하는 웹 애플리케이션입니다.

## 기능

- 구글 드라이브 폴더 선택 또는 ID 직접 입력
- 폴더 내 PDF 파일 자동 스캔
- 파일명으로 학생 이메일 자동 매칭
- Gmail로 자동 발송
- 구글 시트 자동 업데이트 (고사 종류, 성적표 링크, 발송 여부)

## 설치 방법

### 1. 의존성 설치

```bash
cd pdf-email-sender
pip install -r requirements.txt
```

### 2. Google Cloud 프로젝트 설정

1. [Google Cloud Console](https://console.cloud.google.com/)에 접속
2. 새 프로젝트 생성 또는 기존 프로젝트 선택
3. **API 및 서비스 > 라이브러리**로 이동하여 다음 API 활성화:
   - Google Drive API
   - Google Sheets API
   - Gmail API

### 3. OAuth 2.0 클라이언트 ID 생성

1. **API 및 서비스 > 사용자 인증 정보**로 이동
2. **+ 사용자 인증 정보 만들기** > **OAuth 클라이언트 ID** 선택
3. 애플리케이션 유형: **웹 애플리케이션**
4. 승인된 리디렉션 URI 추가:
   ```
   http://localhost:5000/oauth2callback
   ```
5. **만들기** 클릭
6. JSON 다운로드 후 프로젝트 폴더에 `credentials.json`으로 저장

### 4. 환경 변수 설정

`.env.example` 파일을 `.env`로 복사하고 수정:

```bash
cp .env.example .env
```

`.env` 파일 내용:
```
GOOGLE_SHEET_ID=Fmuv27d994uuzQiwT5v1VLp5l5O0peFjDR4L_WQ
FLASK_SECRET_KEY=your-random-secret-key-here
```

### 5. 구글 시트 설정

구글 시트에 다음 컬럼이 있어야 합니다:
- A: 학생명
- B: 고사 종류
- C: 성적표 링크
- D: 이메일
- E: 발송 여부

## 실행 방법

```bash
python app.py
```

브라우저에서 `http://localhost:5000` 접속

## 사용 방법

1. 처음 접속 시 Google 계정 로그인 및 권한 승인
2. 구글 드라이브에 폴더 생성 (예: "3월 학력평가")
3. 폴더에 PDF 파일 업로드 (예: `권정인.pdf`, `김성규.pdf`)
4. 웹앱에서 폴더 선택 또는 폴더 ID 입력
5. **발송하기** 버튼 클릭
6. 발송 결과 확인

## 작동 원리

1. 선택한 폴더의 모든 PDF 파일 스캔
2. 파일명(확장자 제외)에서 학생명 추출
3. 구글 시트에서 해당 학생의 이메일 조회
4. PDF 공유 링크 생성
5. Gmail로 이메일 발송
6. 구글 시트 업데이트:
   - B열: 고사 종류 (폴더명)
   - C열: 성적표 링크
   - E열: "발송 완료"

## 문제 해결

### "인증되지 않았습니다" 오류
- 브라우저 쿠키/캐시 삭제 후 재시도
- `/authorize` 경로로 다시 인증

### 이메일 발송 실패
- Gmail API 할당량 확인
- 발신 이메일 계정의 2단계 인증 설정 확인

### 폴더를 찾을 수 없음
- 폴더 ID가 정확한지 확인
- 해당 폴더에 대한 접근 권한 확인
