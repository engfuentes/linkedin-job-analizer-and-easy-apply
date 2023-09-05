from bs4 import BeautifulSoup
import re
import json
from modules.item import Job
import os.path
from googletrans import Translator

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

    # Create job instance
    job = Job()
    
    # Parse with Beautiful Soup
    soup = BeautifulSoup(job_html, "lxml")
    soup = soup.find(class_="job-view-layout")
    
    # Get job url
    job.url = "https://www.linkedin.com/" + soup.find("a", href=True)['href']

    # Get job name
    job.name = soup.find("h2", class_="jobs-unified-top-card__job-title").get_text().strip()

    # Get company, city, contract_type and number of applicants
    company_location_applicants = soup.find("div", class_="jobs-unified-top-card__primary-description").get_text().split("·")
    job.company = company_location_applicants[0].strip()
    job.location = company_location_applicants[1].split("\n")[0].split("(")[0].strip()
    try:
        job.contract_type = company_location_applicants[1].split("\n")[0].split("(")[1].split(")")[0].strip()
    except:
        job.contract_type = None
    job.applicants = int(re.findall(r'\d+',company_location_applicants[2])[0])

    # Get job contract_time and job_experience
    try:
        job.contract_time = soup.find("li", class_="jobs-unified-top-card__job-insight").get_text().split("·")[0].strip()
    except:
        job.contract_time = None
    try:
        job.experience = soup.find("li", class_="jobs-unified-top-card__job-insight").get_text().split("·")[1].strip()
    except:
        job.experience = None

    # Get the job description and the post date
    description_dirty = soup.find("article").get_text(separator="\n").replace("About the job", "").strip()
    job.description = "\n".join(description_dirty.split("\n")[:-1]).strip()
    job.posted_date = description_dirty.split("\n")[-1].replace("Posted on","").replace(".", "").strip()

    return job

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
        description = translator.translate(description, dest='en').text
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
