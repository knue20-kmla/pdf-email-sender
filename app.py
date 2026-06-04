import os
from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from dotenv import load_dotenv
import json

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('FLASK_SECRET_KEY', 'dev-secret-key')

SCOPES = [
    'https://www.googleapis.com/auth/drive.readonly',
    'https://www.googleapis.com/auth/drive.metadata.readonly',
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/gmail.send'
]

GOOGLE_SHEET_ID = os.getenv('GOOGLE_SHEET_ID')

def get_credentials():
    """세션에서 credentials 가져오기"""
    if 'credentials' not in session:
        return None
    return Credentials(**session['credentials'])

def save_credentials(credentials):
    """credentials를 세션에 저장"""
    session['credentials'] = {
        'token': credentials.token,
        'refresh_token': credentials.refresh_token,
        'token_uri': credentials.token_uri,
        'client_id': credentials.client_id,
        'client_secret': credentials.client_secret,
        'scopes': credentials.scopes
    }

@app.route('/')
def index():
    """메인 페이지"""
    if 'credentials' not in session:
        return redirect(url_for('authorize'))
    return render_template('index.html')

@app.route('/authorize')
def authorize():
    """Google OAuth 인증 시작"""
    credentials_json = os.getenv('GOOGLE_CREDENTIALS')
    if credentials_json:
        client_config = json.loads(credentials_json)
    else:
        with open('credentials.json', 'r') as f:
            client_config = json.load(f)

    flow = Flow.from_client_config(
        client_config,
        scopes=SCOPES,
        redirect_uri=url_for('oauth2callback', _external=True)
    )
    authorization_url, state = flow.authorization_url(
        access_type='offline',
        include_granted_scopes='true'
    )
    session['state'] = state
    return redirect(authorization_url)

@app.route('/oauth2callback')
def oauth2callback():
    """Google OAuth 콜백"""
    state = session['state']
    credentials_json = os.getenv('GOOGLE_CREDENTIALS')
    if credentials_json:
        client_config = json.loads(credentials_json)
    else:
        with open('credentials.json', 'r') as f:
            client_config = json.load(f)

    flow = Flow.from_client_config(
        client_config,
        scopes=SCOPES,
        state=state,
        redirect_uri=url_for('oauth2callback', _external=True)
    )
    flow.fetch_token(authorization_response=request.url)
    credentials = flow.credentials
    save_credentials(credentials)
    return redirect(url_for('index'))

@app.route('/api/folders')
def get_folders():
    """구글 드라이브 폴더 목록 가져오기"""
    credentials = get_credentials()
    if not credentials:
        return jsonify({'error': 'Not authenticated'}), 401

    try:
        service = build('drive', 'v3', credentials=credentials)
        results = service.files().list(
            q="mimeType='application/vnd.google-apps.folder'",
            pageSize=50,
            fields="files(id, name)"
        ).execute()
        folders = results.get('files', [])
        return jsonify(folders)
    except HttpError as error:
        return jsonify({'error': str(error)}), 500

@app.route('/api/students')
def get_students():
    """구글 시트에서 학생 목록 가져오기"""
    credentials = get_credentials()
    if not credentials:
        return jsonify({'error': 'Not authenticated'}), 401

    try:
        service = build('sheets', 'v4', credentials=credentials)
        result = service.spreadsheets().values().get(
            spreadsheetId=GOOGLE_SHEET_ID,
            range='A2:E'
        ).execute()
        values = result.get('values', [])

        students = []
        for i, row in enumerate(values, start=2):
            if len(row) > 0:
                students.append({
                    'row': i,
                    'name': row[0] if len(row) > 0 else '',
                    'exam_type': row[1] if len(row) > 1 else '',
                    'link': row[2] if len(row) > 2 else '',
                    'email': row[3] if len(row) > 3 else '',
                    'status': row[4] if len(row) > 4 else ''
                })

        return jsonify(students)
    except HttpError as error:
        return jsonify({'error': str(error)}), 500

@app.route('/api/send', methods=['POST'])
def send_emails():
    """이메일 발송 및 시트 업데이트"""
    credentials = get_credentials()
    if not credentials:
        return jsonify({'error': 'Not authenticated'}), 401

    data = request.json
    folder_id = data.get('folder_id')
    folder_name = data.get('folder_name')

    if not folder_id:
        return jsonify({'error': 'Folder ID is required'}), 400

    try:
        drive_service = build('drive', 'v3', credentials=credentials)
        sheets_service = build('sheets', 'v4', credentials=credentials)
        gmail_service = build('gmail', 'v1', credentials=credentials)

        results = drive_service.files().list(
            q=f"'{folder_id}' in parents and mimeType='application/pdf'",
            fields="files(id, name)"
        ).execute()
        files = results.get('files', [])

        sheet_result = sheets_service.spreadsheets().values().get(
            spreadsheetId=GOOGLE_SHEET_ID,
            range='A2:E'
        ).execute()
        students = sheet_result.get('values', [])

        student_map = {}
        for i, row in enumerate(students, start=2):
            if len(row) > 3:
                name = row[0]
                email = row[3]
                student_map[name] = {'email': email, 'row': i}

        results_list = []
        updates = []

        for file in files:
            name = file['name'].replace('.pdf', '')

            if name not in student_map:
                results_list.append({'name': name, 'status': 'error', 'message': '이메일을 찾을 수 없습니다'})
                continue

            student = student_map[name]
            email = student['email']
            row = student['row']
            file_id = file['id']

            try:
                drive_service.permissions().create(
                    fileId=file_id,
                    body={'type': 'anyone', 'role': 'reader'}
                ).execute()
            except:
                pass

            pdf_link = f"https://drive.google.com/file/d/{file_id}/view"

            try:
                from email.mime.text import MIMEText
                import base64

                message = MIMEText(f"""
안녕하세요 {name}님,

{folder_name} 성적표를 전달드립니다.

성적표 확인: {pdf_link}

감사합니다.
""")
                message['to'] = email
                message['subject'] = f'[{folder_name}] 성적표 발송'

                raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode()
                gmail_service.users().messages().send(
                    userId='me',
                    body={'raw': raw_message}
                ).execute()

                updates.append({
                    'range': f'B{row}:E{row}',
                    'values': [[folder_name, pdf_link, email, '발송 완료']]
                })

                results_list.append({'name': name, 'status': 'success', 'email': email})

            except Exception as e:
                results_list.append({'name': name, 'status': 'error', 'message': str(e)})

        if updates:
            sheets_service.spreadsheets().values().batchUpdate(
                spreadsheetId=GOOGLE_SHEET_ID,
                body={'data': updates, 'valueInputOption': 'RAW'}
            ).execute()

        return jsonify({'results': results_list})

    except HttpError as error:
        return jsonify({'error': str(error)}), 500

if __name__ == '__main__':
    os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'
    app.run(debug=True, port=5000)
