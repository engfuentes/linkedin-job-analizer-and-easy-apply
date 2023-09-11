import spacy
from spacy import displacy
from spacy.matcher import Matcher
from spacy.language import Language
import json, re, logging, configparser
from modules.helper_functions import translate_description, pre_process_description, tokenize_words, check_similarity

logger = logging.getLogger('check apply module')

# Load the entity data
with open('./data/data.json', 'r') as json_file:
    json_data = json.load(json_file)

# Load parameters from config file
config_obj = configparser.ConfigParser(converters={'list': lambda x: [i.strip() for i in x.split(',')]})
config_obj.read("./configfile.ini")

def load_user_words_to_check():
    """Function that loads the user options regarding the words to check for the language
    
    Returns
    -------
        possible_languages : list
            List of languages that you speak
        adj_to_check, noun_to_check, propn_to_check, verb_to_check, adv_to_check: list
            List of words to check if they are in the document and their similarity with doc words
        similarity_threshold : float
            Threshold to decide if the words are similar or not"""
    
    # Languages the user speaks
    possible_languages = config_obj.getlist('languages_user_speak_fluently', 'languages')

    # Words to check in the languages that you dont speak
    adj_to_check = config_obj.getlist('words_check_language_check', 'adj_to_check')
    noun_to_check = config_obj.getlist('words_check_language_check', 'noun_to_check')
    propn_to_check = config_obj.getlist('words_check_language_check', 'propn_to_check')
    verb_to_check = config_obj.getlist('words_check_language_check', 'verb_to_check')
    adv_to_check = config_obj.getlist('words_check_language_check', 'adv_to_check')
    similarity_threshold = float(config_obj["words_check_language_check"]["similarity_threshold"])

    return possible_languages, adj_to_check, noun_to_check, propn_to_check, verb_to_check, adv_to_check, similarity_threshold

def load_user_experience_to_check():
    """Function that loads the user options regarding the experience to check 
    
    Returns
    -------
        seniority_do_not_apply : list
            List of seniority words that can be present in the description not to apply for the job
        experience_max_year_threshold : int
            Max threshold of years to apply or not to the job"""
    
    # Experience parameters
    seniority_do_not_apply = config_obj.getlist('experience', 'seniority_do_not_apply')
    experience_max_year_threshold = int(config_obj["experience"]["experience_max_year_threshold"])
    
    return seniority_do_not_apply, experience_max_year_threshold

def load_user_technologies_to_check():
    """Function that loads the user options regarding the technologies to check 
    
    Returns
    -------
        entities_do_not_apply : list
            List of entities that you dont want to apply. Example: "Automation Server", "In-Memory Data Store", etc
        programming_languages_apply : list
            List of programming languages that you know. Example: "python", "dax", etc
        backend_frameworks_apply : list
            List of backend frameworks that you know: Example: "django", "flask" """
    
    # Technologies parameters
    entities_do_not_apply = config_obj.getlist('technologies', 'entities_do_not_apply')
    programming_languages_apply = config_obj.getlist('technologies', 'programming_languages_apply') 
    backend_frameworks_apply = config_obj.getlist('technologies', 'backend_frameworks_apply')

    return entities_do_not_apply, programming_languages_apply, backend_frameworks_apply

def pre_process_text(description):
    """Function to process the description
    
    Parameters
    ----------
        description : str
            Description to be processed

    Returns
    -------
        description : str
            Ready to use description
    """
    description = translate_description(description)
    description = pre_process_description(description)
    return description

def transform_words_to_num(span_text):
    """Function that transforms a word number in an int
    
    Parameters
    ----------
        span_text : str
            Span text that has a word number

    Returns
    -------
        integer : int
            The integer
    """
    if 'one' in span_text:
        return 1
    if 'two' in span_text:
        return 2
    if 'three' in span_text:
        return 3
    if 'four' in span_text:
        return 4
    if 'five' in span_text:
        return 5
    if 'six' in span_text:
        return 6
    if 'seven' in span_text:
        return 7
    if 'eight' in span_text:
        return 8
    if 'nine' in span_text:
        return 9
    if 'ten' in span_text:
        return 10

def create_nlp_model():
    """Function that creates the nlp model.
    - Has a custom_boundary to detect : as sentence delimiter
    - Has an EntityRuler to detect the words that are in ./data/data.json
    
    Returns
    -------
        nlp : spacy_nlp_model
            Spacy custom model   
    """
    # Add : to detect as sentence delimiter
    @Language.component("set_custom_boundaries")
    def set_custom_boundaries(doc):
        """Add support to use `:` as a delimiter for sentence detection"""
        for token in doc[:-1]:
            if token.text == ":":
                doc[token.i + 1].is_sent_start = True
        return doc
    
    nlp = spacy.load("en_core_web_lg") # Load the large model
    nlp.add_pipe("set_custom_boundaries", before="parser") # Add the new delimiter to the pipeline

    # Create the EntityRuler to detect words
    ruler = nlp.add_pipe("entity_ruler", before="ner")

    # List of Entities and Patterns
    patterns = []
    for key in json_data:
        for entity in json_data[key]:
            patterns.append({"label": key, "pattern": entity.lower()})

    ruler.add_patterns(patterns)
    
    return nlp

def check_language_requirement(doc, nlp):
    
    """Function to check the language requirement.
    
    Parameters
    ----------
        doc : spacy doc
            Description to check in spacy doc type
        nlp : spacy nlp model
            Spacy nlp model to be used
    Returns
    -------
        apply_language : bool
            Boolean to apply or not according to language requirements
        reason_not_apply : str
            Reason not to apply if there is one
    """
    
    apply_language = True
    reason_not_apply = ""

    # Load user options
    possible_languages, adj_to_check, noun_to_check, propn_to_check, verb_to_check, \
    adv_to_check, similarity_threshold = load_user_words_to_check()

    # Tokenize words to check
    adj_to_check = tokenize_words(adj_to_check, nlp)
    noun_to_check = tokenize_words(noun_to_check, nlp)
    propn_to_check = tokenize_words(propn_to_check, nlp)
    verb_to_check = tokenize_words(verb_to_check, nlp)
    adv_to_check = tokenize_words(adv_to_check, nlp)

    # Check if there are languages in the job description
    for entity in doc.ents:
        # Check only entities that are Language
        if entity.label_ == "Language":
            
            # Check only if the entity is not one of the possible language that you can speak
            if entity.text not in possible_languages:                  
                # Get the sentence where that entity is
                sentence = entity.sent
                # Get words from the sentence with the language that you do not speak
                adjectives = [token for token in sentence if token.pos_ == "ADJ"]
                nouns = [token for token in sentence if token.pos_ == "NOUN"]
                propn = [token for token in sentence if token.pos_ == "PROPN"]
                verbs = [token for token in sentence if token.pos_ == "VERB"]
                adv = [token for token in sentence if token.pos_ == "ADV"]

                # Calculate similarity with the words to check                
                sim_1 = check_similarity(adjectives, adj_to_check, entity)
                sim_2 = check_similarity(nouns, noun_to_check, entity)
                sim_3 = check_similarity(propn, propn_to_check, entity)
                sim_4 = check_similarity(verbs, verb_to_check, entity)
                sim_5 = check_similarity(adv, adv_to_check, entity)
                
                # Calculate the max similarity. If similarity > similarity_threshold then do not apply
                if max([sim_1, sim_2, sim_3, sim_4, sim_5]) > similarity_threshold:
                    apply_language = False
                    reason_not_apply = "Language Requirement"
    
    return apply_language, reason_not_apply

def check_experience_requirement(doc, nlp):
    """Function to check the experience or seniority required by the job description.
    
    Parameters
    ----------
        doc : spacy doc
            Description to check in spacy doc type
        nlp : spacy_nlp_model
            Spacy custom model
    Returns
    -------
        apply : bool
            Boolean to apply or not according to experience requirements
        reason_not_apply : str
            Reason not to apply if there is one
    """
    apply_experience = True
    reason_not_apply = ""

    # Load the user options
    seniority_do_not_apply, experience_max_year_threshold = load_user_experience_to_check()

    # Check the seniority
    for entity in doc.ents:
        # Check the Role Experience Entity if there is one. We pass which ones not to apply to, for example "senior"
        if entity.label_ == "Role Experience":
            for seniority in seniority_do_not_apply:
                if entity.text == seniority.lower():
                    apply_experience = False
                    reason_not_apply = "Seniority"

    # Check the number of years of experience
    for token in doc:
        if token.text == "experience" or token.text == "experiences":
            # If it says the number of year of experience that are required
            sentence = token.sent
            
            matcher = Matcher(nlp.vocab)
            pattern1 = [{"LIKE_NUM": True}, {"ORTH": "+"}, {"LOWER": "years"}] # If it has form 4+ years
            pattern11 = [{"POS": "PUNCT"}, {"LOWER": "years"}] # If it has form +4 years
            pattern2 = [{"ORTH": {"NOT_IN": ["-"]}}, {"LIKE_NUM": True}, {"LOWER": "years"}] # If it has format 4 years
            pattern3 = [{"LIKE_NUM": True}, {"ORTH": "-"} , {"LIKE_NUM": True},{"LOWER": "years"}] # If it has a format of 2-5 Years
            matcher.add("pattern_+", [pattern1])
            matcher.add("pattern_++", [pattern11])
            matcher.add("pattern_num", [pattern2])
            matcher.add("pattern_range", [pattern3])
            
            matches = matcher(sentence)

            for match_id, start, end in matches:
                string_id = nlp.vocab.strings[match_id]  # Get string representation
                span = sentence[start:end]  # The matched span
                number_years = re.findall(r'[0-9]+', span.text)
                
                # Check if the numbers are not written as words, otherwise transform
                if not number_years:
                    number_years = transform_words_to_num(span.text)
                else:
                    if len(number_years) == 1:
                        number_years = int(number_years[0])
                    else:
                        list_range = [int(num) for num in number_years]
                        string_id = "pattern_range"
                
                if string_id == "pattern_+" or string_id == "pattern_++":
                    if (number_years + 1) > experience_max_year_threshold and number_years < 11: # The and is to avoid 100 years
                        apply_experience = False
                        reason_not_apply = "Experience"
                
                if string_id == "pattern_num":
                    if (number_years > experience_max_year_threshold) and number_years < 11: # The and is to avoid 100 years
                        apply_experience = False
                        reason_not_apply = "Experience"
                
                if string_id == "pattern_range":
                    if min(list_range) > experience_max_year_threshold:
                        apply_experience = False
                        reason_not_apply = "Experience"
            
            # If it uses a ADJ + "years of experience"
            if experience_max_year_threshold < 4:
                pattern = [{"POS": "ADJ"}, {"LOWER": "years"}, {"LOWER": "of"}, {"LOWER": "experience"}]
                matcher.add("pattern_adj_years of experience", [pattern])
                matches = matcher(sentence)
            
            for match_id, start, end in matches:
                string_id = nlp.vocab.strings[match_id]  # Get string representation
                span = sentence[start:end]  # The matched span

                if string_id == "pattern_adj_years of experience":
                    adj = span[0]
                    similarity = max([adj.similarity(nlp("many")), adj.similarity(nlp("multiple"))]) # Check if the adjective is similar to many
                    if similarity > 0.7:
                        apply_experience = False
                        reason_not_apply = "Experience"
            
            # If it uses a ADJ + "experience"
            if experience_max_year_threshold < 4:
                pattern = [{"POS": "ADJ"}, {"LOWER": "experience"}]
                matcher.add("pattern_adj_experience", [pattern])
                matches = matcher(sentence)
            
            for match_id, start, end in matches:
                string_id = nlp.vocab.strings[match_id]  # Get string representation
                span = sentence[start:end]  # The matched span

                if string_id == "pattern_adj_experience":
                    adj = span[0]
                    similarity = max([adj.similarity(nlp("strong")), adj.similarity(nlp("solid"))]) # Check if the adjective is similar to strong
                    if similarity > 0.7:
                        apply_experience = False
                        reason_not_apply = "Experience"
    
    return apply_experience, reason_not_apply

def check_technology_requirement(doc):
    """Function to check the technologies required by the job description.
    
    Parameters
    ----------
        doc : spacy doc
            Description to check in spacy doc type
    Returns
    -------
        apply_technology : bool
            Boolean to apply or not according to experience requirements
        reason_not_apply : str
            Reason not to apply if there is one
        list_technologies_no_knowledge : list
            List of technologies that you dont know and are the reason not to apply to the job, if there are some
        list_tags : list
            List of entities, they will work as tags for the job description
    """
    
    apply_technology = True
    reason_not_apply = []
    list_technologies_no_knowledge = []
    list_possible_tags = []
    list_tags = []

    # Load the user options 
    entities_do_not_apply, programming_languages_apply, backend_frameworks_apply = load_user_technologies_to_check()
    
    # List of possible tags using the entities that you created
    for key in json_data:
        for entity in json_data[key]:
            list_possible_tags.append(entity.lower())

    # Check the entities
    for entity in doc.ents:

        # Check if the entity is in the list of the entities that you created and append to list_tags if they are
        if entity.text in list_possible_tags:
            list_tags.append(entity.text)
        
        # Check if the entity is one of the entities not to apply. Example "Automation Server", "In-Memory Data Store", etc
        if entity.label_ in entities_do_not_apply:
            apply_technology = False
            list_technologies_no_knowledge.append(entity.text) # Append list of technologies that you dont know
            reason_not_apply.append("Technology Group")
        
        # Check if there are programming languages that you dont know
        if entity.label_ == "Programming Language":
            if entity.text not in programming_languages_apply:
                sentence = entity.sent # sentence where the programming language is
                
                # Check if any of the programming languages that you know is in the sentence, as there can be an or
                # example: proficiency in programming languages such as python, java, or scala
                for prog_lang in programming_languages_apply:
                    if prog_lang in sentence.text:
                            for token in sentence:
                                if token.text == "or": # Check if there is an "or" word in the sentence
                                    break
                    else:
                        apply_technology = False
                        list_technologies_no_knowledge.append(entity.text) # Append list of technologies that you dont know
                        reason_not_apply.append("Programming Language")

        # Check if there are programming languages that you dont know
        if entity.label_ == "Backend Web Framework":
            if entity.text not in backend_frameworks_apply:
                apply_technology = False
                list_technologies_no_knowledge.append(entity.text) # Append list of technologies that you dont know
                reason_not_apply.append("Backend Web Framework")
    
    # Use a set not to repeat the option
    list_technologies_no_knowledge = list(set(list_technologies_no_knowledge))
    reason_not_apply = list(set(reason_not_apply))
    list_tags = list(set(list_tags))

    return apply_technology, reason_not_apply, list_technologies_no_knowledge, list_tags

def check_if_email(doc,nlp):
    """Function to check if the job description has an email as the recruiters usually ask you to apply through
    email instead of the easy apply
    
    Parameters
    ----------
        doc : spacy doc
            Description to check in spacy doc type
        nlp : spacy nlp model
            Spacy nlp model to be used
    Returns
    -------
        email : list
            list if there are not emails it will be empty
    """
    email = []
    # Create Matcher with the spacy email as pattern
    matcher = Matcher(nlp.vocab)
    pattern = [{"LIKE_EMAIL": True}]
    matcher.add("EMAIL_ADDRESS", [pattern])
    matches = matcher(doc)

    # If there is a match then get the email form the documemt
    for match_id, start, end in matches:
        email.append(doc[start:end].text)
    
    return email

def check_apply_or_not(description):
    """Function to decide if apply for the job or not
    
    Parameters
    ----------
        description : str
            Description to check
    Returns
    -------
        apply : bool
            Boolean to apply or not
        email: bool or str
            If there is an email in the description then the email otherwise False
        reason_not_apply : list
            If there are reasons not to apply then a list of them
        list_technologies_no_knowledge : list
            List of the technologies that you dont have knowledge if there is any
        clean_description : str
            Translated and cleaned description of the job
    """
    
    apply = True

    # Pre-process the description to use in spacy
    clean_description = pre_process_text(description)
    
    # Create model
    nlp = create_nlp_model()

    # Create document
    doc = nlp(clean_description)

    # Check language requirement
    apply_lang, reason_not_apply_lang = check_language_requirement(doc, nlp)

    # Check experience requirement
    apply_exp, reason_not_apply_exp = check_experience_requirement(doc, nlp)
    
    # Check technology requirement
    apply_tech, reason_not_apply_tech, list_technologies_no_knowledge, list_tags = check_technology_requirement(doc)

    # Check if there is an email in the description
    email = check_if_email(doc,nlp)

    # Decide to apply if all the requirements are True, otherwise do not apply
    list_apply_decision = [apply_lang, apply_exp, apply_tech]

    if all(list_apply_decision):
        apply = True
    else:
        apply = False
    
    # Check if there are reasons not to apply and append to the list
    if reason_not_apply_lang:
        reason_not_apply_tech.append(reason_not_apply_lang)
    if reason_not_apply_exp:
        reason_not_apply_tech.append(reason_not_apply_exp)
    
    reason_not_apply = reason_not_apply_tech
    
    return apply, email, reason_not_apply, list_technologies_no_knowledge, list_tags, clean_description