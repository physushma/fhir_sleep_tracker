# Sleep Tracker Data to FHIR Converter

This Python program converts data collected from sleep tracker applications into the Fast Healthcare Interoperability Resources (FHIR) standard data format. It also provides functionality to convert FHIR data back into a general table format, suitable for data analysis.

## Features

- **Data Conversion**: Converts sleep tracker data (in CSV format) into FHIR standard format.
- **FHIR to Table Conversion**: Converts FHIR formatted data back into a general table format (SQLite database).
- **REST API**: Provides RESTful APIs to add new patients, insert sleep observation data, delete observations, and retrieve patient and observation data in FHIR format.
- **CORS Enabled**: Supports Cross-Origin Resource Sharing (CORS) for integration with web applications.
- **Error Handling**: Provides error handling for missing fields and database operations.
