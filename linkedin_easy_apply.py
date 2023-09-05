import asyncio
from playwright.async_api import async_playwright
from modules.helper_functions import scrap_job, save_job_info_to_json
from modules.check_apply import check_apply_or_not
from modules.save_to_postgresql_db import save_to_postgresql_db
import configparser

# playwright codegen --load-storage=auth.json linkedin.com

# Load parameters from config file
config_obj = configparser.ConfigParser(converters={'list': lambda x: [i.strip() for i in x.split(',')]})
config_obj.read("./configfile.ini")

# Options
save_to_json_file_option = config_obj.getboolean('options', 'save_to_json_file')
save_to_postgresql_db_option = config_obj.getboolean('options', 'save_to_postgresql_db')

# User search
user_search_position = config_obj["user_search"]["position"]
user_search_country = config_obj["user_search"]["country"]

# Languages the user speaks
fluent_languages = config_obj.getlist('languages_user_speak_fluently', 'languages')

# Words to check in the languages that you dont speak
adj_to_check = config_obj.getlist('words_check_language_check', 'adj_to_check')
noun_to_check = config_obj.getlist('words_check_language_check', 'noun_to_check')
propn_to_check = config_obj.getlist('words_check_language_check', 'propn_to_check')
verb_to_check = config_obj.getlist('words_check_language_check', 'verb_to_check')
adv_to_check = config_obj.getlist('words_check_language_check', 'adv_to_check')
similarity_threshold = float(config_obj["words_check_language_check"]["similarity_threshold"])

# Experience parameters
seniority_do_not_apply = config_obj.getlist('experience', 'seniority_do_not_apply')
experience_max_year_threshold = int(config_obj["experience"]["experience_max_year_threshold"])

# Technologies parameters
entities_do_not_apply = config_obj.getlist('technologies', 'entities_do_not_apply')
programming_languages_apply = config_obj.getlist('technologies', 'programming_languages_apply') 
backend_frameworks_apply = config_obj.getlist('technologies', 'backend_frameworks_apply')

async def run(p):
    browser = await p.chromium.launch(headless=False)
    
    # Create a context and load the cookies with the login info
    context = await browser.new_context(storage_state="auth.json")
    
    # Enter to linkedin
    page = await context.new_page()
    
    await page.goto("https://www.linkedin.com/jobs/")

    # Choose the job title
    await page.get_by_role("combobox", name="Search by title, skill, or company").click()
    await page.get_by_role("combobox", name="Search by title, skill, or company").fill(f'{user_search_position}')
    await page.get_by_role("button", name=f'{user_search_position}', exact=True).click()
    await page.wait_for_timeout(2000)

    # Choose the country
    await page.get_by_role("combobox", name="City, state, or zip code").click()
    await page.get_by_role("combobox", name="City, state, or zip code").fill(f'{user_search_country}')
    await page.get_by_role("button", name=f'{user_search_country}', exact=True).click()

    await page.wait_for_timeout(2000)
    await page.get_by_label("Easy Apply filter.").click()

    await page.wait_for_timeout(2000)

    # Check all the pages while there is no error
    page_number = 1 # Initial page number

    while True:
        try:
            page_number += 1
            list_jobs_instances = [] # List of job instances to save to the json (After scrapping one website page)
            await page.wait_for_timeout(1000)
            
            # Locate the list of jobs results
            for job in await page.locator("ul.scaffold-layout__list-container > li.ember-view").all():
                # Click on each job
                await job.click()

                await page.wait_for_timeout(1000)
                
                # Get the html code of the job
                job_html = await page.content()
                
                # Scrap the job information
                job_inst = scrap_job(job_html) # Get the job instance with the scrapped info
                
                # Check the description to decide if apply or not. Also get the email if must be applied sending email
                # instead of EasyApply, and Reasons not to apply and job tags 
                job_inst.apply, job_inst.email, job_inst.reason_not_apply, \
                job_inst.list_tech_no_knowledge, job_inst.list_tags,  \
                job_inst.description = check_apply_or_not(job_inst.description,
                                                                fluent_languages,
                                                                adj_to_check,
                                                                noun_to_check,
                                                                propn_to_check,
                                                                verb_to_check,
                                                                adv_to_check,
                                                                similarity_threshold,
                                                                seniority_do_not_apply,
                                                                experience_max_year_threshold,
                                                                entities_do_not_apply,
                                                                programming_languages_apply,
                                                                backend_frameworks_apply)
                
                # Append the job instance to a list
                list_jobs_instances.append(job_inst)
                
                if job_inst.apply and job_inst.email:
                    print("APPLY!")
                
                await page.wait_for_timeout(1000)

                # Click in the Easy Apply Button
                #await page.locator("div.jobs-s-apply button:visible").click()

            # After one page has been webscrapped and analyzed then save all the instances of the list to a json file. If Option = True
            if save_to_json_file_option:
                save_job_info_to_json(list_jobs_instances, "./data/linkedin_jobs.json")
            
            # Save to postgresql if option = True
            if save_to_postgresql_db_option:
                save_to_postgresql_db(list_jobs_instances)
            
            # Click the next page
            await page.locator(f"button[aria-label='Page {page_number}']").click()
        
        except Exception as e:
            print(e)
            break

    await browser.close()

async def main():
    async with async_playwright() as p:
        await run(p)

asyncio.run(main())