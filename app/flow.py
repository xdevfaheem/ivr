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
                f"ID: {doc_id}\nName: {doc['name']}\nDate: {date}\nTime: {', '.join(day_slots) or 'No slots'}"
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
    name="get_doctor_availability",
    description="Get doctor(s) of a department and their availability (date and time slots)",
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


async def check_appointment_status(args: FlowArgs):
    appt_id = args["appointment_id"]
    if appt_id in appointments_db:
        appt = appointments_db[appt_id]
        return f"Patient: {appt['patient']}, Doctor ID: {appt['doctor_id']}, Date: {appt['date']}, Time: {appt['time']}, Status: {appt['status']}"

    return "Appointment not found."


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

Be professional but friendly. Have a natural and conversational with the user in the same language they are speaking in. You can use english or other language words strictly when necessary for clarity and correctness.

Your responses will be converted to speech. Write output that is easy to speak and easy to listen to.
Do not use emojis, markdown, bullet points, asterisks, or any non-verbal symbols.
Use standard punctuation such as full stops and commas to ensure clear and natural speech.

NOTE: When asking for information, don't ask all the details in one go, ask them one-by-one whatever you need.
And more importantly, indicate the user whatever you are going to do (i.e., check doctor's availability, booking the appointment, etc) before doing it (calling a function), this is very important, to let them know what's happening behind and also make sure to confirm all the details before taking an action.

FYI Remember, Todays's Date is `01-02-2026 (DD-MM-YYYY)`
""",
            }
        ],
        "task_messages": [
            {
                "role": "system",
                "content": "Listen to the user and choose the correct action.",  # "Greet the patient and ask what they'd like to do: book, cancel, reschedule or check appointment status."
            }
        ],
        "functions": [handle_indent_func_schema],
        "respond_immediately": False,
    }


def create_book_node() -> NodeConfig:
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
                "description": "Appointment date (in DD-MM-YYYY format)",
            },
            "time": {
                "type": "string",
                "description": "Appointment time (in HH:MM format)",
            },
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
                "content": "Converse with the patient and first collect necessary details, like name, department and the date they want appointment on, right after that, check for doctors availability on that department (using `get_doctor_availability` function), let them know the doctor's availability, after agreeing on time slot, confirm all details, book the appointment and finally let them know the appointment ID.",
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
        description="Cancel an appointment with its ID",
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
    async def get_appointment_status(args: FlowArgs, flow_manager: FlowManager):
        response = await check_appointment_status(args)
        return response, None

    appointment_status_func_schema = FlowsFunctionSchema(
        name="get_appointment_status",
        description="Get all the information about the appointment",
        properties={"appointment_id": {"type": "string"}},
        required=["appointment_id"],
        handler=get_appointment_status,
    )

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
                "content": "First get the appointment ID from the user, use it with `get_appointment_status` function to get the appointment status, then get the new date or time or both, from the user, and check the availability of the doctor on that date/time using `get_doctors_availability` function, after agreeing on time slots, confirm all the detail and reschedule their appointment.",
            }
        ],
        "functions": [
            appointment_status_func_schema,
            doctor_availability_func_schema,
            reschedule_func_schema,
        ],
    }


def create_appointment_status_node() -> NodeConfig:
    async def handle_appointment_status(args: FlowArgs, flow_manager: FlowManager):
        response = await check_appointment_status(args)
        return response, create_main_menu_node()

    appointment_status_func_schema = FlowsFunctionSchema(
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
        "functions": [appointment_status_func_schema],
    }


def create_main_menu_node() -> NodeConfig:
    return {
        "name": "follow-up",
        "task_messages": [
            {
                "role": "system",
                "content": "Ask the user what'd they like to do next or like, is there anything to help with, then just choose the appropriate action, strictly with no follow up.",
            }
        ],
        "functions": [handle_indent_func_schema],
    }


def create_end_node() -> NodeConfig:
    return {
        "name": "end",
        "task_messages": [{"role": "system", "content": "Thank them and say goodbye."}],
        "post_actions": [{"type": "end_conversation"}],
    }
