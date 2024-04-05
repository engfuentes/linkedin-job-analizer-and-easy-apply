import psycopg2, os, logging
from dotenv import load_dotenv
import hashlib

load_dotenv()

logger = logging.getLogger('save_to_postgresql_db')

def save_to_postgresql_db(list_jobs_instances, dict_user_opts):
    """Function used to saved the data from the jobs to a PosgreSQL Database
    
    Parameters
    ----------
        list_job_instances : list
            List of job instances that have to be saved to the database
        dict_user_opt_search_save_apply : dict
            Dictionary with the user options of search, save and apply 
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
    
    name_postgre_table = dict_user_opts["name_postgre_table"]

    # Create linkedin_jobs table if none exists
    cur.execute(f"""
    CREATE TABLE IF NOT EXISTS {name_postgre_table} (
        id CHAR(10) PRIMARY KEY,
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
        description_lang VARCHAR(5),
        posted_date DATE,
        apply BOOL,
        email TEXT [],
        reason_not_apply TEXT [],
        list_tech_no_knowledge TEXT [],
        list_tags TEXT [],
        easy_apply_questions TEXT [],
        applied BOOL,
        could_not_apply_due_to_questions BOOL,
        manual_apply BOOL
    );
    """)

    for job in list_jobs_instances:
        # Get unique id hassing the job description and shortening the hash
        unique_id = hashlib.sha1(job.description.encode()).hexdigest()[0:10]

        # Check if already in Database
        cur.execute(
            f"""SELECT * FROM {name_postgre_table} WHERE id = %s""", (unique_id,))
        result = cur.fetchone()

        ## If it is in the Db then log but do not insert
        if result:
            logger.warn(f"Job already in database: {job.position_name}")
        
        else:
            # Define insert statement
            cur.execute(f"""INSERT INTO {name_postgre_table} (
                id,
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
                description_lang,
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
                    %s,
                    %s,
                    %s
                    );""", (
                unique_id,
                job.search_position,
                job.search_country,            
                job.url,
                job.position_name,
                job.company,
                job.city,
                job.country,
                job.contract_type,
                job.applicants,
                job.contract_time,
                job.experience,
                job.description,
                job.description_lang,
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