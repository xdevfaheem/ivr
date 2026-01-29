from db import appointments_db, department_index, doctor_availability_db, doctors_db
from pipecat_flows import FlowArgs, FlowManager, FlowsFunctionSchema, NodeConfig


# indent handler
async def handle_indent(args: FlowArgs, flow_manager: FlowManager):
    action = args["action"]
    if action == "book":
        return None, create_book_node()
    elif action == "cancel":
        return None, create_cancel_node()
    elif action == "reschedule":
        return None, create_reschedule_node()
    elif action == "check_appointment_status":
        return None, create_appointment_status_node()
    return None, create_end_node()


handle_indent_func_schema = FlowsFunctionSchema(
    name="select_action",
    description="Selects an action based on the user intent",
    properties={
        "action": {
            "type": "string",
            "enum": [
                "book",
                "cancel",
                "reschedule",
                "check_appointment_status",
                "end",
            ],
        }
    },
    required=["action"],
    handler=handle_indent,
)


def create_initial_node() -> NodeConfig:
    return {
        "name": "greeting",
        "role_messages": [
            {
                "role": "system",
                "content": """You are a helpful hospital appointment assistant, who help patients:
- Book new appointments
- Cancel existing appointments
- Reschedule existing appointments 
- Check appointment status 

Be professional but friendly. Keep your responses natural, breif and conversational, in the **same** language as the user. Use other languages only when strictly necessary for clarity or correctness.

Your responses will be converted to speech. Write output that is easy to speak and easy to listen to.
Do not use emojis, markdown, bullet points, asterisks, or any non-verbal symbols.
Use standard punctuation such as full stops and commas to ensure clear and natural speech.

And finally, make sure to confirm all the details before taking an action.""",
            }
        ],
        "task_messages": [
            {
                "role": "system",
                "content": "Greet the patient and ask what they'd like to do: book, cancel, reschedule or check appointment status.",
            }
        ],
        "functions": [handle_indent_func_schema],
    }


def create_book_node() -> NodeConfig:
    async def get_doctors_availability(args: FlowArgs, flow_manager: FlowManager):
        department = args["department"].lower()
        date = args.get("date")

        doctors = department_index.get(department)
        if not doctors:
            return "No doctors found for this department.", None

        response = []
        for doc_id in doctors:
            doc = doctors_db[doc_id]
            slots = doctor_availability_db.get(doc_id, {})
            if date:
                day_slots = slots.get(date, [])
                response.append(
                    f"ID: {doc_id}\nName: {doc['name']}\Date: {date}\Time: {', '.join(day_slots) or 'No slots'}"
                )
            else:
                # iterate slots.items() and ensure safe joins
                date_with_time = []
                for d, times in slots.items():
                    times = times or []
                    date_with_time.append(
                        f"Date: {d}\nTime: {', '.join(times) or 'No slots'}"
                    )
                response.append(
                    "ID: {}\nName: {}\nAvailability:\n\n{}".format(
                        doc_id, doc["name"], "\n".join(date_with_time)
                    )
                )
        return "\n---\n".join(response), None

    doctor_availability_func_schema = FlowsFunctionSchema(
        name="doctor_availability_status",
        description="Get doctor(s) of a department and their availability",
        properties={
            "department": {
                "type": "string",
                "enum": [
                    "cardiology",
                    "dermatology",
                    "orthopedics",
                    "urology",
                    "neurology",
                    "ent",
                    "gm",
                ],
                "description": "Department the patient belongs to",
            },
            "date": {
                "type": "string",
                "description": "Date to check if provided, in DD-MM-YYYY format",
            },
        },
        required=["department"],
        handler=get_doctors_availability,
    )

    async def handle_book_appointment(args: FlowArgs, flow_manager: FlowManager):
        appt_id = str(len(appointments_db) + 1).zfill(3)

        doctor_id, date, time = args["doctor_id"], args["date"], args["time"]
        # remove slot
        try:
            doctor_availability_db[doctor_id][date].remove(time)
        except Exception:
            pass  # pass as their maight be differnce in string handling

        appointments_db[appt_id] = {
            "patient": args["patient_name"],
            "date": args["date"],
            "time": args["time"],
            "department": args["department"],
            "doctor_id": args["doctor_id"],
            "status": "confirmed",
        }

        return f"Appointment booked. ID: {appt_id}", create_main_menu_node()

    handle_booking_func_schema = FlowsFunctionSchema(
        name="book_appointment",
        description="Book a new appointment",
        properties={
            "patient_name": {
                "type": "string",
                "description": "The name of the patient",
            },
            "date": {
                "type": "string",
                "description": "Appointment date in DD-MM-YYYY format",
            },
            "time": {"type": "string", "description": "Appointment time in HH:MM time"},
            "department": {
                "type": "string",
                "enum": [
                    "cardiology",
                    "dermatology",
                    "orthopedics",
                    "urology",
                    "neurology",
                    "ent",
                    "gm",
                ],
                "description": "Department the patient belongs to",
            },
            "doctor_id": {"type": "string", "description": "ID of the doctor to book"},
        },
        required=["patient_name", "date", "time", "department"],
        handler=handle_book_appointment,
    )

    return {
        "name": "book",
        "task_messages": [
            {
                "role": "system",
                "content": "Converse with the patient and first collect necessary details like name, department and the date they want appointment on, then check for doctors availability on that department (via `doctor_availability_status` function), after agreeing on time slot, confirm all details, book the appointment and finally let them know the appointment ID very clearly.",
            }
        ],
        "functions": [doctor_availability_func_schema, handle_booking_func_schema],
    }


def create_cancel_node() -> NodeConfig:
    async def handle_cancel_appointment(args: FlowArgs, flow_manager: FlowManager):
        appt_id = args["appointment_id"]
        if appt_id in appointments_db:
            appointments_db[appt_id]["status"] = "cancelled"
            return "Appointment cancelled successfully.", create_main_menu_node()
        return "Appointment not found.", create_main_menu_node()

    cancel_func_schema = FlowsFunctionSchema(
        name="cancel_appointment",
        description="Cancel an appointment",
        properties={"appointment_id": {"type": "string"}},
        required=["appointment_id"],
        handler=handle_cancel_appointment,
    )

    return {
        "name": "cancel",
        "task_messages": [
            {
                "role": "system",
                "content": "Ask for the appointment ID and cancel that appointment.",
            }
        ],
        "functions": [cancel_func_schema],
    }


def create_reschedule_node() -> NodeConfig:
    async def handle_reschedule(args: FlowArgs, flow_manager: FlowManager):
        appt_id = args["appointment_id"]
        if appt_id in appointments_db:
            appointments_db[appt_id]["date"] = args["new_date"]
            appointments_db[appt_id]["time"] = args["new_time"]
            return "Appointment rescheduled.", create_main_menu_node()
        return "Appointment not found.", create_main_menu_node()

    reschedule_func_schema = FlowsFunctionSchema(
        name="reschedule_appointment",
        description="Reschedule an existing appointment to a new date/time",
        properties={
            "appointment_id": {
                "type": "string",
                "description": "Exisiting appointment ID",
            },
            "new_date": {
                "type": "string",
                "description": "New appointment date in DD-MM-YYYY format",
            },
            "new_time": {
                "type": "string",
                "description": "New appointment time in HH:MM time",
            },
        },
        required=["appointment_id", "new_date", "new_time"],
        handler=handle_reschedule,
    )
    return {
        "name": "reschedule",
        "task_messages": [
            {
                "role": "system",
                "content": "Converse with the patient and collect the necessary information and reschedule their appointment.",
            }
        ],
        "functions": [reschedule_func_schema],
    }


def create_appointment_status_node() -> NodeConfig:
    async def handle_appointment_status(args: FlowArgs, flow_manager: FlowManager):
        appt_id = args["appointment_id"]
        if appt_id in appointments_db:
            appt = appointments_db[appt_id]
            return (
                f"Patient: {appt['patient']}, Doctor: {appt['doctor']}, Date: {appt['date']}, Time: {appt['time']}, Status: {appt['status']}",
                create_main_menu_node(),
            )
        return "Appointment not found.", create_main_menu_node()

    check_status_func_schema = FlowsFunctionSchema(
        name="check_appointment_status",
        description="Check the appointment's status",
        properties={"appointment_id": {"type": "string"}},
        required=["appointment_id"],
        handler=handle_appointment_status,
    )
    return {
        "name": "status",
        "task_messages": [
            {
                "role": "system",
                "content": "Ask for the appointment ID and check its status.",
            }
        ],
        "functions": [check_status_func_schema],
    }


def create_main_menu_node() -> NodeConfig:
    return {
        "name": "follow-up",
        "task_messages": [
            {
                "role": "system",
                "content": "Chat and follow up with the user and ask them what'd they like to do next or like, is there anything to help with",
            }
        ],
        "functions": [handle_indent_func_schema],
    }


def create_end_node() -> NodeConfig:
    return {
        "name": "end",
        "task_messages": [
            {"role": "system", "content": "Thank & wish them and say goodbye."}
        ],
        "post_actions": [{"type": "end_conversation"}],
    }
