import os
import sys

# Add the parent directory to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from app.models.requirement import NABTEBAcceptance, NABTEBFacultyAcceptance, NABTEBProgramAcceptance
from app.models.university import University
from app.extensions import db
from datetime import datetime

def populate_nabteb_data():
    app = create_app()
    with app.app_context():
        # Kaduna State University - Explicit exclusion
        kaduna_uni = University.query.filter(University.university_name.ilike('%Kaduna State%')).first()
        if kaduna_uni:
            nabteb = NABTEBAcceptance(
                university_id=kaduna_uni.id,
                accepts_as_olevel=False,
                accepts_advanced_cert=False,
                verification_source='institutional_data_2023',
                special_conditions='Explicitly only accepts WAEC and NECO certificates',
                verified_at=datetime.utcnow()
            )
            db.session.add(nabteb)
            
        # UNIBEN - Explicit acceptance with specific faculties and programs
        uniben = University.query.filter(University.university_name.ilike('%Benin%')).first()
        if uniben:
            nabteb = NABTEBAcceptance(
                university_id=uniben.id,
                accepts_as_olevel=True,
                accepts_advanced_cert=True,
                verification_source='institutional_data_2023',
                special_conditions='Accepted as O\'level equivalent for basic requirements. NABTEB Advanced Certificate recognized as specialized diploma equivalent.',
                verified_at=datetime.utcnow()
            )
            db.session.add(nabteb)
            
            # Add faculty acceptances
            faculties = [
                ('Social Sciences', 'full', None),
                ('Education', 'full', None),
                ('Engineering', 'full', None),
                ('Management Sciences', 'full', None),
                ('Arts', 'partial', 'Only selected programs')
            ]
            
            for faculty, acceptance_type, conditions in faculties:
                faculty_acceptance = NABTEBFacultyAcceptance(
                    nabteb_acceptance=nabteb,
                    faculty_name=faculty,
                    acceptance_type=acceptance_type,
                    conditions=conditions
                )
                db.session.add(faculty_acceptance)
            
            # Add program acceptances
            programs = [
                ('Geography and Regional Planning', 'full', None),
                ('Political Science', 'full', None),
                ('Sociology', 'full', None),
                ('Public Administration', 'full', None),
                ('Economics', 'full', None),
                ('Accounting', 'full', None),
                ('Business Administration', 'full', None),
                ('Banking and Finance', 'full', None),
                ('Fine Arts', 'full', None),
                ('Mass Communication', 'full', None)
            ]
            
            for program, acceptance_type, conditions in programs:
                program_acceptance = NABTEBProgramAcceptance(
                    nabteb_acceptance=nabteb,
                    program_name=program,
                    acceptance_type=acceptance_type,
                    conditions=conditions
                )
                db.session.add(program_acceptance)
        
        try:
            db.session.commit()
            print("Successfully populated NABTEB acceptance data")
        except Exception as e:
            db.session.rollback()
            print(f"Error populating data: {str(e)}")

if __name__ == '__main__':
    populate_nabteb_data()
