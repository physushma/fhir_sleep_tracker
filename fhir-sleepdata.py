from flask import Flask, request, jsonify
import os
import csv
import json
import sqlite3
from fhir.resources.patient import Patient
from fhir.resources.reference import Reference
from fhir.resources.coding import Coding
from fhir.resources.observation import Observation,ObservationComponent
from fhir.resources.identifier import Identifier
from fhir.resources.humanname import HumanName
from fhir.resources.contactpoint import ContactPoint
from fhir.resources.address import Address
from fhir.resources.codeableconcept import CodeableConcept
from fhir.resources.quantity import Quantity
from fhir.resources.bundle import Bundle, BundleEntry, BundleEntryRequest
from datetime import date
from decimal import Decimal
from flask_cors import CORS
from flask import make_response



db_name = "sleep_data.db"
app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})  # Enable CORS for all routes and all origins


# Function to create the Patients table from a CSV file
def create_table_from_csv(db_name, csv_filename):
    conn = sqlite3.connect(db_name)
    cursor = conn.cursor()

    cursor.execute('''CREATE TABLE IF NOT EXISTS Patients (
        Patient_ID INTEGER PRIMARY KEY,
        First_Name TEXT,
        Last_Name TEXT,
        Date_of_Birth DATE,
        Gender TEXT,
        Phone_Number TEXT,
        Email TEXT,
        Address TEXT,
        City TEXT,
        State TEXT,
        Zip_Code TEXT
    )''')

    with open(csv_filename, "r") as csv_file:
        csv_reader = csv.reader(csv_file)
        next(csv_reader)  # Skip the header row
        for row in csv_reader:
            cursor.execute("INSERT INTO Patients VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", row)

    conn.commit()
    conn.close()

    print(f"Table 'Patients' has been created and populated with data from '{csv_filename}'.")

def create_sleep_observations_table(db_name, csv_filename):
    # Connect to SQLite database (creates a new database if it doesn't exist)
    conn = sqlite3.connect(db_name)
    cursor = conn.cursor()

    # Create sleep_observations table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS sleep_observations (
            patient_id INTEGER,
            snoring_rate REAL,
            respiratory_rate REAL,
            body_temperature REAL,
            limb_movement REAL,
            blood_oxygen REAL,
            eye_movement REAL,
            sleeping_hours REAL,
            heart_rate INTEGER,
            stress_level INTEGER,
            observation_date TEXT,
            PRIMARY KEY (patient_id, observation_date)
        )
    ''')

    with open(csv_filename, 'r') as csvfile:
            csvreader = csv.reader(csvfile)
            next(csvreader) 

            for row in csvreader:
                cursor.execute('''
                INSERT INTO sleep_observations (
                    patient_id, snoring_rate, respiratory_rate, body_temperature,
                    limb_movement, blood_oxygen, eye_movement, sleeping_hours,
                    heart_rate, stress_level, observation_date
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', row)
    # Commit changes and close the connection
    conn.commit()
    conn.close()

    print(f"Table 'sleep_observations' has been created and populated with data from '{csv_filename}'.")

# Function to read patient data based on Patient_ID
def read_patient_data(db_name, patient_id):
    conn = sqlite3.connect(db_name)
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM Patients WHERE Patient_ID = ?", (patient_id,))
    patient_data = cursor.fetchone()

    conn.close()

    return patient_data

def get_records_count(table_name):
    with sqlite3.connect(db_name) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM {}".format(table_name))
        count = cursor.fetchone()[0]
        return count

def insert_new_patient(cursor, patient_data):
    with sqlite3.connect(db_name) as conn:
        try:
            cursor = conn.cursor()
            
            query = '''
                INSERT INTO Patients 
                (First_Name, Last_Name, Date_of_Birth, Gender, Phone_Number, Email, Address, City, State, Zip_Code)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            '''

            values = (
                patient_data['First_Name'],
                patient_data['Last_Name'],
                patient_data['Date_of_Birth'],
                patient_data['Gender'],
                patient_data['Phone_Number'],
                patient_data['Email'],
                patient_data['Address'],
                patient_data['City'],
                patient_data['State'],
                patient_data['Zip_Code']
            )

            cursor.execute(query, values)

            complete_insert_statement = query.replace('?', '{}').format(*values)
            print(complete_insert_statement)            

            # Commit changes, no need to close the connection explicitly
            conn.commit()
            print("Data inserted into sleep_observation table.\n")
            print(patient_data)

        except sqlite3.Error as e:
            print(f"Error inserting data: {e}")


def read_patient_sleep_data(db_name, patient_id):
    conn = sqlite3.connect(db_name)
    cursor = conn.cursor()

    cursor.execute(f""" SELECT  * 
                        FROM     (
                            SELECT  *, ROW_NUMBER () OVER (ORDER BY observation_date) AS obs_desc_rnk 
                            FROM  sleep_observations a WHERE  patient_id = ?
                        )a 
                        WHERE body_temperature is not null""", (patient_id,))
    patient_obs_data = cursor.fetchall()

    conn.close()
    # Correct
    return patient_obs_data


def insert_sleep_data(db_name, data_dict):
    with sqlite3.connect(db_name) as conn:
        try:
            cursor = conn.cursor()
            query = '''
                INSERT INTO sleep_observations 
                (patient_id, observation_date, body_temperature, snoring_rate, respiratory_rate, eye_movement, sleeping_hours, heart_rate)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            '''

            values = (
                data_dict['patient_id'],
                data_dict['observation_date'],
                data_dict['body_temperature'],
                data_dict['snoring_rate'],
                data_dict['respiratory_rate'],
                data_dict['eye_movement'],
                data_dict['sleeping_hours'],
                data_dict['heart_rate']
            )
            
            cursor.execute(query, values)

            complete_insert_statement = query.replace('?', '{}').format(*values)
            print(complete_insert_statement)            

            # Commit changes, no need to close the connection explicitly
            conn.commit()
            print("Data inserted into sleep_observation table.\n")
            print(data_dict)

        except sqlite3.Error as e:
            print(f"Error inserting data: {e}")

def delete_observation_data(db_name, patient_id, observation_date):
    conn = sqlite3.connect(db_name)
    cursor = conn.cursor()

    # Delete data from the sleep_observations table based on patient_id and observation_date
    cursor.execute('''
        DELETE FROM sleep_observations
        WHERE patient_id = ? AND observation_date = ?
    ''', (patient_id, observation_date))

    # Commit changes and close the connection
    conn.commit()
    conn.close()

    print('Observation data deleted.')

@app.route('/fhir/add_new_patient', methods=['POST'])
def api_add_new_patient():
    try:
        data = request.get_json()

        # Check if all required fields are present in the request
        required_fields = ['First_Name', 'Last_Name', 'Date_of_Birth', 'Gender', 'Phone_Number', 'Email', 'Address', 'City', 'State', 'Zip_Code']
        if not all(field in data for field in required_fields):
            return jsonify({'error': 'Missing required fields'}), 400

        insert_new_patient(db_name, data)

        return jsonify({'success': True}), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/fhir/insert_sleep_data', methods=['POST'])
def api_insert_sleep_data():
    try:
        data = request.get_json()

        # Check if all required fields are present in the request
        required_fields = ['patient_id', 'observation_date', 'snoring_rate', 'respiratory_rate', 'eye_movement', 'sleeping_hours','heart_rate']
        if not all(field in data for field in required_fields):
            return jsonify({'error': 'Missing required fields'}), 400

        insert_sleep_data(db_name, data)

        return jsonify({'success': True}), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/fhir/delete_patient_obs', methods=['POST'])
def delete_observation_fhir():
    try:
        data = request.get_json()

        # Call the function to delete data
        delete_observation_data(db_name, data['patient_id'], data['observation_date'])
        return jsonify({'success': True}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

class CustomEncoder(json.JSONEncoder):
    def default(self, obj):
        if obj is None:
            return None  # Return null for None values

        if isinstance(obj, Decimal):
            return str(obj)  # Convert Decimal to a string
        elif isinstance(obj, date):
            return obj.isoformat()  # Convert date to ISO format
        return super(CustomEncoder, self).default(obj)

# API route to get patient data by Patient_ID in FHIR format
@app.route('/fhir/patient/<int:patient_id>', methods=['GET'])
def get_patient_data_fhir(patient_id):
    
    patient_data = read_patient_data(db_name, patient_id)

    if patient_data:
        patient = Patient()
        patient.id = str(patient_data[0])
        patient.identifier = [Identifier(use="official", value=str(patient_data[0]))]
        patient.name = [HumanName(use="official", given=[patient_data[1]], family=patient_data[2])]
        patient.birthDate = str(patient_data[3])
        patient.gender = patient_data[4]
        patient.telecom = [ContactPoint(system="phone", value=patient_data[5])]
        patient.telecom.append(ContactPoint(system="email", value=patient_data[6]))
        patient.address = [Address(use="home", line=[patient_data[7]], city=patient_data[8], state=patient_data[9], postalCode=patient_data[10])]

        return patient.dict()

    else:
        return "Patient not found", 404

# API route to get sleep observations by Patient_ID in FHIR format
@app.route('/fhir/sleep-observations/<int:patient_id>', methods=['GET'])
def get_sleep_observations_fhir(patient_id):
    observations = read_patient_sleep_data(db_name, patient_id=patient_id)

    if observations:
        bundle = Bundle(type="searchset")
        bundle.entry = []

        for obs in observations:
            # Define the code for the Observation
            code = CodeableConcept()
            code.coding = [Coding(system="http://loinc.org", code="LOINC_CODE", display="Sleep Observation")]
            code.text = "Sleep Observation"

            # Initialize the Observation object with the required code
            observation = Observation(status="final", code=code)
            reference = Reference(reference=f"Patient/{obs[0]}")
            observation.subject = reference        

            # Add components for each attribute of the observation
            # Make sure the indices match the order in your database
            observation.component = [
                ObservationComponent(code=CodeableConcept(text="Snoring Rate"), valueQuantity=Quantity(value=float(obs[1])if obs[1] else "0")),
                ObservationComponent(code=CodeableConcept(text="Respiratory Rate"), valueQuantity=Quantity(value=float(obs[2])if obs[2] else "0")),
                ObservationComponent(code=CodeableConcept(text="Body Temperature"), valueQuantity=Quantity(value=float(obs[3])if obs[3] else "0")),
                ObservationComponent(code=CodeableConcept(text="Limb Movement"), valueQuantity=Quantity(value=float(obs[4])if obs[4] else "0")),
                ObservationComponent(code=CodeableConcept(text="Blood Oxygen"), valueQuantity=Quantity(value=float(obs[5])if obs[5] else "0")),
                ObservationComponent(code=CodeableConcept(text="Eye Movement"), valueQuantity=Quantity(value=float(obs[6])if obs[6] else "0")),
                ObservationComponent(code=CodeableConcept(text="Sleeping Hours"), valueQuantity=Quantity(value=float(obs[7]), unit="h")),
                ObservationComponent(code=CodeableConcept(text="Heart Rate"), valueQuantity=Quantity(value=float(obs[8])if obs[8] else "0")),
                ObservationComponent(code=CodeableConcept(text="Stress Level"), valueString=str(obs[9])if obs[9] else "0"),
                ObservationComponent(code=CodeableConcept(text="Observation Date"), valueString=str(obs[10])if obs[10] else "0"),
            ]

            bundle_entry = BundleEntry(resource=observation)
            bundle.entry.append(bundle_entry)

        return bundle.dict()
    else:
        return "Patient observations not found", 404

loinc_codes = {
    'Snoring Rate': 'R06.83',
    'Limb Movement': 'G47.6',
    'Heart Rate': '8889-8',
    'Sleeping Hours': '45550-1',
    'Stress Level': '76542-0',
    'Eye Movement': 'H55.89',
    'Blood Oxygen': '20564-1',
    'Body Temperature': '8310-5',
    'Respiratory Rate': '9279-1'
 }

# API route to get sleep observations by Patient_ID in FHIR format with LOINC codes
@app.route('/fhir/sleep-observations-loinc/<int:patient_id>', methods=['GET'])
def get_sleep_observations_fhir_with_loinc(patient_id):
    observations = read_patient_sleep_data(db_name, patient_id=patient_id)
    
    if observations:

        bundle = Bundle(type="searchset")
        bundle.entry = []

        for obs in observations:
            observation_component_data = [
                ("Snoring Rate", obs[1], None),
                ("Respiratory Rate", obs[2], None),
                ("Body Temperature", obs[3], None),
                ("Limb Movement", obs[4], None),
                ("Blood Oxygen", obs[5], None),
                ("Eye Movement", obs[6], None),
                ("Sleeping Hours", obs[7], "h"),
                ("Heart Rate", obs[8], None),
                ("Stress Level", obs[9], None),
    #            ("Observation Date", observations[10], ),
            ]

            # Define the code for the Observation
            code = CodeableConcept()
            code.coding = [Coding(system="http://loinc.org", code="LOINC_CODE", display="Sleep Observation")]
            code.text = "Sleep Observation"

            # Initialize the Observation object with the required code
            observation = Observation(status="final", code=code)
            reference = Reference(reference=f"Patient/{obs[0]}")
            observation.subject = reference        

            observation.component = []

            for text, value, unit in observation_component_data:
                try:
                    coding = [Coding(system="http://loinc.org", code=loinc_codes[text], display=text)]
                    oc = ObservationComponent(code=CodeableConcept(text=text, coding=coding), valueQuantity=Quantity(value=value)) 
                    observation.component.append(oc)
                except (ValueError, TypeError):
                    print('Skipped invalid data {0}, {1}, {2}'.format(text, value, unit))
                    
            bundle_entry = BundleEntry(resource=observation)
            bundle.entry.append(bundle_entry)

        return bundle.dict()
    else:
        return "Patient observations not found", 404

@app.route('/fhir/names', methods=['GET'])
def get_patient_names():
    conn = sqlite3.connect(db_name)
    cursor = conn.cursor()

    # Query to select the required columns
    cursor.execute("SELECT Patient_ID, First_Name, Last_Name FROM Patients")
    patients = cursor.fetchall()

    # Format the response
    response = [
        {"value": str(patient[0]), "label": f"{patient[1]} {patient[2]}"}
        for patient in patients
    ]

    conn.close()
    return jsonify(response)

@app.route('/fhir/dates/<int:patient_id>', methods=['GET'])
def get_observation_dates(patient_id):
    conn = sqlite3.connect(db_name)
    cursor = conn.cursor()

    # Query to select observation dates for the specified patient_id
    cursor.execute("SELECT observation_date FROM sleep_observations WHERE patient_id = ?", (patient_id,))
    observation_dates = cursor.fetchall()

    # Format the response
    response = [
        {"value": str(i), "label": date}
        for i, date in enumerate(observation_dates, start=1)
    ]

    conn.close()
    return jsonify(response)

@app.route('/verify_credentials', methods=['POST', 'OPTIONS'])
def verify_credentials():
    if request.method == 'OPTIONS':
        # Handle CORS preflight request
        response = make_response()
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type')
        response.headers.add('Access-Control-Allow-Methods', 'POST')
        return response
    
    if request.method == 'POST':
        data = request.json
        username = data['username']
        password = data['password']

        conn = sqlite3.connect('credentials.db')
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM users WHERE username = ? AND password = ?", (username, password))
        user = cursor.fetchone()

        conn.close()

        if user:
            response = jsonify({'exists': True})
            response.headers.add('Access-Control-Allow-Origin', '*')
            return response
        else:
            response = jsonify({'exists': False})
            response.headers.add('Access-Control-Allow-Origin', '*')
            return response

@app.route('/add_credentials', methods=['POST'])
def add_credentials():
    if request.method == 'POST':
        data = request.get_json()
        username = data['username']
        password = data['password']

        conn = sqlite3.connect('credentials.db')
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
        user = cursor.fetchone()

        if user:
            conn.close()
            response = jsonify({'error': 'Username already exists'})
            response.headers.add('Access-Control-Allow-Origin', '*')
            return response

        cursor.execute("INSERT INTO users (username, password) VALUES (?, ?)", (username, password))
        conn.commit()
        conn.close()

        response = jsonify({'success': True})
        response.status_code = 201  # Resource created successfully
        response.headers.add('Access-Control-Allow-Origin', '*')
        return response


@app.route('/get_credentials', methods=['GET'])
def get_credentials():
    # Connect to the SQLite database
    conn = sqlite3.connect('credentials.db')
    cursor = conn.cursor()

    # Execute the query to fetch all usernames and passwords
    cursor.execute("SELECT username, password FROM users")
    credentials = cursor.fetchall()

    # Close the database connection
    conn.close()

    # Format the data for the response
    credentials_list = [{'username': username, 'password': password} for username, password in credentials]

    return jsonify(credentials_list)

if __name__ == "__main__":
    
    db_name = "sleep_data.db"

    if os.path.exists(db_name):
       os.remove(db_name)
   
    create_table_from_csv(db_name, "data/patients.csv")

    create_sleep_observations_table(db_name, "data/sleep_observation.csv")

    patient_id = 1
    #print(read_patient_data(patient_id))

    patient_dict = get_patient_data_fhir(patient_id)
    
    with open("sample-patient-fhir.json", "w") as f:
        json.dump(patient_dict, f, indent=2, cls=CustomEncoder)
    print('Patient fhir format written to file. \n')

    print('\n============================')

    obs_bundle_dict = get_sleep_observations_fhir_with_loinc(patient_id=patient_id)
    with open("sample-patient-obs-bundle.json", 'w') as f:
        json.dump(obs_bundle_dict, f, indent=2, cls=CustomEncoder)
    print('Patient observations in fhir format written to file. \n')

    # Check adding new patient works
    patient_data = {
        'First_Name': 'John',
        'Last_Name': 'Doe',
        'Date_of_Birth': '1990-01-01',
        'Gender': 'Male',
        'Phone_Number': '123-456-7890',
        'Email': 'john.doe@example.com',
        'Address': '123 Main St',
        'City': 'Anytown',
        'State': 'CA',
        'Zip_Code': '12345'
    }

    before_cnt = get_records_count("Patients")
    insert_new_patient(db_name, patient_data)
    after_cnt = get_records_count("Patients")

    print('Before count: {} After count: {}'.format(before_cnt, after_cnt))

    # Check insert works
    d = {
        "patient_id": 1,
        "observation_date": "2023-02-01",
        "body_temperature": 98.0,
        "snoring_rate": 5.5,
        "respiratory_rate": 18.0,
        "eye_movement": "0",
        "sleeping_hours": 7.5,
        "heart_rate": 70,
        "stres_level":1,
        "limb_movement":10,
        "blood_oxygen":90
    }

    before_cnt = get_records_count("sleep_observations")
    insert_sleep_data(db_name, d)
    after_cnt = get_records_count("sleep_observations")

    print('Before count: {} After count: {}'.format(before_cnt, after_cnt))

    delete_observation_data(db_name, patient_id=1, observation_date='2023-02-01')
    after_delete_cnt = get_records_count("sleep_observations")
    print('Before count: {} After count: {}'.format(after_cnt, after_delete_cnt))

    # Set the port dynamically with a default to 5000 for local development
    port = int(os.environ.get("PORT", 5000))

    app.run(debug=True, host='0.0.0.0', port=port)
    # http://127.0.0.1:5000/fhir/patient/1 in postman
    # curl http://127.0.0.1:5000/fhir/patient/1 in terminal