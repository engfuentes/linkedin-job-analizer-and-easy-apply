import psycopg2, os, logging
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger('save_to_postgresql_db')

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
    
    logger.info("Saving to the PostgreSQL DB")

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
        id serial ,
        search_position VARCHAR(255),
        search_country VARCHAR(255), 
        url TEXT,
        position_name VARCHAR(255),
        company VARCHAR(255),
        city VARCHAR(255),
        country VARCHAR(255),
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
        list_tags TEXT [],
        easy_apply_questions TEXT [],
        applied BOOL,
        could_not_apply_due_to_questions BOOL,
        manual_apply BOOL,
        PRIMARY KEY (posted_date, position_name, company) 
    );
    """)

    for job in list_jobs_instances:
        # Check if already in Database
        cur.execute(
            "SELECT * FROM linkedin_jobs WHERE posted_date = %s AND position_name = %s AND company = %s",\
            (job.posted_date, job.position_name, job.company,))
        result = cur.fetchone()

        ## If it is in the Db then log but do not insert
        if result:
            logger.warn(f"Job already in database: {job.position_name}")
        
        else:
            # Define insert statement
            cur.execute("""INSERT INTO linkedin_jobs (
                search_position,
                search_country, 
                url,
                position_name,
                company,
                city,
                country,
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
                list_tags,
                easy_apply_questions,
                applied,
                could_not_apply_due_to_questions,
                manual_apply
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
                    %s,
                    %s,
                    %s,
                    %s,
                    %s,
                    %s,
                    %s,
                    %s
                    );""", (
                job.search_position,
                job.search_country,            
                job.url,
                job.position_name,
                job.company,
                job.city,
                job.country,
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
                job.list_tags,
                job.easy_apply_questions,
                job.applied,
                job.could_not_apply_due_to_questions,
                job.manual_apply
            ))

            # Execute insert of data into database
            connection.commit()
    
    # Close cursor and connection to database 
    cur.close()
    connection.close()