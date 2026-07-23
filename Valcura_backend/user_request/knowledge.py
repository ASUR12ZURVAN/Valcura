KNOWLEDGE_BASE = [
    {
        "title": "Doctor timings",
        "keywords": ["doctor", "timing", "hours", "availability", "schedule"],
        "answer": "Doctors are available from 9:00 AM to 5:00 PM, Monday to Saturday. Emergency services are available 24/7.",
    },
    {
        "title": "Departments",
        "keywords": ["department", "specialty", "cardiology", "pediatrics", "general medicine"],
        "answer": "Available departments include General Medicine, Cardiology, Pediatrics, Orthopedics, Dermatology, and Emergency Care.",
    },
    {
        "title": "Insurance accepted",
        "keywords": ["insurance", "claim", "cover", "policy", "plans"],
        "answer": "We accept major health insurance providers, including private plans and corporate insurance coverage. Please confirm your provider at the reception desk.",
    },
    {
        "title": "Hospital policies",
        "keywords": ["policy", "cancellation", "appointment", "refund", "hospital rules"],
        "answer": "Appointments may be rescheduled 24 hours in advance. Same-day cancellations are subject to policy review. Please follow hygiene and queue guidelines.",
    },
    {
        "title": "Medicine instructions",
        "keywords": ["medicine", "medication", "dosage", "instruction", "tablet", "prescription"],
        "answer": "Please take medicines exactly as prescribed by the doctor. Follow the timing and dosage instructions on the prescription label.",
    },
    {
        "title": "Reports",
        "keywords": ["report", "lab", "test", "result", "reports"],
        "answer": "Lab and diagnostic reports are usually available within 24 to 48 hours. The reception desk can help deliver or explain the results.",
    },
    {
        "title": "FAQs",
        "keywords": ["faq", "help", "support", "question", "how"],
        "answer": "For general support, contact the reception desk or use the WhatsApp assistant to request help with appointment, reports, or follow-up questions.",
    },
]


def retrieve_context(question: str) -> str:
    question_lower = question.lower()
    scored_docs = []

    for item in KNOWLEDGE_BASE:
        score = sum(1 for keyword in item["keywords"] if keyword in question_lower)
        if score:
            scored_docs.append((score, item["answer"]))

    if not scored_docs:
        return "No matching structured info was found. Please ask about doctor timings, departments, accepted insurance, policies, medicine instructions, reports, or FAQs."

    scored_docs.sort(key=lambda entry: entry[0], reverse=True)
    return "\n".join(answer for _, answer in scored_docs[:3])
