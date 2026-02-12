# DXF 견적 분석 API

quote.html의 실시간 견적 기능을 위해 DXF 파일을 분석하는 FastAPI 백엔드입니다.

## 설치

```bash
cd backend
pip install -r requirements.txt
```

## 실행

```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

개발 시: `http://localhost:8000`
API 문서: `http://localhost:8000/docs`

## API 엔드포인트

| 메서드 | 경로 | 설명 |
|--------|------|------|
| POST | `/analyze-dxf` | DXF 파일 업로드 → `{ length, piercing, area }` 반환 |
| GET | `/health` | 헬스 체크 |

## 프론트엔드 연동

`assets/js/supabase-config.js` 또는 배포 환경에서 다음을 설정:

```javascript
window.DXF_ANALYZE_API_URL = 'https://your-api-domain.com/analyze-dxf';
```

로컬 개발 시:

```javascript
window.DXF_ANALYZE_API_URL = 'http://localhost:8000/analyze-dxf';
```

## 배포

- **Railway / Render / Fly.io**: `main.py`를 엔트리포인트로 사용
- **Docker** 예시:

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY main.py .
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

## 참고

- DWG 파일은 지원하지 않습니다. AutoCAD에서 DXF로 저장 후 업로드하세요.
- 절단 길이: LINE, ARC, CIRCLE, LWPOLYLINE, POLYLINE, SPLINE 합산
- 타공(piercing): CIRCLE 및 폐쇄 LWPOLYLINE/POLYLINE 개수
