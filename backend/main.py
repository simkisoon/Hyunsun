"""
판금 가공 견적 - DXF 파일 분석 API
quote.html 폼에서 DXF 업로드 시 절단 길이·타공 수를 계산하여 반환합니다.
"""
import math
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="DXF 견적 분석 API", version="1.0")

# CORS: 프론트엔드(quote.html)에서 호출 가능하도록 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 프로덕션에서는 특정 도메인으로 제한 권장
    allow_credentials=True,
    allow_methods=["POST", "OPTIONS"],
    allow_headers=["*"],
)


def calc_line_length(entity):
    """LINE 엔티티 길이"""
    try:
        start = entity.dxf.start
        end = entity.dxf.end
        return ((end.x - start.x) ** 2 + (end.y - start.y) ** 2) ** 0.5
    except Exception:
        return 0


def calc_arc_length(entity):
    """ARC 엔티티 호 길이 (ezdxf angles는 degree)"""
    try:
        r = entity.dxf.radius
        start_angle = entity.dxf.start_angle
        end_angle = entity.dxf.end_angle
        angle = abs(end_angle - start_angle)
        if angle > 360:
            angle = angle % 360
        return r * math.radians(angle)
    except Exception:
        return 0


def calc_circle_length(entity):
    """CIRCLE 엔티티 둘레"""
    try:
        return 2 * math.pi * entity.dxf.radius
    except Exception:
        return 0


def calc_lwpolyline_length(entity):
    """LWPOLYLINE 길이 (직선·호 세그먼트 합산)"""
    try:
        length = 0
        points = list(entity.get_points())
        if len(points) < 2:
            return 0
        for i in range(len(points) - 1):
            p0, p1 = points[i], points[i + 1]
            start = (p0[0], p0[1])
            end = (p1[0], p1[1])
            length += ((end[0] - start[0]) ** 2 + (end[1] - start[1]) ** 2) ** 0.5
        if entity.closed:
            p0, p1 = points[-1], points[0]
            length += ((p1[0] - p0[0]) ** 2 + (p1[1] - p0[1]) ** 2) ** 0.5
        return length
    except Exception:
        return 0


def calc_polyline_length(entity):
    """POLYLINE 길이"""
    try:
        length = 0
        for v in entity.vertices:
            length += 0  # vertices는 점만 있음, 실제로는 다음 꼭짓점과의 거리
        # ezdxf POLYLINE은 vertices를 순회하며 각 segment 계산
        vertices = list(entity.vertices)
        if len(vertices) < 2:
            return 0
        for i in range(len(vertices) - 1):
            v0, v1 = vertices[i], vertices[i + 1]
            try:
                p0 = v0.dxf.location
                p1 = v1.dxf.location
                length += ((p1.x - p0.x) ** 2 + (p1.y - p0.y) ** 2) ** 0.5
            except Exception:
                pass
        if entity.is_closed and len(vertices) >= 2:
            p0 = vertices[-1].dxf.location
            p1 = vertices[0].dxf.location
            length += ((p1.x - p0.x) ** 2 + (p1.y - p0.y) ** 2) ** 0.5
        return length
    except Exception:
        return 0


def is_closed_loop(entity):
    """폐쇄 루프(타공) 여부"""
    if entity.dxftype() == "CIRCLE":
        return True
    if entity.dxftype() == "LWPOLYLINE" and getattr(entity, "closed", False):
        return True
    if entity.dxftype() == "POLYLINE" and getattr(entity, "is_closed", False):
        return True
    if entity.dxftype() == "ELLIPSE":
        try:
            if getattr(entity.dxf, "start_param", 0) == 0 and getattr(entity.dxf, "end_param", 0) >= 2 * math.pi - 0.01:
                return True
        except Exception:
            pass
    return False


@app.post("/analyze-dxf")
async def analyze_dxf(file: UploadFile = File(...)):
    """
    DXF 파일을 업로드하면 절단 길이(mm)와 타공 횟수를 반환합니다.
    """
    if not file.filename:
        raise HTTPException(status_code=400, detail="파일이 없습니다.")
    ext = file.filename.lower().split(".")[-1] if "." in file.filename else ""
    if ext not in ("dxf",):
        raise HTTPException(
            status_code=400,
            detail="DXF 파일만 지원합니다. DWG는 AutoCAD에서 DXF로 저장 후 업로드해 주세요.",
        )

    content = await file.read()
    if len(content) == 0:
        raise HTTPException(status_code=400, detail="빈 파일입니다.")

    try:
        import ezdxf
        doc = ezdxf.readbytes(content)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"DXF 파싱 오류: {str(e)}")

    msp = doc.modelspace()
    total_length = 0.0
    piercing_count = 0

    for entity in msp:
        try:
            t = entity.dxftype()
            if t == "LINE":
                total_length += calc_line_length(entity)
            elif t == "ARC":
                total_length += calc_arc_length(entity)
            elif t == "CIRCLE":
                total_length += calc_circle_length(entity)
                piercing_count += 1
            elif t == "LWPOLYLINE":
                total_length += calc_lwpolyline_length(entity)
                if is_closed_loop(entity):
                    piercing_count += 1
            elif t == "POLYLINE":
                total_length += calc_polyline_length(entity)
                if is_closed_loop(entity):
                    piercing_count += 1
            elif t == "SPLINE":
                try:
                    bezier = entity.flattening(0.01)
                    for i in range(len(bezier) - 1):
                        p0, p1 = bezier[i], bezier[i + 1]
                        total_length += ((p1[0] - p0[0]) ** 2 + (p1[1] - p0[1]) ** 2) ** 0.5
                except Exception:
                    pass
        except Exception:
            continue

    return {
        "length": round(total_length, 2),
        "piercing": piercing_count,
        "area": 0,
    }


@app.get("/health")
async def health():
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
