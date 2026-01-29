# mock in-memory DB
appointments_db = {
    "001": {
        "patient": "Rahul Sharma",
        "date": "2026-02-01",
        "time": "09:30",
        "department": "cardiology",
        "status": "confirmed",
    },
    "002": {
        "patient": "Priya Verma",
        "date": "2026-02-01",
        "time": "10:15",
        "department": "dermatology",
        "status": "confirmed",
    },
    "003": {
        "patient": "Amit Patel",
        "date": "2026-02-01",
        "time": "11:00",
        "department": "orthopedics",
        "status": "confirmed",
    },
    "004": {
        "patient": "Neha Iyer",
        "date": "2026-02-01",
        "time": "12:30",
        "department": "neurology",
        "status": "confirmed",
    },
    "005": {
        "patient": "Suresh Reddy",
        "date": "2026-02-02",
        "time": "09:00",
        "department": "gm",
        "status": "confirmed",
    },
    "006": {
        "patient": "Ananya Chatterjee",
        "date": "2026-02-02",
        "time": "10:45",
        "department": "gm",
        "status": "confirmed",
    },
    "007": {
        "patient": "Vikram Singh",
        "date": "2026-02-02",
        "time": "11:30",
        "department": "ent",
        "status": "confirmed",
    },
    "008": {
        "patient": "Pooja Mehta",
        "date": "2026-02-02",
        "time": "14:00",
        "department": "neurology",
        "status": "confirmed",
    },
    "009": {
        "patient": "Arjun Malhotra",
        "date": "2026-02-03",
        "time": "09:15",
        "department": "urology",
        "status": "confirmed",
    },
    "010": {
        "patient": "Kavita Joshi",
        "date": "2026-02-03",
        "time": "10:00",
        "department": "cardiology",
        "status": "confirmed",
    },
}

# doctors
doctors_db = {
    "D001": {"name": "Dr. Rakesh Menon", "department": "cardiology"},
    "D002": {"name": "Dr. Sneha Kulkarni", "department": "dermatology"},
    "D003": {"name": "Dr. Ajay Rao", "department": "orthopedics"},
    "D004": {"name": "Dr. Rohith Sharma", "department": "urology"},
    "D005": {"name": "Dr. Shreyas Babu", "department": "ent"},
    "D006": {"name": "Dr. Arun Kumar", "department": "neurology"},
    "D007": {"name": "Dr. Surya Kumar", "department": "gm"},
    "D008": {"name": "Dr. Rajesh", "department": "cardiology"},
}

# department → doctors
department_index = {
    "cardiology": ["D001", "D008"],
    "dermatology": ["D002"],
    "orthopedics": ["D003"],
    "urology": ["D004"],
    "neurology": ["D006"],
    "gm": ["D007"],
    "ent": ["D005"],
}

doctor_availability_db = {
    "D001": {
        "01-01-2026": ["09:00 AM", "09:30 AM", "10:00 AM", "11:30 AM", "01:00 PM", "04:30 PM"],
        "02-01-2026": ["08:00 AM", "10:00 AM", "10:30 AM", "12:00 PM", "01:00 PM", "02:30 PM"],
    },
    "D002": {
        "01-01-2026": ["10:00 AM", "10:30 AM", "11:00 AM", "02:00 PM", "03:30 PM"] 
    },
    "D003": {
        "02-01-2026": ["09:00 AM", "09:30 AM", "10:00 AM", "11:00 AM", "12:30 PM"],
        "03-01-2026": ["02:00 PM", "02:30 PM"],
        "04-01-2026": ["09:00 AM", "10:30 AM", "01:00 PM"],
    },
    "D004": {
        "01-01-2026": ["08:30 AM"],
        "03-01-2026": ["11:00 AM", "11:30 AM"],
    },
    "D005": {
        "02-01-2026": ["10:00 AM", "10:30 AM", "11:00 AM", "11:30 AM", "12:00 PM"],
    },
    "D006": {
        "01-01-2026": ["08:00 AM", "09:00 AM", "10:00 AM", "11:00 AM"],
        "02-01-2026": ["01:00 PM", "02:00 PM", "03:00 PM"],
        "03-01-2026": ["09:30 AM", "10:30 AM", "11:30 AM", "12:30 PM"],
    },
    "D007": {
        "01-01-2026": ["09:00 AM"],
    },
    "D008": {
        "02-01-2026": ["09:00 AM", "09:30 AM", "10:00 AM", "10:30 AM", "11:00 AM", "11:30 AM"],
        "03-01-2026": ["01:00 PM", "01:30 PM", "02:00 PM"],
        "05-01-2026": ["09:00 AM", "10:00 AM"],
    },
}
# doctor availability
