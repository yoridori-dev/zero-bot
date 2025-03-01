from pydrive2.auth import GoogleAuth
from pydrive2.drive import GoogleDrive
import os

# ✅ Google Drive 認証
def authenticate_drive():
    gauth = GoogleAuth()
    gauth.LoadCredentialsFile("credentials.json")  # ✅ 認証情報をロード

    if gauth.credentials is None:
        gauth.CommandLineAuth()  # ✅ 新しいターミナル認証方式
        gauth.SaveCredentialsFile("credentials.json")  # ✅ 初回認証時に保存
    elif gauth.access_token_expired:
        gauth.Refresh()  # ✅ トークンが期限切れならリフレッシュ
    else:
        gauth.Authorize()  # ✅ 認証済みならそのまま利用
    drive = authenticate_drive()

def upload_to_drive(file_path, folder_id):
    """Google Drive にファイルをアップロード"""
    try:
        file_name = os.path.basename(file_path)
        file_drive = drive.CreateFile({"title": file_name, "parents": [{"id": folder_id}]})
        file_drive.SetContentFile(file_path)
        file_drive.Upload()
        print(f"[DEBUG] {file_name} を Google Drive にアップロードしました")
        return True
    except Exception as e:
        print(f"[ERROR] Google Drive アップロードエラー: {e}")
        return False
