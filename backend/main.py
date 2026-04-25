import os
from datetime import datetime
from typing import Optional, List

from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy import (
    create_engine,
    Column,
    Integer,
    String,
    Text,
    Boolean,
    DateTime,
    ForeignKey,
)
from sqlalchemy.orm import declarative_base, sessionmaker, Session, relationship


DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL is not set")

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
Base = declarative_base()


class Patient(Base):
    __tablename__ = "patients"

    id = Column(Integer, primary_key=True, index=True)
    full_name = Column(String, index=True)
    birth_date = Column(String)
    phone = Column(String, nullable=True)
    summary = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    visits = relationship("Visit", back_populates="patient")


class Visit(Base):
    __tablename__ = "visits"

    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(Integer, ForeignKey("patients.id"))
    reason = Column(Text, nullable=True)
    transcript = Column(Text, nullable=True)
    ai_draft = Column(Text, nullable=True)
    icd10_code = Column(String, nullable=True)
    icd10_title = Column(String, nullable=True)
    patient_instruction = Column(Text, nullable=True)
    approved = Column(Boolean, default=False)
    status = Column(String, default="draft")
    created_at = Column(DateTime, default=datetime.utcnow)

    patient = relationship("Patient", back_populates="visits")


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    entity_type = Column(String)
    entity_id = Column(Integer)
    action = Column(String)
    details = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


Base.metadata.create_all(bind=engine)


app = FastAPI(title="ClinFlow AI Backend", version="0.2.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


class PatientCreate(BaseModel):
    full_name: str
    birth_date: str
    phone: Optional[str] = None
    summary: Optional[str] = None


class VisitCreate(BaseModel):
    patient_id: int
    reason: Optional[str] = None


class ApproveVisitPayload(BaseModel):
    approved_by: Optional[str] = "demo_doctor"


@app.get("/")
def healthcheck():
    return {
        "status": "ok",
        "service": "ClinFlow AI Backend",
        "version": "0.2.0",
        "database": "connected",
        "message": "Backend with PostgreSQL is running",
    }


@app.post("/seed")
def seed_demo_data(db: Session = Depends(get_db)):
    existing = db.query(Patient).filter(Patient.full_name == "Иванов Иван Иванович").first()

    if existing:
        return {
            "message": "Demo patient already exists",
            "patient_id": existing.id,
        }

    patient = Patient(
        full_name="Иванов Иван Иванович",
        birth_date="1985-04-12",
        phone="+79990000000",
        summary="Демо-пациент для MVP. Жалобы: кашель, температура, слабость.",
    )

    db.add(patient)
    db.commit()
    db.refresh(patient)

    audit = AuditLog(
        entity_type="patient",
        entity_id=patient.id,
        action="seed_demo_patient",
        details="Created demo patient",
    )
    db.add(audit)
    db.commit()

    return {
        "message": "Demo patient created",
        "patient": patient,
    }


@app.get("/patients")
def get_patients(db: Session = Depends(get_db)):
    patients = db.query(Patient).order_by(Patient.id.desc()).all()
    return patients


@app.post("/patients")
def create_patient(payload: PatientCreate, db: Session = Depends(get_db)):
    patient = Patient(
        full_name=payload.full_name,
        birth_date=payload.birth_date,
        phone=payload.phone,
        summary=payload.summary,
    )

    db.add(patient)
    db.commit()
    db.refresh(patient)

    audit = AuditLog(
        entity_type="patient",
        entity_id=patient.id,
        action="create_patient",
        details=f"Created patient {patient.full_name}",
    )
    db.add(audit)
    db.commit()

    return patient


@app.get("/patients/{patient_id}")
def get_patient(patient_id: int, db: Session = Depends(get_db)):
    patient = db.query(Patient).filter(Patient.id == patient_id).first()

    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")

    return patient


@app.post("/visits")
def create_visit(payload: VisitCreate, db: Session = Depends(get_db)):
    patient = db.query(Patient).filter(Patient.id == payload.patient_id).first()

    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")

    visit = Visit(
        patient_id=payload.patient_id,
        reason=payload.reason or "Демо-прием",
        status="created",
    )

    db.add(visit)
    db.commit()
    db.refresh(visit)

    audit = AuditLog(
        entity_type="visit",
        entity_id=visit.id,
        action="create_visit",
        details=f"Created visit for patient_id={payload.patient_id}",
    )
    db.add(audit)
    db.commit()

    return visit


@app.get("/visits")
def get_visits(db: Session = Depends(get_db)):
    visits = db.query(Visit).order_by(Visit.id.desc()).all()
    return visits


@app.post("/ai/demo-visit")
def demo_visit(db: Session = Depends(get_db)):
    patient = db.query(Patient).filter(Patient.full_name == "Иванов Иван Иванович").first()

    if not patient:
        patient = Patient(
            full_name="Иванов Иван Иванович",
            birth_date="1985-04-12",
            phone="+79990000000",
            summary="Демо-пациент для MVP. Жалобы: кашель, температура, слабость.",
        )
        db.add(patient)
        db.commit()
        db.refresh(patient)

    transcript = (
        "Пациент жалуется на кашель, температуру до 38.2, слабость в течение трех дней. "
        "Отмечает боль в горле. Одышки нет. Аллергии отрицает."
    )

    ai_draft = {
        "complaints": "Кашель, температура до 38.2, слабость, боль в горле.",
        "anamnesis": "Симптомы около трех дней. Одышки нет. Аллергии отрицает.",
        "objective_status": "Требует внесения врачом после осмотра.",
        "assessment": "AI-черновик. Возможны признаки острого респираторного заболевания.",
        "plan": "Осмотр, контроль состояния, рекомендации врача.",
    }

    icd10_code = "J06.9"
    icd10_title = "Острая инфекция верхних дыхательных путей неуточненная"

    patient_instruction = (
        "Соблюдайте рекомендации врача, контролируйте температуру, пейте достаточно жидкости. "
        "При ухудшении состояния обратитесь за медицинской помощью."
    )

    visit = Visit(
        patient_id=patient.id,
        reason="Кашель, температура, слабость",
        transcript=transcript,
        ai_draft=str(ai_draft),
        icd10_code=icd10_code,
        icd10_title=icd10_title,
        patient_instruction=patient_instruction,
        approved=False,
        status="ai_draft",
    )

    db.add(visit)
    db.commit()
    db.refresh(visit)

    audit = AuditLog(
        entity_type="visit",
        entity_id=visit.id,
        action="generate_ai_demo_visit",
        details="Generated AI demo visit draft",
    )
    db.add(audit)
    db.commit()

    return {
        "visit_id": visit.id,
        "patient": {
            "id": patient.id,
            "full_name": patient.full_name,
            "birth_date": patient.birth_date,
            "summary": patient.summary,
        },
        "transcript": transcript,
        "ai_draft": ai_draft,
        "icd10_suggestions": [
            {
                "code": icd10_code,
                "title": icd10_title,
                "note": "Черновая подсказка. Требует проверки врачом.",
            }
        ],
        "patient_instruction": patient_instruction,
        "human_review_required": True,
        "status": "ai_draft_saved_to_database",
    }


@app.post("/visits/{visit_id}/approve")
def approve_visit(
    visit_id: int,
    payload: ApproveVisitPayload,
    db: Session = Depends(get_db),
):
    visit = db.query(Visit).filter(Visit.id == visit_id).first()

    if not visit:
        raise HTTPException(status_code=404, detail="Visit not found")

    visit.approved = True
    visit.status = "approved_by_doctor"
    db.commit()
    db.refresh(visit)

    audit = AuditLog(
        entity_type="visit",
        entity_id=visit.id,
        action="approve_visit",
        details=f"Approved by {payload.approved_by}",
    )
    db.add(audit)
    db.commit()

    return {
        "visit_id": visit.id,
        "approved": visit.approved,
        "status": visit.status,
        "message": "Финальная версия утверждена врачом",
    }


@app.get("/audit-logs")
def get_audit_logs(db: Session = Depends(get_db)):
    logs = db.query(AuditLog).order_by(AuditLog.id.desc()).limit(50).all()
    return logs
