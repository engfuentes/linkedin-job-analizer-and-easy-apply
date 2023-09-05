import psycopg2
import os
from dotenv import load_dotenv

load_dotenv()

def save_to_postgresql_db(list_jobs_instances):
    """Function used to saved the data from the jobs to a PosgreSQL Database
    
    Parameters
    ----------
        list_job_instances : list
        List of job instances that have to be saved to the database
    Returns
    -------
        apply : bool
            Boolean to apply or not according to language requirements
        reason_not_apply : str
            Reason not to apply if there is one
    """
    
    ## Connection details
    POSTGRESQL_HOSTNAME = os.getenv("POSTGRESQL_HOSTNAME")
    POSTGRESQL_USERNAME = os.getenv("POSTGRESQL_USERNAME")
    POSTGRESQL_PASSWORD = os.getenv("POSTGRESQL_PASSWORD")
    POSTGRESQL_DATABASE = os.getenv("POSTGRESQL_DATABASE")

    # Connect to database
    connection = psycopg2.connect(host=POSTGRESQL_HOSTNAME, user=POSTGRESQL_USERNAME,
                                  password=POSTGRESQL_PASSWORD, dbname=POSTGRESQL_DATABASE)
    
    # Create cursor
    cur = connection.cursor()
    
    # Create linkedin_jobs table if none exists
    cur.execute("""
    CREATE TABLE IF NOT EXISTS linkedin_jobs (
        id serial PRIMARY KEY, 
        url TEXT,
        name VARCHAR(255),
        company VARCHAR(255),
        location VARCHAR(255),
        contract_type VARCHAR(255),
        applicants INTEGER,
        contract_time VARCHAR(255),
        experience VARCHAR(255),
        description TEXT,
        posted_date VARCHAR(100),
        apply BOOL,
        email TEXT [],
        reason_not_apply TEXT [],
        list_tech_no_knowledge TEXT [],
        list_tags TEXT []
    );
    """)

    for job in list_jobs_instances:
        # Define insert statement
        cur.execute("""INSERT INTO linkedin_jobs (
            url,
            name,
            company,
            location,
            contract_type,
            applicants,
            contract_time,
            experience,
            description,
            posted_date,
            apply,
            email,
            reason_not_apply,
            list_tech_no_knowledge,
            list_tags
            ) values (
                %s,
                %s,
                %s,
                %s,
                %s,
                %s,
                %s,
                %s,
                %s,
                %s,
                %s,
                %s,
                %s,
                %s,
                %s
                );""", (
            job.url,
            job.name,
            job.company,
            job.location,
            str(job.contract_type),
            job.applicants,
            str(job.contract_time),
            job.experience,
            job.description,
            job.posted_date,
            job.apply,
            job.email,
            job.reason_not_apply,
            job.list_tech_no_knowledge,
            job.list_tags
        ))

        # Execute insert of data into database
        connection.commit()
    
    # Close cursor and connection to database 
    cur.close()
    connection.close()