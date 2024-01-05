from bs4 import BeautifulSoup
import re, sys, json, logging, configparser
from datetime import datetime, timedelta
import os.path
from googletrans import Translator
from modules.save_to_postgresql_db import save_to_postgresql_db
from modules.item import Job

def scrap_job(job_html):
    """Function to scrap the information of the job
    
    Parameters
    ----------
        job_html : html
            html code of the job description
    Returns
    -------
        job : instance
            Instance of a job class with the scrapped information of the job
    """
    logger = logging.getLogger('scrap_job_help_function')

    # Create job instance
    job = Job()
    
    # Parse with Beautiful Soup
    soup = BeautifulSoup(job_html, "lxml")
    soup = soup.find(class_="job-view-layout")
    
    # Get job url
    job_url = "https://www.linkedin.com/" + soup.find("a", href=True)['href']
    job.url = job_url.split("?")[0]

    # Start class data
    start_class_data = "job-details-jobs-unified-top-card__"

    # Get job name
    job.position_name = soup.find("h2", class_=f"{start_class_data}job-title").get_text().strip()

    # Get company, city, country, number of applicants and posted_date
    company_location_applicants_selection = soup.find("div", class_=f"{start_class_data}primary-description-without-tagline")
    company_applicants_location_text = company_location_applicants_selection.get_text().split("·")
    
    try:
        job.company = company_applicants_location_text[0].strip()
    except:
        job.company = None

    try:
        # Get the location dirty text, as it contains when it was posted or reposted
        location_dirty_text = company_applicants_location_text[1]
        
        # Get the Undesired text to be deleted in location
        undesired_text_selection = company_location_applicants_selection.find_all("span", class_="tvm__text")
        undesired_text_list = [x.get_text() for x in undesired_text_selection]

        # Delete the undesired text from location ("Reposted 2 weeks ago")
        location = location_dirty_text.replace(undesired_text_list[0],"").strip()
        
        # Split the location to check for country and city
        location = location.split(",")
        
        if len(location) < 3:
            job.city = location[0]
        if len(location) == 3:
            job.city = location[0]
            job.country = location[2].strip()
    except:
        job.city = None

    try:
        posted_date_text = undesired_text_list[0].replace("Reposted", "").replace("ago", "").strip()
        job.posted_date = get_aprox_posted_date(posted_date_text)
    except:
        job.posted_date = None

    try:
        job.applicants = int(re.findall(r'\d+',company_applicants_location_text[2])[0])
    except:
        job.applicants = None

    # Get job contract_type, contract_time and job_experience
    contract_details_li = soup.find_all("li", class_=f"{start_class_data}job-insight")[0]
    contract_details_aria_hidden_spans = contract_details_li.find_all("span", {'aria-hidden': 'true'})
    contract_details_others_spans = contract_details_li.find_all("span", class_=f"{start_class_data}job-insight-view-model-secondary")

    try:
        job.contract_type = contract_details_aria_hidden_spans[0].get_text()
    except:
        job.contract_type = None

    try:
        job.contract_time = contract_details_aria_hidden_spans[1].get_text()
    except:
        job.contract_time = None

    try:
        job.experience = contract_details_others_spans[1].get_text().strip()
    except:
        job.experience = None

    # Get the job description and the post date
    description_dirty = soup.find("article").get_text(separator="\n").replace("About the job", "").strip()
    job.description = "\n".join(description_dirty.split("\n")[:-1]).strip()

    return job

def get_aprox_posted_date(posted_date_text):
    """Function that calculates an approximate posted date of the job
    
    Parameters
    ----------
        posted_date_text : str
            Text that describes how long time ago the job was posted in Linkedin
    Returns
    -------
        posted_date : str
            Approximate Posted date in the format "%d-%m-%Y"
    """
    current_datetime = datetime.now()
    number = int(re.findall("\d+", posted_date_text)[0])

    if "hour" in posted_date_text:
        posted_datetime = current_datetime - timedelta(hours = number)
    elif "day" in posted_date_text:
        posted_datetime = current_datetime - timedelta(days = number)
    elif "week" in posted_date_text:
        posted_datetime = current_datetime - timedelta(weeks = number)
    elif "month" in posted_date_text:
        posted_datetime = current_datetime - timedelta(days = number*30)

    posted_date = posted_datetime.strftime("%d-%m-%Y")
    
    return posted_date

def save_job_questions_no_answer(list_questions_no_answer, path):
    """Function to save the questions without answers
        
        Parameters
        ----------
            list_questions_no_answer : list
                List of questions without answers
            path : str
                path to save the information in a json file
        Returns
        -------
            json_file : json
                Create a json file in the path directory
        """

    # if file exists open the file, append the data and write again the file
    if os.path.isfile(path):
        with open(path, 'r+') as json_file:
            file_data = json.load(json_file)
            for question in list_questions_no_answer:
                file_data.append(question)
        with open(path, 'w') as json_file:        
            json.dump(file_data, json_file, indent=4)
    # Else create the file and write it
    else:
        with open(path, 'w') as json_file:
            json.dump(list_questions_no_answer, json_file, indent=4)

def save_job_info_to_json(list_jobs_instances, path):
    """Function to scrap the information of the job
    
    Parameters
    ----------
        list_jobs_instances : instances
            List of job instances with the linkedin jobs information
        path : str
            path to save the information in a json file
    Returns
    -------
        json_file : json
            Create a json file in the path directory
    """
    
    logger = logging.getLogger('save_job_info_to_json')

    logger.info("Saving to json file")

    list_dicts = []
    # Transform objects to dict
    for instance in list_jobs_instances:
        list_dicts.append(instance.transform_to_dict())
    
    # if file exists open the file, append the data and write again the file
    if os.path.isfile(path):
        with open(path, 'r+') as json_file:
            file_data = json.load(json_file)
            for dictionary in list_dicts:
                file_data.append(dictionary)
        with open(path, 'w') as json_file:        
            json.dump(file_data, json_file, indent=4)
    # Else create the file and write it
    else:
        with open(path, 'w') as json_file:
            json.dump(list_dicts, json_file, indent=4)

def translate_description(description):
    """Function to translate the description if needed.
    
    Parameters
    ----------
        description : str
            Description to be translated

    Returns
    -------
        description : str
            Translated description if was not in english
    """
    
    translator = Translator()
    # Detect language and if it is not english then translate
    if translator.detect(description).lang != 'en':
        try:
            description = translator.translate(description, dest='en').text
        except:
            return description
    return description

def pre_process_description(description):
    """Function to clean the description. Replace some symbols and add a stop if there is a newline
    without a stop. This will help to delimit the sentences with spacy. Also all words are transformed
    to lowercase
    
    Parameters
    ----------
        description : str
            Description to be processed

    Returns
    -------
        clean_description : str
            Clean description. Without new lines and with stops if missing. Also lowercase
    """

    list_description = list(description.replace("\u2022","").replace("/", " "))
    for i , symbol in enumerate(list_description):
        if symbol == '\n':   
            prev_symbol = list_description[i-1]
            if prev_symbol == "." or prev_symbol == ":" or prev_symbol == " ":
                list_description[i] = " " # Replace \n for a space
            else:
                list_description[i] = ". " # Replace \n for a . and space

    clean_description = "".join(list_description).lower()
    return clean_description

def tokenize_words(list_words, nlp):
    """Function to tokenize words and be able to know the similarity
    
    Parameters
    ----------
        list_words : list
            List of words to check that need to be tokenized
        nlp : spacy nlp model
            Model to be used to tokenize

    Returns
    -------
        tokenize_words : spacy doc
            Spacy doc with the words that now are tokens
    """

    tokenize_words = nlp(" ".join(list_words))
    return tokenize_words

def check_similarity(list_doc, list_check, entity):
    """Function to check similarity between words.
    
    Parameters
    ----------
        list_doc : list
            List of words that are in the document and must be checked
        list_check : list
            List of words that you want to check if they are in the document
        entity : spacy entity
            Language to be checked and that you do not speak
    Returns
    -------
        max_similarity : float
            Max similarity between the words to check
    """

    max_similarity = 0

    for doc_word in list_doc:
        # Only check words that are not the entity (the language)
        if doc_word.text != entity.text:
            for check_word in list_check:
                # Calculate similarity between word vectors
                similarity = doc_word.similarity(check_word)
                if similarity > max_similarity:
                    # Get the max similarity from the list
                    max_similarity = similarity

    return max_similarity

def scrap_easy_apply(questions_html):
    """Function to scrap the information of EasyApply Questions tab
    
    Parameters
    ----------
        questions_html : html
            html code of the questions
    Returns
    -------
        input_questions : list
            List of questions that require input
        select_questions : list
            List of questions that require to select from options
        checkbox_questions : list
            List of questions that require to click a button with options
        fill_select_questions : list
            List of questions that require first to fill and then select an option
    """
    soup = BeautifulSoup(questions_html, "lxml")

    questions = soup.find_all("div", class_="jobs-easy-apply-form-section__grouping")

    input_questions = []
    select_questions = []
    checkbox_questions = []
    fill_select_questions = []

    for i, question in enumerate(questions):
        if question.find("label", class_="artdeco-text-input--label"):
            input_questions.append(question.get_text().strip())
        if question.find("select"):
            select_questions.append(question.find("span").get_text().strip())
        if question.find("input", class_="fb-form-element__checkbox"):
            legend = question.find("legend")
            checkbox_questions.append(legend.find("span", class_="visually-hidden").get_text().strip())
        if question.find("label",class_="fb-dash-form-element__label") and not question.find("select"):
            fill_select_questions.append(question.find("span", class_="visually-hidden").get_text().strip())

    return input_questions, select_questions, checkbox_questions, fill_select_questions

def load_json_to_dict(path):
    """Function that loads a json file as dict
    
    Parameters
    ----------
        path : str
            Path to the json file
    Returns
    -------
        file_data : dict
            Data from the json, as dict
    """
    with open(path, 'r') as json_file:
        file_data = json.load(json_file)
        return file_data

def load_user_search_save_apply_options():
    """Function that loads the user options to search, save and apply from the config.ini file
    
    Returns
    -------
        dict_user_opts : dict
            Dictionary with the user options of search, save and apply      
    """
    # Load parameters from config file
    config_obj = configparser.ConfigParser(converters={'list': lambda x: [i.strip() for i in x.split(',')]})
    config_obj.read("./configfile.ini")

    dict_user_opts = dict()
    
    # Options
    dict_user_opts["save_to_json_file"] = config_obj.getboolean('options', 'save_to_json_file')
    dict_user_opts["save_to_postgresql_db"] = config_obj.getboolean('options', 'save_to_postgresql_db')
    dict_user_opts["apply_with_easy_apply"] = config_obj.getboolean('options', 'easy_apply')
    dict_user_opts["easy_apply_quest_answ_path"] = config_obj["options"]["easy_apply_quest_answ_path"]
    dict_user_opts["name_postgre_table"] = config_obj["options"]["name_postgre_table"]
    dict_user_opts["headless"] = config_obj.getboolean('options', 'headless')

    # User search
    dict_user_opts["search_positions"] = config_obj.getlist("user_search","positions")
    dict_user_opts["search_countries"] = config_obj.getlist("user_search","countries")

    # Filters
    dict_user_opts["easy_apply_filter"] = config_obj.getboolean("filters","easy_apply")
    dict_user_opts["date_posted_filter"] = config_obj["filters"]["date_posted"]
    dict_user_opts["experience_level_filter"] = config_obj.getlist("filters","experience_level")
    dict_user_opts["how_to_work_filter"] = config_obj.getlist("filters","how_to_work")


    return dict_user_opts

def logger_config():
    """Function that sets the logger config"""
    logging.basicConfig(
        filename="logs.log",
        encoding="utf-8",
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        level=logging.INFO,
    )

async def get_total_number_job_pages(page):
    """Function that gets the number of job pages that has the search results
    
    Parameters
    ----------
        page : playwright object
            playwright page object
    Returns
    -------
        init_page_number : int
            Initial page number
        max_number_pages : int
            Max number of pages
    """
    
    # Check all the pages while there is no error
    init_page_number = 1 # Initial page number

    # Get the max number of pages
    if await page.locator("div.jobs-search-results-list > div.jobs-search-results-list__pagination").count() != 0:
        num_pages_range = await page.locator("div.artdeco-pagination__page-state").text_content()
        max_number_pages = int(re.findall(r'[0-9]+', num_pages_range)[1])
    else:
        max_number_pages = 1

    return init_page_number, max_number_pages

def save_jobs_information(list_jobs_instances, dict_user_opts):
    """Function that saves the information to a json and/or PostgreSQL database
    
    Parameters
    ----------
        list_jobs_instances : list
            List of job instances with the jobs information
        dict_user_opt_search_save_apply : dict
            Dictionary with the user options of search, save and apply  
    """

    # After one page has been webscrapped and analyzed then save all the instances of the list to a json file. If Option = True
    if dict_user_opts["save_to_json_file"]:
        save_job_info_to_json(list_jobs_instances, "./data/linkedin_jobs.json")

    # Save to postgresql if option = True
    if dict_user_opts["save_to_postgresql_db"]:
        save_to_postgresql_db(list_jobs_instances, dict_user_opts)

def log_exceptions(e, logger):
    """Function that log the exceptions and break the try
    Parameters
    ----------
        e : Exception
            List of job instances with the jobs information
        logger : object
            logger object 
    """
    
    logger.info(f"Error: {e}")
    exc_type, exc_obj, exc_tb = sys.exc_info()
    fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
    logger.info(f"Exc_type: {exc_type}")
    logger.info(f"FName: {fname}")
    logger.info(f"LineNo: {exc_tb.tb_lineno}")

async def check_easy_apply_button(page):
    """Function checks if there is an EasyApply button to apply
    
    Parameters
    ----------
        page : playwright object
            playwright page object
    Returns
    -------
        bool : bool
            True if there is an Easy Apply button, False otherwise
    """
    if await page.locator("div.jobs-s-apply > div > button:visible > span", has_text="Easy Apply").count() !=0:
        return True
    else:
        return False