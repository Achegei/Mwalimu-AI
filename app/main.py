from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.core.database import engine
from app.routes.admin import router as admin_router
from app.routes.auth import router as auth_router
from app.routes.student import router as student_router
from app.routes.teacher import router as teacher_router

app = FastAPI(
    title="Mwalimu AI",
    description=(
        "AI-supported learning and teacher analytics platform "
        "for Kenyan secondary schools."
    ),
    version="0.1.0",
)


app.mount(
    "/static",
    StaticFiles(directory="app/static"),
    name="static",
)


templates = Jinja2Templates(
    directory="app/templates",
)


app.include_router(auth_router)
app.include_router(student_router)
app.include_router(teacher_router)
app.include_router(admin_router)


@app.get(
    "/",
    response_class=HTMLResponse,
)
async def home(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="auth/login.html",
        context={},
    )


@app.get(
    "/student/dashboard",
    response_class=HTMLResponse,
)
async def student_dashboard(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="student/dashboard.html",
        context={},
    )


@app.get("/teacher/dashboard", response_class=HTMLResponse)
async def teacher_dashboard(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="teacher/dashboard.html",
        context={},
    )


@app.get("/admin/dashboard", response_class=HTMLResponse)
async def admin_dashboard(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="admin/dashboard.html",
        context={},
    )


@app.get(
    "/student/subjects/{subject_id}",
    response_class=HTMLResponse,
)
async def student_subject(
    request: Request,
    subject_id: int,
):
    return templates.TemplateResponse(
        request=request,
        name="student/subject.html",
        context={
            "subject_id": subject_id,
        },
    )


@app.get(
    "/student/topics/{topic_id}/diagnostic",
    response_class=HTMLResponse,
)
async def student_diagnostic(
    request: Request,
    topic_id: int,
):
    return templates.TemplateResponse(
        request=request,
        name="student/diagnostic.html",
        context={
            "topic_id": topic_id,
        },
    )


@app.get(
    "/student/diagnostic/{attempt_id}/tutor",
    response_class=HTMLResponse,
)
async def student_tutor(
    request: Request,
    attempt_id: int,
):
    return templates.TemplateResponse(
        request=request,
        name="student/tutor.html",
        context={
            "attempt_id": attempt_id,
        },
    )


@app.get(
    "/student/diagnostic/{diagnostic_attempt_id}/practice",
    response_class=HTMLResponse,
)
async def student_practice(
    request: Request,
    diagnostic_attempt_id: int,
):
    return templates.TemplateResponse(
        request=request,
        name="student/practice.html",
        context={
            "diagnostic_attempt_id": diagnostic_attempt_id,
        },
    )


@app.get("/health")
async def health_check():
    database_status = "connected"

    try:
        async with engine.connect() as connection:
            await connection.execute(text("SELECT 1"))
    except SQLAlchemyError:
        database_status = "unavailable"

    return {
        "status": ("healthy" if database_status == "connected" else "degraded"),
        "database": database_status,
    }


@app.get(
    "/teacher/classes/{classroom_id}",
    response_class=HTMLResponse,
)
async def teacher_class_analytics(
    request: Request,
    classroom_id: int,
):
    return templates.TemplateResponse(
        request=request,
        name="teacher/classroom.html",
        context={
            "classroom_id": classroom_id,
        },
    )


@app.get(
    "/teacher/classes/{classroom_id}/students/{student_id}",
    response_class=HTMLResponse,
)
async def teacher_student_progress_page(
    request: Request,
    classroom_id: int,
    student_id: int,
):
    return templates.TemplateResponse(
        request=request,
        name="teacher/student_progress.html",
        context={
            "classroom_id": classroom_id,
            "student_id": student_id,
        },
    )
