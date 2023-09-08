import asyncio
from playwright.async_api import async_playwright
from modules.helper_functions import scrap_job, log_exceptions
from modules.check_apply import check_apply_or_not
from modules.easy_apply import easy_apply
import logging

async def create_broswer_search_apply_filters(p, dict_user_opt_search_save_apply):
    """Function that creates a broswer, context and page. Performs the search of the job
    and also applies the search filters
    
    Parameters
    ----------
        p : playwright object
            playwright object
        dict_user_opt_search_save_apply : dict
            Dictionary with the user options of search, save and apply 
    Returns
    -------
        page : playwright object
            playwright page object
        browser : playwright object
            playwright browser object
    """
    # Create browser
    browser = await p.chromium.launch(headless=True)
    
    # Create a context and load the cookies with the login info
    context = await browser.new_context(storage_state="auth.json")
    
    # Enter to linkedin
    page = await context.new_page()
    
    await page.goto("https://www.linkedin.com/jobs/")

    user_search_position = dict_user_opt_search_save_apply["search_position"]
    user_search_country = dict_user_opt_search_save_apply["search_country"]

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

    return page, browser

async def scrap_apply_jobs_page(page, dict_user_opt_search_save_apply):
    """Function that performs the scrap decide if apply and apply actions to a job search results page
    Parameters
    ----------
        page : playwright object
            playwright page
        dict_user_opt_search_save_apply : dict
            Dictionary with the user options of search, save and apply
    Returns
    -------
        list_jobs_instances : list
            List of job instances with the jobs information
    """
    
    list_jobs_instances = [] # List of job instances to save to the json (After scrapping one website page)
    
    logger = logging.getLogger('scrap_apply_jobs_page')

    await page.wait_for_timeout(3000)

    # Locate the list of jobs results
    for job in await page.locator("ul.scaffold-layout__list-container > li.ember-view").all():
        # Click on each job        
        await job.click()

        await page.wait_for_timeout(2000)
        
        # Get the html code of the job
        job_html = await page.content()
        
        # Scrap the job information
        job_inst = scrap_job(job_html) # Get the job instance with the scrapped info

        # Add to the job instance the search_position and search_country
        job_inst.search_position = dict_user_opt_search_save_apply["search_position"]
        job_inst.search_country = dict_user_opt_search_save_apply["search_country"]

        logger.info(f"Check if apply:{job_inst.position_name}, {job_inst.company}, {job_inst.url}")
        # Check the description to decide if apply or not. Also get the email if must be applied sending email
        # instead of EasyApply, and Reasons not to apply and job tags 
        job_inst.apply, job_inst.email, job_inst.reason_not_apply, \
        job_inst.list_tech_no_knowledge, job_inst.list_tags,  \
        job_inst.description = check_apply_or_not(job_inst.description)

        # If it was decided to apply and there is not an email in the description (many require to send an email)
        if job_inst.apply and not job_inst.email and dict_user_opt_search_save_apply["use_easy_apply"]:
            logger.info(f"Apply: {job_inst.position_name}, {job_inst.company}, {job_inst.url}")
            job_inst = await easy_apply(page, job_inst)
            logger.info(f"Applied: {job_inst.applied}")

        # Scroll with the mouse
        await page.mouse.move(x=100, y=300)
        await page.mouse.wheel(delta_x=0.0, delta_y=150.0)

        # Append the job instance to a list
        list_jobs_instances.append(job_inst)

    return list_jobs_instances