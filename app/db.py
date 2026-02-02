# mock in-memory DB
appointments_db = {}

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
        "01-02-2026": ["09:00 AM", "09:30 AM", "10:00 AM", "11:30 AM", "01:00 PM", "04:30 PM"],
        "02-0222026": ["08:00 AM", "10:00 AM", "10:30 AM", "12:00 PM", "01:00 PM", "02:30 PM"],
    },
    "D002": {
        "01-02-2026": ["10:00 AM", "10:30 AM", "11:00 AM", "02:00 PM", "03:30 PM"] 
    },
    "D003": {
        "02-02-2026": ["09:00 AM", "09:30 AM", "10:00 AM", "11:00 AM", "12:30 PM"],
        "03-02-2026": ["02:00 PM", "02:30 PM"],
        "04-02-2026": ["09:00 AM", "10:30 AM", "01:00 PM"],
    },
    "D004": {
        "01-02-2026": ["08:30 AM"],
        "03-02-2026": ["11:00 AM", "11:30 AM"],
    },
    "D005": {
        "02-02-2026": ["10:00 AM", "10:30 AM", "11:00 AM", "11:30 AM", "12:00 PM"],
    },
    "D006": {
        "01-02-2026": ["08:00 AM", "09:00 AM", "10:00 AM", "11:00 AM"],
        "02-02-2026": ["01:00 PM", "02:00 PM", "03:00 PM"],
        "03-02-2026": ["09:30 AM", "10:30 AM", "11:30 AM", "12:30 PM"],
    },
    "D007": {
        "01-02-2026": ["09:00 AM"],
    },
    "D008": {
        "02-02-2026": ["09:00 AM", "09:30 AM", "10:00 AM", "10:30 AM", "11:00 AM", "11:30 AM"],
        "03-02-2026": ["01:00 PM", "01:30 PM", "02:00 PM"],
        "05-02-2026": ["09:00 AM", "10:00 AM"],
    },
}
# doctor availability
