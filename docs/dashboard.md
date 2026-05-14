# Coffee Model Dashboard

Dashboard model đã chuyển từ Streamlit sang React + FastAPI.

## Chạy backend

```powershell
pip install -r requirements.txt
uvicorn api.main:app --reload --host 127.0.0.1 --port 8000
```

## Chạy frontend

```powershell
cd frontend
npm install
npm run dev
```

Mở `http://127.0.0.1:5173`.

## Ghi chú

- Dashboard chỉ làm phần model prediction, không làm data dashboard.
- Backend ưu tiên checkpoint trong `dashboard/model_registry.json`; nếu chưa có checkpoint thì train fallback từ CSV.
- Gemini đang dùng Vertex AI qua `google-genai`. File `.env` cần có:

```env
GOOGLE_GENAI_USE_VERTEXAI=true
GOOGLE_CLOUD_PROJECT=igot-studio
GOOGLE_CLOUD_LOCATION=global
```

Đăng nhập local bằng Application Default Credentials:

```powershell
gcloud auth application-default login
gcloud config set project igot-studio
gcloud auth application-default set-quota-project igot-studio
```

Nếu thiếu quyền, chưa bật Vertex AI API, hoặc chưa đăng nhập ADC, UI sẽ hiển thị trạng thái Gemini chưa khả dụng và không làm crash dashboard.
