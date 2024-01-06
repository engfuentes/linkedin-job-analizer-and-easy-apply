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

            # Fill the title
            await page.locator("label").filter(has_text="Your title").fill(work_experience["title"])
            await page.wait_for_timeout(300)

            # Fill the company
            await page.locator("label").filter(has_text="Company").fill(work_experience["company"])
            await page.wait_for_timeout(300)
        
            # Select from
            await page.get_by_label("Month of From").select_option(work_experience["from_month"])
            await page.get_by_label("Year of From").select_option(work_experience["from_year"])
            await page.wait_for_timeout(300)

            # Select to
            await page.get_by_label("Month of To").select_option(work_experience["to_month"])
            await page.get_by_label("Year of To").select_option(work_experience["to_year"])
            await page.wait_for_timeout(300)

            # Fill Select City
            combobox_list = await page.get_by_role("combobox").all()
            select_city = combobox_list[-1]

            await select_city.fill(work_experience["city"]) # Fill the Answer
            await page.wait_for_timeout(500)
            await select_city.press("ArrowDown") # Select from the list
            await select_city.press("Enter")
            await page.wait_for_timeout(300)

            # Fill Job Description
            await page.locator("label").filter(has_text="Description").fill(work_experience["description"])
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
                                      work_experience, education, privacy_policy = scrap_easy_apply(questions_html)
    # Make one list of the 4 lists
    easy_apply_questions = list(itertools.chain(input_questions, select_questions, checkbox_questions, fill_select_questions))
    # Add to the job instance the Easy Apply questions
    job_inst.easy_apply_questions = easy_apply_questions

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

    # If there are input questions, fill them
    if input_questions:
        for input_question in input_questions:
            try:
                answer = easy_apply_quest_answ[input_question]
                await page.get_by_text(input_question).fill(answer)
                await page.wait_for_timeout(300)
            except Exception as e:
                job_inst = await exception_questions(e, logger, job_inst, page)
                return job_inst
    
    # If there are select questions, select them
    if select_questions:
        for select_question in select_questions:
            try:
                answer = easy_apply_quest_answ[select_question]
                await page.get_by_label(select_question).select_option(answer)
                await page.wait_for_timeout(300)
            except Exception as e:
                job_inst = await exception_questions(e, logger, job_inst, page)
                return job_inst
    
    # If there are checkbox questions, check them            
    if checkbox_questions:
        fieldsets = await page.locator("fieldset").all() # Get all the fieldsets with the checkbox questions
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
        await page.locator("button[aria-label=Dismiss]").click()
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

    await page.wait_for_timeout(500)
    
    # Check if there are questions
    job_inst = await check_questions(page, job_inst, dict_user_opts)

    # Check if questions could be answered, if not exit the EasyApply Tab and return the instance
    if job_inst.could_not_apply_due_to_questions == True:
        await exit_easy_apply(page)
        return job_inst
    
    # If all was ok and the button was Review
    if (await page.locator("button[aria-label='Review your application']").count()) == 1:
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