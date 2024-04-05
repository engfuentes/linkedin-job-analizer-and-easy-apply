import asyncio, logging
from playwright.async_api import async_playwright
from modules.helper_functions import scrap_easy_apply, load_json_to_dict, log_exceptions, \
    save_job_questions_no_answer
import itertools
import json

logger = logging.getLogger('easy apply module')

async def exception_questions(e, logger, job_inst, page):
    """Function used when there are exceptions in the questions
    
    Parameters
    ----------
        e : Exception Object
            Exception Object
        logger : logger object
            Logger object
        job_inst : job instance
            Instance of the job that is being processed
        page : playwright object
            Playwright page
    Returns
    -------
        job_inst : job instance
            Instance of the job that is being processed
    """
    log_exceptions(e, logger)
    job_inst.could_not_apply_due_to_questions = True
    await exit_easy_apply(page)
    return job_inst

async def remove_work_or_education_history(page, job_inst):
    """Function used Remove the Work History or Education that was prefilled by Linkedin
    
    Parameters
    ----------
        page : playwright object
            Playwright page
        job_inst : job instance
            Instance of the job that is being processed
    """
    try:
        # Get the total number of remove buttons
        total_buttons = await page.locator("button[aria-label='Remove the following work experience']").count()
        
        for i in range(0, total_buttons):
            # Get first button from the actual list. (If it is not done now some buttons are not recognized into the loop)
            buttons = await page.locator("button[aria-label='Remove the following work experience']").all()
            button = buttons[0]
            
            # Click Remove Button
            await button.click()
            await page.wait_for_timeout(500)

            # Click other Remove Button to confirm
            await page.get_by_role("button", name="Remove").click()
            await page.wait_for_timeout(500)
    
    except Exception as e:
        job_inst = await exception_questions(e, logger, job_inst, page)
        return job_inst

async def add_work_history(page, work_history, job_inst):
    """Function used to fill the Work Experience tab
    
    Parameters
    ----------
        page : playwright object
            Playwright page
        work_history : list
            List of dict with the Work History that has to be filled (According to the position you apply)
        job_inst : job instance
            Instance of the job that is being processed
    """
    try:
        for work_experience in work_history:
            # Click add Button
            await page.locator("button.jobs-easy-apply-repeatable-groupings__add-button").click()

            # Get the last work card
            work_card_list = await page.locator("div.artdeco-card > div.pb4").all()
            work_card = work_card_list[-1]
           
            # Fill the title
            await work_card.locator("label").filter(has_text="Your title").fill(work_experience["title"])
            await page.wait_for_timeout(300)

            # Fill the company
            #await page.locator("label").filter(has_text="Company").fill(work_experience["company"])
            await work_card.get_by_text("Company", exact=True).fill(work_experience["company"])
            await page.wait_for_timeout(300)
        
            # If current work the click checkbox
            if work_experience["current_work"] == "True":
                await work_card.locator(f'div > label[data-test-text-selectable-option__label="I currently work here"]').click()
                await page.wait_for_timeout(300)

            # Select from
            await work_card.get_by_label("Month of From").select_option(work_experience["from_month"])
            await work_card.get_by_label("Year of From").select_option(work_experience["from_year"])
            await page.wait_for_timeout(300)

            # Select to
            if work_experience["current_work"] == "False":
                await work_card.get_by_label("Month of To").select_option(work_experience["to_month"])
                await work_card.get_by_label("Year of To").select_option(work_experience["to_year"])
                await page.wait_for_timeout(300)

            # Fill Select City
            if work_experience["city"] != "None":
                combobox_list = await work_card.get_by_role("combobox").all()
                select_city = combobox_list[-1]

                await select_city.fill(work_experience["city"]) # Fill the Answer
                await page.wait_for_timeout(500)
                await select_city.press("ArrowDown") # Select from the list
                await select_city.press("Enter")
                await page.wait_for_timeout(300)

            # Fill Job Description
            await work_card.locator("label").filter(has_text="Description").fill(work_experience["description"])
            await page.wait_for_timeout(300)

            # Save the Work Experience
            await page.get_by_role("button", name="Save").click()
    
    except Exception as e:
        job_inst = await exception_questions(e, logger, job_inst, page)
        return job_inst

async def add_education_history(page, education_history, job_inst):
    """Function used to fill the Education tab
    
    Parameters
    ----------
        page : playwright object
            Playwright page
        education_history : list
            List of dict with the Education that has to be filled (According to the position you apply)
        job_inst : job instance
            Instance of the job that is being processed
    """
    try:
        for education_step in education_history:
            # Click add Button
            await page.locator("button.jobs-easy-apply-repeatable-groupings__add-button").click()

            # Fill the school
            await page.locator("label").filter(has_text="School").fill(education_step["school"])
            await page.wait_for_timeout(300)

            # Fill Select City
            combobox_list = await page.get_by_role("combobox").all()# Fill the answer
            select_city = combobox_list[0]

            await select_city.fill(education_step["city"]) # Fill the Answer
            await page.wait_for_timeout(500)
            await select_city.press("ArrowDown") # Select from the list
            await select_city.press("Enter")
            await page.wait_for_timeout(300)

            # Fill the degree
            await page.locator("label").filter(has_text="Degree").fill(education_step["degree"])
            await page.wait_for_timeout(300)

            # Fill the major / field of study
            await page.locator("label").filter(has_text="Major / Field of study").fill(education_step["field_study"])
            await page.wait_for_timeout(300)
        
            # Select from
            await page.get_by_label("Month of From").select_option(education_step["from_month"])
            await page.get_by_label("Year of From").select_option(education_step["from_year"])
            await page.wait_for_timeout(300)

            # Select to
            await page.get_by_label("Month of To").select_option(education_step["to_month"])
            await page.get_by_label("Year of To").select_option(education_step["to_year"])
            await page.wait_for_timeout(300)

            # Save the Job
            await page.get_by_role("button", name="Save").click()
    
    except Exception as e:
        job_inst = await exception_questions(e, logger, job_inst, page)
        return job_inst

async def click_correct_cv(cvs, language):
    """Function used click the correct cv from a list of cvs elements
    
    Parameters
    ----------
        cvs : List of playwright objects (CVs)
            list
        language : str
            Correct language to choose. The name must be present in the cv file
    """       
    for cv in cvs:
        cv_text = await cv.inner_text()
        if language.lower() in cv_text.lower():
            # Click the cv if it is not selected
            if await cv.get_attribute('aria-label') != "Selected":
                await cv.click()
                break

async def choose_cv(page, job_inst):
    """Function used find and choose the proper cv
    
    Parameters
    ----------
        page : playwright object
            Playwright page
        job_inst : job instance
            Instance of the job that is being processed
    """    
    # Get the job description language
    description_lang = job_inst.description_lang

    # Click button to show more resumes
    if (await page.locator("button[aria-label='Show more resumes']").count()) == 1:
        await page.locator("button[aria-label='Show more resumes']").click()

    # Get all the resume elements
    cvs = await page.locator("div.jobs-document-upload-redesign-card__container").all()

    # Click the proper CV depending the language
    if description_lang == "es":
        await click_correct_cv(cvs, "Espanol")
    elif description_lang == "it":
        await click_correct_cv(cvs, "Italiano")
    else:
        await click_correct_cv(cvs, "English")    

def add_answers_questions_work_visa(easy_apply_quest_answ, dict_user_opts, country):
    """Function that adds to the easy_apply_quest_answ dict some answers about the work visa conditions,
    depending the country of the job position
    
    Parameters
    ----------
        easy_apply_quest_answ : dict
            Dictionary with the questions and answers for easy apply
        dict_user_opts : dict
            Dictionary with the user options of search, save and apply
        country : str
            Country of the job position
    Returns
    -------
        easy_apply_quest_answ : dict
            Dictionary with the questions and answers for easy apply
    """
    # Get the list of countries that you dont need a work visa to work
    list_countries_no_work_visa = dict_user_opts["countries_no_visa"]

    if country in list_countries_no_work_visa:
        easy_apply_quest_answ["Do you need sponsorship for a new position?"] = "No"
        easy_apply_quest_answ["Will you now or in the future require sponsorship for employment visa status?"] = "No"
        easy_apply_quest_answ["Do you need visa sponsorship to work in this location?"] = "No"
        easy_apply_quest_answ["Are you authorized to work in the job's country?"] = "Yes"
        easy_apply_quest_answ[f"Are you legally authorized to work in {country}?"] = "Yes"
    else:
        easy_apply_quest_answ["Do you need sponsorship for a new position?"] = "Yes"
        easy_apply_quest_answ["Will you now or in the future require sponsorship for employment visa status?"] = "Yes"
        easy_apply_quest_answ["Do you need visa sponsorship to work in this location?"] = "Yes"
        easy_apply_quest_answ["Are you authorized to work in the job's country?"] = "No"
        easy_apply_quest_answ[f"Are you legally authorized to work in {country}?"] = "No"

    return easy_apply_quest_answ

async def check_questions(page, job_inst, dict_user_opts):
    """Function that checks if there are questions in the EasyApply tab. If there are questions
    it checks if it has the answers, if not, it addes them to a list that is saved to a json file
    
    Parameters
    ----------
        page : playwright object
            Playwright page
        job_inst : job instance
            Instance of the job that is being processed
        dict_user_opts : dict
            Dictionary with the user options of search, save and apply 
    Returns
    -------
        job_inst : job instance
            Instance of the job that is being processed
    """
    await page.wait_for_timeout(500)
    
    # List of missing questions 
    missing_questions = []

    # Import the questions and answers of EasyApply
    easy_apply_quest_answ = load_json_to_dict(dict_user_opts["easy_apply_quest_answ_path"])

    # Get html code from the page
    questions_html = await page.content()
    # Scrap the html to check if there are questions with 4 types: Input, Select, Checkbox or Fill and Select
    input_questions, select_questions, checkbox_questions, fill_select_questions, \
                                      work_experience, education, privacy_policy, resume = scrap_easy_apply(questions_html)
    # Make one list of the 4 lists
    easy_apply_questions = list(itertools.chain(input_questions, select_questions, checkbox_questions, fill_select_questions))
    # Add to the job instance the Easy Apply questions
    job_inst.easy_apply_questions = easy_apply_questions

    # Add visa related questions to the easy_apply questions and answers dict
    easy_apply_quest_answ = add_answers_questions_work_visa(easy_apply_quest_answ, dict_user_opts, job_inst.search_country)

    # Check if all the questions are in the dict with the answers, if not append the missing ones to the list
    for question in easy_apply_questions:
        if question not in easy_apply_quest_answ.keys():
            missing_questions.append(question)
            # If cannot apply due to missing questions change the bool to True to apply later
            job_inst.could_not_apply_due_to_questions = True

    # If the bool is true due to a missing question in the dict save all the missing questions to a json file
    # and return the job_instance
    if job_inst.could_not_apply_due_to_questions == True:
        save_job_questions_no_answer(missing_questions, './data/questions_no_answer.json')
        logger.info(f"Questions without answers: {missing_questions}")
        return job_inst

    # Locate only the EasyApply content
    easy_apply_tab = page.locator("div.jobs-easy-apply-content")

    # If there are input questions, fill them
    if input_questions:
        for input_question in input_questions:
            try:
                answer = easy_apply_quest_answ[input_question]
                await easy_apply_tab.get_by_text(input_question, exact=True).fill(answer)
                await page.wait_for_timeout(300)
            except Exception as e:
                job_inst = await exception_questions(e, logger, job_inst, page)
                return job_inst
    
    # If there are select questions, select them
    if select_questions:
        for select_question in select_questions:
            try:
                answer = easy_apply_quest_answ[select_question]
                await easy_apply_tab.get_by_label(select_question).select_option(answer)
                await page.wait_for_timeout(300)
            except Exception as e:
                job_inst = await exception_questions(e, logger, job_inst, page)
                return job_inst
    
    # If there are checkbox questions, check them            
    if checkbox_questions:
        fieldsets = await easy_apply_tab.locator("fieldset").all() # Get all the fieldsets with the checkbox questions
        for checkbox_question in checkbox_questions:
            try:
                answer = easy_apply_quest_answ[checkbox_question]

                for fieldset in fieldsets:
                    legend_text_option1 = await fieldset.locator("legend > span > span[aria-hidden=true]").count()
                    legend_text_option2 = await fieldset.locator("legend > div > span[aria-hidden=true]").count()
                    
                    if legend_text_option1 == 1:
                        legend_text = await fieldset.locator("legend > span > span[aria-hidden=true]").text_content()
                    elif legend_text_option2 == 1:
                        legend_text = await fieldset.locator("legend > div > span[aria-hidden=true]").text_content()
                    
                    if checkbox_question == legend_text.strip():
                        await fieldset.locator(f'div > label[data-test-text-selectable-option__label="{answer}"]').click()
                        await page.wait_for_timeout(300)
                        break

            except Exception as e:
                job_inst = await exception_questions(e, logger, job_inst, page)
                return job_inst

    # Check if there are fill questions
    if fill_select_questions:
        for fill_select_question in fill_select_questions:
            try:
                answer = easy_apply_quest_answ[fill_select_question]
                divs = await page.locator("div.fb-dash-form-element").all()
                for div in divs:
                    label_text = await div.locator("span[aria-hidden=true]").text_content()
                    if label_text == fill_select_question:
                        await div.get_by_role("combobox").fill(answer) # Fill the answer
                        await page.wait_for_timeout(500)
                        await div.locator("span[aria-hidden=true]").press("ArrowDown")
                        await div.locator("span[aria-hidden=true]").press("Enter")
                        break
                await page.wait_for_timeout(300)
            except:
                try:
                    answer = easy_apply_quest_answ[fill_select_question]
                    label_text = await page.locator("div.fb-dash-form-element").locator("span[aria-hidden=true]").text_content()
                    div = page.locator("div.fb-dash-form-element")
                    if label_text == fill_select_question:
                        await div.get_by_role("combobox").fill(answer) # Fill the answer
                        await page.wait_for_timeout(500)
                        await div.locator("span[aria-hidden=true]").press("ArrowDown")
                        await div.locator("span[aria-hidden=true]").press("Enter")
                    await page.wait_for_timeout(300)
                
                except Exception as e:
                    job_inst = await exception_questions(e, logger, job_inst, page)
                    return job_inst

    # Check for Work Experience Tab. If exists then delete all the jobs and fill with new
    if work_experience:
        # Remove all the work history
        await remove_work_or_education_history(page, job_inst)

        # Load the desired Work Experience that is related to the position
        work_history = load_json_to_dict("./data/work_and_education_history.json")["Work Experience"]

        # Add relevant work Experience
        await add_work_history(page, work_history, job_inst)

    # Check for Education Tab. If exists then delete all the education and fill with new
    if education:
        # Remove all the education
        await remove_work_or_education_history(page, job_inst)

        # Load the desired Education that is related to the position
        education_history = load_json_to_dict("./data/work_and_education_history.json")["Education"]

        # Add relevant Education
        await add_education_history(page, education_history, job_inst)

    # Check if there is a Privacy Policy to accept
    if privacy_policy:
        # Accept the Privacy Policy
        await page.locator(f'div > label[data-test-text-selectable-option__label="I Agree Terms & Conditions"]').click()
        page.wait_for_timeout(300)

    # Check if the CV can be chosen
    if resume:
        # Choose the correct CV
        await choose_cv(page, job_inst)

    return job_inst

async def exit_easy_apply(page):
    """Function to exit Easy Apply
    
    Parameters
    ----------
        page : playwright object
            Playwright page
    """
    try:
        await page.get_by_role("button", name="Dismiss").click()
        await page.wait_for_timeout(500)
        await page.get_by_role("button", name="Discard").click()
    except:
        await page.locator("div.jobs-easy-apply-modal > button[aria-label=Dismiss]").click()
        await page.wait_for_timeout(500)
        await page.get_by_role("button", name="Discard").click()

async def check_buttons(page, job_inst, dict_user_opts):
    """Function that checks the 3 different buttons ofthe Easy Apply tabs: Next, Review, Submit Application
    
    Parameters
    ----------
        page : playwright object
            Playwright page
        job_inst : job instance
            Instance of the job that is being processed
        dict_user_opts : dict
            Dictionary with the user options of search, save and apply 
    Returns
    -------
        job_inst : job instance
            Instance of the job that is being processed
    """
    await page.wait_for_timeout(500)
    
    # Check if there are questions
    job_inst = await check_questions(page, job_inst, dict_user_opts)

    # Check if questions could be answered, if not exit the EasyApply Tab and return the instance
    if job_inst.could_not_apply_due_to_questions == True:
        await exit_easy_apply(page)
        return job_inst
    
    await page.wait_for_timeout(500)

    # If all was ok and then click "Submit application", "Review" or "Next"

    if (await page.get_by_label("Submit application").count()) == 1:
        # If there is a Submit Application button
        await page.get_by_label("Submit application").click()
        job_inst.applied = True
        await page.wait_for_timeout(2000)

        try:
            logger.info("Pressing button 1 to close")
            await page.get_by_role("button", name="Done").click()
            await page.wait_for_timeout(1000)
        except:
            logger.info("Pressing button 2 to close")
            await page.get_by_role("button", name="Dismiss").click()
            await page.wait_for_timeout(1000)
        
        return job_inst

    elif (await page.locator("button[aria-label='Review your application']").count()) == 1:
        await page.locator("button[aria-label='Review your application']").click()
    elif (await page.locator("button[aria-label='Continue to next step']").count()) == 1:
        await page.locator("button[aria-label='Continue to next step']").click()

    return job_inst

async def easy_apply(page, job_inst, dict_user_opts):
    """Function that applies to the job with Easy Apply. It is going to check if it has a tab with specific questions
    for the job. If this questions are not in a dict, then they are saved to answer and later apply again
    
    Parameters
    ----------
        page : playwright object
            Playwright object
        job_inst : instance
            Instance of a job class with the job information
        dict_user_opts : dict
            Dictionary with the user options of search, save and apply    
    Returns
    -------
        job_inst : instance
            Instance of a job class with the job information
    """
    # Click Easy apply button
    await page.locator("div.jobs-s-apply > div > button:visible > span", has_text="Easy Apply").click()
    await page.wait_for_timeout(1000)

    job_inst.applied = False
    job_inst.could_not_apply_due_to_questions = False

    # Do the loop of checking buttons and filling information until applied or until cannot
    # Apply do to missing answers
    applied = job_inst.applied
    not_apply_due_to_questions = job_inst.could_not_apply_due_to_questions
    while (applied == False) and (not_apply_due_to_questions == False):
        job_inst = await check_buttons(page, job_inst, dict_user_opts)
        applied = job_inst.applied
        not_apply_due_to_questions = job_inst.could_not_apply_due_to_questions
        await page.wait_for_timeout(1000)
    
    return job_inst