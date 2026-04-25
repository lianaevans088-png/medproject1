from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="ClinFlow AI Backend", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def healthcheck():
    return {
        "status": "ok",
        "service": "ClinFlow AI Backend",
        "message": "Backend is running"
    }


@app.get("/patients")
def get_patients():
    return [
        {
            "id": 1,
            "full_name": "Иванов Иван Иванович",
            "birth_date": "1985-04-12",
            "summary": "Демо-пациент для MVP"
        }
    ]


@app.post("/ai/demo-visit")
def demo_visit():
    return {
        "transcript": "Пациент жалуется на кашель, температуру до 38.2, слабость в течение трех дней. Одышки нет. Аллергии отрицает.",
        "ai_draft": {
            "complaints": "Кашель, температура до 38.2, слабость.",
            "anamnesis": "Симптомы около трех дней. Одышки нет. Аллергии отрицает.",
            "objective_status": "Требует внесения врачом после осмотра.",
            "assessment": "AI-черновик. Возможны признаки острого респираторного заболевания.",
            "plan": "Осмотр, контроль состояния, рекомендации врача."
        },
        "icd10_suggestions": [
            {
                "code": "J06.9",
                "title": "Острая инфекция верхних дыхательных путей неуточненная",
                "note": "Черновая подсказка. Требует проверки врачом."
            }
        ],
        "patient_instruction": "Соблюдайте рекомендации врача, контролируйте температуру. При ухудшении обратитесь за медицинской помощью.",
        "human_review_required": True
    }
